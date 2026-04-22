import logging
import os
import secrets
import string
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Optional

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "northenvolunteerdb")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120
REFRESH_TOKEN_EXPIRE_DAYS = 7

MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "Volunteer Management Portal")
MAIL_STARTTLS = os.getenv("MAIL_STARTTLS", "True").lower() == "true"
MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS", "False").lower() == "true"
USE_CREDENTIALS = os.getenv("USE_CREDENTIALS", "True").lower() == "true"
VALIDATE_CERTS = os.getenv("VALIDATE_CERTS", "True").lower() == "true"

EMAIL_CONFIG = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME or "",
    MAIL_PASSWORD=MAIL_PASSWORD or "",
    MAIL_FROM=MAIL_FROM or "",
    MAIL_PORT=MAIL_PORT,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_FROM_NAME=MAIL_FROM_NAME,
    MAIL_STARTTLS=MAIL_STARTTLS,
    MAIL_SSL_TLS=MAIL_SSL_TLS,
    USE_CREDENTIALS=USE_CREDENTIALS,
    VALIDATE_CERTS=VALIDATE_CERTS,
)

DATABASE_URL = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

app = FastAPI(title="JamatKhana API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expiry: Optional[int] = None


class TokenRefresh(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_size=20,
    max_overflow=40,
    pool_timeout=60,
    pool_pre_ping=True,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

volunteer_engine = engine
volunteer_async_session = async_session


async def get_db():
    async with async_session() as session:
        yield session


async def get_volunteer_db():
    async with volunteer_async_session() as session:
        yield session


async def set_db_actor(db: AsyncSession, actor_id: str) -> None:
    await db.execute(text("SELECT set_config('application.user_id', :actor_id, false)"), {"actor_id": actor_id})


async def clear_db_actor(db: AsyncSession) -> None:
    await db.execute(text("RESET application.user_id"))


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def _get_user_row_by_email(db: AsyncSession, email: str):
    stmt = text(
        "SELECT id, email, password_hash, full_name, role_id, scope, region_id, is_active "
        "FROM users WHERE email = :email"
    )
    result = await db.execute(stmt, {"email": email})
    return result.mappings().first()


def _row_to_user(row) -> SimpleNamespace:
    user = SimpleNamespace(**dict(row))
    user.Id = row.get("id")
    user.Email = row.get("email")
    user.PasswordHash = row.get("password_hash")
    user.FullName = row.get("full_name")
    user.RoleId = row.get("role_id")
    user.Scope = row.get("scope")
    user.RegionId = row.get("region_id")
    user.IsActive = row.get("is_active")
    user.JamatKhanaIds = []
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str):
    row = await _get_user_row_by_email(db, email)
    if not row or not verify_password(password, row.get("password_hash")):
        return None
    return _row_to_user(row)


async def _resolve_role_name(db: AsyncSession, role_id: Optional[int]) -> Optional[str]:
    if role_id is None:
        return None
    try:
        role_q = await db.execute(text("SELECT name FROM user_roles WHERE id = :id"), {"id": role_id})
        role = role_q.first()
        if role:
            return role[0]
        role_q = await db.execute(text("SELECT name FROM roles WHERE id = :id"), {"id": role_id})
        role = role_q.first()
        if role:
            return role[0]
    except Exception:
        return None
    return None


async def _resolve_region_name(db: AsyncSession, region_id: Optional[int]) -> Optional[str]:
    if region_id is None:
        return None
    try:
        region_q = await db.execute(text("SELECT name FROM regions WHERE id = :id"), {"id": region_id})
        region = region_q.first()
        if region:
            return region[0]
        event_q = await db.execute(text("SELECT name FROM events WHERE id = :id"), {"id": region_id})
        event = event_q.first()
        if event:
            return event[0]
    except Exception:
        return None
    return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_volunteer_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    row = await _get_user_row_by_email(db, email)
    if row is None or not row.get("is_active"):
        raise credentials_exception
    return _row_to_user(row)


def generate_secure_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def is_email_configured() -> bool:
    return bool(MAIL_USERNAME and MAIL_PASSWORD and MAIL_FROM)


async def send_seed_password_email(
    recipient_email: str,
    recipient_name: str,
    seed_password: str,
    role_id: int,
) -> bool:
    try:
        if not is_email_configured():
            logger.warning("Email config missing; skipping sending email to %s", recipient_email)
            return False
        subject = "Your Volunteer Management Portal Account Password"
        body = (
            f"<p>Dear {recipient_name},</p>"
            f"<p>Your account has been created/updated. Here is your password:</p>"
            f"<p><strong>{seed_password}</strong></p>"
            f"<p>Please log in and change your password immediately.</p>"
            f"<p>Regards,<br/>{MAIL_FROM_NAME}</p>"
        )
        message = MessageSchema(
            subject=subject,
            recipients=[recipient_email],
            body=body,
            subtype=MessageType.html,
        )
        fm = FastMail(EMAIL_CONFIG)
        await fm.send_message(message)
        return True
    except Exception as ex:
        logger.warning("Failed to send email to %s: %s", recipient_email, str(ex))
        return False


@app.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_volunteer_db),
):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.IsActive:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive")

    role_name = await _resolve_role_name(db, user.RoleId)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.Email,
            "role": role_name if role_name is not None else user.RoleId,
            "name": user.FullName,
            "id": user.Id,
            "scope": user.Scope,
            "region_id": user.RegionId,
        },
        expires_delta=access_token_expires,
    )
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_refresh_token(
        data={
            "email": user.Email,
            "role": role_name if role_name is not None else user.RoleId,
            "name": user.FullName,
            "id": user.Id,
            "scope": user.Scope,
            "region_id": user.RegionId,
        },
        expires_delta=refresh_token_expires,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expiry": ACCESS_TOKEN_EXPIRE_MINUTES,
    }


@app.post("/login-json", response_model=Token)
async def login_json(payload: LoginRequest, db: AsyncSession = Depends(get_volunteer_db)):
    row = await _get_user_row_by_email(db, payload.email)
    if not row or not verify_password(payload.password, row.get("password_hash")):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not row.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive")

    now = datetime.utcnow()
    user_id = row.get("id")
    await db.execute(
        text("UPDATE users SET last_login = :now, updated_at = :now WHERE id = :id"),
        {"now": now, "id": user_id},
    )
    await db.commit()

    role_id = row.get("role_id")
    region_id = row.get("region_id")
    role_name = await _resolve_role_name(db, role_id)
    region_name = await _resolve_region_name(db, region_id)

    access_token = create_access_token(
        data={
            "sub": row.get("email"),
            "role": role_name if role_name is not None else role_id,
            "name": row.get("full_name"),
            "id": user_id,
            "scope": row.get("scope"),
            "region_id": region_name if region_name is not None else region_id,
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        data={
            "email": row.get("email"),
            "role": role_name if role_name is not None else role_id,
            "name": row.get("full_name"),
            "id": user_id,
            "scope": row.get("scope"),
            "region_id": region_name if region_name is not None else region_id,
        },
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expiry": ACCESS_TOKEN_EXPIRE_MINUTES,
    }


@app.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_volunteer_db),
):
    try:
        payload = jwt.decode(token_data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
        email = payload.get("email")
        if email is None:
            raise HTTPException(status_code=400, detail="Invalid refresh token")

        row = await _get_user_row_by_email(db, email)
        if row is None:
            raise HTTPException(status_code=400, detail="User not found")
        if not row.get("is_active"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive")

        role_id = row.get("role_id")
        role_name = await _resolve_role_name(db, role_id)
        region_id = row.get("region_id")
        region_name = await _resolve_region_name(db, region_id)

        access_token = create_access_token(
            data={
                "sub": row.get("email"),
                "role": role_name if role_name is not None else role_id,
                "name": row.get("full_name"),
                "id": row.get("id"),
                "scope": row.get("scope"),
                "region_id": region_name if region_name is not None else region_id,
            },
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token_value = create_refresh_token(
            data={
                "email": row.get("email"),
                "role": role_name if role_name is not None else role_id,
                "name": row.get("full_name"),
                "id": row.get("id"),
                "scope": row.get("scope"),
                "region_id": region_name if region_name is not None else region_id,
            },
            expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token_value,
            "token_type": "bearer",
            "expiry": ACCESS_TOKEN_EXPIRE_MINUTES,
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


from volunteer_auth import router as volunteer_auth_router, set_database_dependency as set_auth_db_dep
import volunteer_api_v2

set_auth_db_dep(get_volunteer_db)
volunteer_api_v2.set_database_dependencies(get_volunteer_db, get_db)

app.include_router(volunteer_auth_router)
app.include_router(volunteer_api_v2.volunteer_router, dependencies=[Depends(get_current_user)])


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/debug/config")
async def debug_config():
    return {
        "POSTGRES_HOST": POSTGRES_HOST,
        "POSTGRES_DB": POSTGRES_DB,
        "POSTGRES_PORT": POSTGRES_PORT,
        "POSTGRES_USER": POSTGRES_USER,
        "DATABASE_URL": DATABASE_URL[:50] + "...",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
