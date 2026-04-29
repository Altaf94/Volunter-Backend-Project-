import logging
import os
import secrets
import string
import time
import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Optional

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.middleware.base import BaseHTTPMiddleware

from app_config import (
    APP_ENV,
    DATABASE_URL,
    DB_POOL_RECYCLE,
    IS_DEVELOPMENT,
    IS_PRODUCTION,
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_USER,
    SQLALCHEMY_ECHO,
    USE_REMOTE_DATABASE,
    db_engine_connect_args,
)

# Import logging configuration
from logging_config import setup_logging
from error_logging import ErrorCode, ErrorLogger, ErrorSeverity

load_dotenv()

# Initialize logging
setup_logging()
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

def is_email_configured() -> bool:
    return bool(MAIL_USERNAME and MAIL_PASSWORD and MAIL_FROM)

if is_email_configured():
    EMAIL_CONFIG = ConnectionConfig(
        MAIL_USERNAME=MAIL_USERNAME,
        MAIL_PASSWORD=MAIL_PASSWORD,
        MAIL_FROM=MAIL_FROM,
        MAIL_PORT=MAIL_PORT,
        MAIL_SERVER=MAIL_SERVER,
        MAIL_FROM_NAME=MAIL_FROM_NAME,
        MAIL_STARTTLS=MAIL_STARTTLS,
        MAIL_SSL_TLS=MAIL_SSL_TLS,
        USE_CREDENTIALS=USE_CREDENTIALS,
        VALIDATE_CERTS=VALIDATE_CERTS,
    )
else:
    EMAIL_CONFIG = None

# Primary PostgreSQL: app_config (development = local POSTGRES_*; production = DATABASE_URL on Heroku).

# Census Database Configuration (for CNIC usage checks)
CENSUS_HOST = os.getenv("CENSUS_HOST", "jamat-postgres.postgres.database.azure.com")
CENSUS_USER = os.getenv("CENSUS_USER", "postgresadmin")
CENSUS_PASSWORD = os.getenv("CENSUS_PASSWORD", "wuFdyv-zorruk-gokni2")
CENSUS_DB = os.getenv("CENSUS_DB", "census_db_updated")
CENSUS_PORT = os.getenv("CENSUS_PORT", "5432")

CENSUS_DATABASE_URL = (
    f"postgresql+asyncpg://{CENSUS_USER}:{CENSUS_PASSWORD}"
    f"@{CENSUS_HOST}:{CENSUS_PORT}/{CENSUS_DB}"
)

# Browser origins allowed to call this API. CRA (`npm start`) is :3000 — local FastAPI
# (e.g. :8001) is not an "origin" for CORS. When the built UI and API are on different
# hosts, add the UI origin(s) in CORS_ORIGINS (e.g. on Heroku: your Vercel/Netlify URL).
_cors_base = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    # Heroku is accessible via both http and https depending on how the UI is loaded.
    "http://northen-volunteer-25070e7d956a.herokuapp.com",
    "https://northen-volunteer-25070e7d956a.herokuapp.com",
]
_cors_extra = [o.strip() for o in (os.getenv("CORS_ORIGINS") or "").split(",") if o.strip()]
CORS_ALLOW_ORIGINS = list(dict.fromkeys(_cors_base + _cors_extra))

# Public base URL for Swagger "Try it out" (override with PUBLIC_API_BASE_URL, e.g. Vercel talks to Heroku).
_DEFAULT_PUBLIC_PROD = "https://northen-volunteer-25070e7d956a.herokuapp.com"
if os.getenv("PUBLIC_API_BASE_URL", "").strip():
    _PUBLIC_BASE = os.getenv("PUBLIC_API_BASE_URL", "").strip().rstrip("/")
elif IS_DEVELOPMENT:
    _dev_port = os.getenv("PORT", "8001")
    _PUBLIC_BASE = f"http://127.0.0.1:{_dev_port}"
else:
    _PUBLIC_BASE = _DEFAULT_PUBLIC_PROD.rstrip("/")

_OPENAPI_LOCAL = f"http://127.0.0.1:{os.getenv('PORT', '8001')}"
_OPENAPI_SERVERS = (
    [
        {"url": _PUBLIC_BASE, "description": "This environment (default: local Postgres in development)"},
        {"url": _DEFAULT_PUBLIC_PROD, "description": "Production API (Heroku)"},
    ]
    if IS_DEVELOPMENT
    else [
        {"url": _PUBLIC_BASE, "description": "Production API (Heroku)"},
        {"url": _OPENAPI_LOCAL, "description": "Local (development)"},
    ]
)

app = FastAPI(
    title="Jamat Khana / Volunteer API",
    version="1.0",
    description=(
        "Volunteer management and Jamat Khana event APIs. "
        "**ReDoc:** `/redoc` — **OpenAPI JSON:** `/openapi.json`. "
        "Authenticate via `POST /api/volunteers/auth/login`, then **Authorize** in Swagger for Bearer tokens."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    servers=_OPENAPI_SERVERS,
)


# ============================================
# REQUEST LOGGING + REQUEST ID MIDDLEWARE
# Every incoming request gets a unique request_id which is:
#   - written to request.state.request_id (so endpoints can read it)
#   - returned in the X-Request-ID response header
#   - included in the access log line
# Any uncaught exception is logged via ErrorLogger and returned as a
# structured JSON error so the frontend can display the same code/id
# the support team has on file.
# ============================================

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Reuse caller-supplied id when present (helps cross-service tracing).
        incoming_id = request.headers.get("x-request-id")
        request_id = incoming_id or str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        client_host = request.client.host if request.client else "-"
        logger.info(
            f"[{request_id}] --> {request.method} {request.url.path} from {client_host}"
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                f"[{request_id}] !! {request.method} {request.url.path} crashed after {elapsed_ms:.1f}ms"
            )
            # Best-effort persistence of the unhandled error.
            try:
                async with async_session() as session:
                    await ErrorLogger.log_error(
                        db=session,
                        code=ErrorCode.UNHANDLED_EXCEPTION,
                        message=f"Unhandled exception: {type(exc).__name__}: {exc}",
                        status_code=500,
                        severity=ErrorSeverity.CRITICAL,
                        details={
                            "path": request.url.path,
                            "method": request.method,
                        },
                        request_id=request_id,
                        request=request,
                        exc=exc,
                    )
            except Exception:
                logger.exception(f"[{request_id}] failed to persist unhandled exception")

            return JSONResponse(
                status_code=500,
                content={
                    "errorCode": ErrorCode.UNHANDLED_EXCEPTION.value,
                    "message": "An unexpected error occurred. Please contact support with the request id.",
                    "requestId": request_id,
                },
                headers={"X-Request-ID": request_id},
            )

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            f"[{request_id}] <-- {request.method} {request.url.path} "
            f"status={response.status_code} time={elapsed_ms:.1f}ms"
        )
        return response


app.add_middleware(RequestContextMiddleware)

# Put CORSMiddleware last so it is outermost. This ensures CORS headers are present
# even when RequestContextMiddleware returns an error response.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# ============================================
# GLOBAL EXCEPTION HANDLERS
# ============================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", None)

    # If endpoints raise HTTPException(detail={"errorCode": ...}) the body
    # is already structured - just enrich and pass it through.
    if isinstance(exc.detail, dict):
        body = dict(exc.detail)
        body.setdefault("requestId", request_id)
        body.setdefault("message", body.get("message") or "Request failed")
        body.setdefault("errorCode", body.get("errorCode") or "INTERNAL_ERROR")
    else:
        body = {
            "errorCode": "HTTP_" + str(exc.status_code),
            "message": str(exc.detail) if exc.detail else "Request failed",
            "requestId": request_id,
        }

    # 4xx -> warning, 5xx -> error in the file logs.
    log_level = logging.WARNING if exc.status_code < 500 else logging.ERROR
    logger.log(
        log_level,
        f"[{request_id}] HTTPException {exc.status_code} on {request.method} {request.url.path}: {body.get('message')}",
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        headers={"X-Request-ID": request_id} if request_id else None,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)
    logger.warning(
        f"[{request_id}] Validation failed on {request.method} {request.url.path}: {exc.errors()}"
    )
    # Optional DB log (adds a round trip per 422; off by default for latency).
    if (os.getenv("LOG_VALIDATION_ERRORS_TO_DB", "").strip().lower() in ("1", "true", "yes")):
        try:
            async with async_session() as session:
                await ErrorLogger.log_error(
                    db=session,
                    code=ErrorCode.VALIDATION_ERROR,
                    message="Request validation failed",
                    status_code=422,
                    severity=ErrorSeverity.WARNING,
                    details={"errors": exc.errors(), "path": request.url.path},
                    request_id=request_id,
                    request=request,
                )
        except Exception:
            logger.exception(f"[{request_id}] failed to persist validation error")

    return JSONResponse(
        status_code=422,
        content={
            "errorCode": ErrorCode.VALIDATION_ERROR.value,
            "message": "Request validation failed",
            "requestId": request_id,
            "errors": exc.errors(),
        },
        headers={"X-Request-ID": request_id} if request_id else None,
    )


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# OpenAPI "Authorize" still uses /login (OAuth2 form); route is hidden from the docs list.
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
    connect_args=db_engine_connect_args(),
    echo=SQLALCHEMY_ECHO,
    pool_size=20,
    max_overflow=40,
    pool_timeout=60,
    pool_pre_ping=True,
    pool_recycle=DB_POOL_RECYCLE,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

volunteer_engine = engine
volunteer_async_session = async_session

# Census database engine
census_engine = create_async_engine(
    CENSUS_DATABASE_URL,
    echo=SQLALCHEMY_ECHO,
    pool_size=20,
    max_overflow=40,
    pool_timeout=60,
    pool_pre_ping=True,
    pool_recycle=DB_POOL_RECYCLE,
)
census_async_session = async_sessionmaker(census_engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session() as session:
        yield session


async def get_volunteer_db():
    async with volunteer_async_session() as session:
        yield session


async def get_census_db():
    async with census_async_session() as session:
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


@app.post("/login", response_model=Token, include_in_schema=False)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_volunteer_db),
):
    request_id = getattr(request.state, "request_id", None)
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        await ErrorLogger.log_error(
            db=db,
            code=ErrorCode.INVALID_CREDENTIALS,
            message="Incorrect email or password",
            status_code=400,
            severity=ErrorSeverity.WARNING,
            details={"email": form_data.username},
            request_id=request_id,
            request=request,
        )
        raise HTTPException(
            status_code=400,
            detail={
                "errorCode": ErrorCode.INVALID_CREDENTIALS.value,
                "message": "Incorrect email or password",
                "requestId": request_id,
            },
        )
    if not user.IsActive:
        await ErrorLogger.log_error(
            db=db,
            code=ErrorCode.ACCOUNT_INACTIVE,
            message="User account is inactive",
            status_code=401,
            severity=ErrorSeverity.WARNING,
            details={"email": form_data.username, "user_id": user.Id},
            request_id=request_id,
            user_id=user.Id,
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "errorCode": ErrorCode.ACCOUNT_INACTIVE.value,
                "message": "User account is inactive",
                "requestId": request_id,
            },
        )

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


@app.post("/login-json", response_model=Token, include_in_schema=False)
async def login_json(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_volunteer_db),
):
    request_id = getattr(request.state, "request_id", None)
    row = await _get_user_row_by_email(db, payload.email)
    if not row or not verify_password(payload.password, row.get("password_hash")):
        await ErrorLogger.log_error(
            db=db,
            code=ErrorCode.INVALID_CREDENTIALS,
            message="Incorrect email or password",
            status_code=400,
            severity=ErrorSeverity.WARNING,
            details={"email": payload.email, "user_exists": bool(row)},
            request_id=request_id,
            request=request,
        )
        raise HTTPException(
            status_code=400,
            detail={
                "errorCode": ErrorCode.INVALID_CREDENTIALS.value,
                "message": "Incorrect email or password",
                "requestId": request_id,
            },
        )
    if not row.get("is_active"):
        await ErrorLogger.log_error(
            db=db,
            code=ErrorCode.ACCOUNT_INACTIVE,
            message="User account is inactive",
            status_code=401,
            severity=ErrorSeverity.WARNING,
            details={"email": payload.email, "user_id": row.get("id")},
            request_id=request_id,
            user_id=row.get("id"),
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "errorCode": ErrorCode.ACCOUNT_INACTIVE.value,
                "message": "User account is inactive",
                "requestId": request_id,
            },
        )

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


@app.post("/refresh", response_model=Token, include_in_schema=False)
async def refresh_token(
    request: Request,
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_volunteer_db),
):
    request_id = getattr(request.state, "request_id", None)
    try:
        payload = jwt.decode(token_data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            await ErrorLogger.log_error(
                db=db,
                code=ErrorCode.TOKEN_INVALID,
                message="Refresh failed: invalid token type",
                status_code=400,
                severity=ErrorSeverity.WARNING,
                details={"token_type": payload.get("type")},
                request_id=request_id,
                request=request,
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "errorCode": ErrorCode.TOKEN_INVALID.value,
                    "message": "Invalid token type",
                    "requestId": request_id,
                },
            )
        email = payload.get("email")
        if email is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "errorCode": ErrorCode.TOKEN_INVALID.value,
                    "message": "Invalid refresh token",
                    "requestId": request_id,
                },
            )

        row = await _get_user_row_by_email(db, email)
        if row is None:
            await ErrorLogger.log_error(
                db=db,
                code=ErrorCode.USER_NOT_FOUND,
                message="Refresh failed: user not found",
                status_code=400,
                severity=ErrorSeverity.WARNING,
                details={"email": email},
                request_id=request_id,
                request=request,
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "errorCode": ErrorCode.USER_NOT_FOUND.value,
                    "message": "User not found",
                    "requestId": request_id,
                },
            )
        if not row.get("is_active"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "errorCode": ErrorCode.ACCOUNT_INACTIVE.value,
                    "message": "User account is inactive",
                    "requestId": request_id,
                },
            )

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
        await ErrorLogger.log_error(
            db=db,
            code=ErrorCode.TOKEN_EXPIRED,
            message="Refresh token has expired",
            status_code=401,
            severity=ErrorSeverity.WARNING,
            request_id=request_id,
            request=request,
        )
        raise HTTPException(
            status_code=401,
            detail={
                "errorCode": ErrorCode.TOKEN_EXPIRED.value,
                "message": "Refresh token has expired",
                "requestId": request_id,
            },
        )
    except jwt.PyJWTError as exc:
        await ErrorLogger.log_error(
            db=db,
            code=ErrorCode.TOKEN_INVALID,
            message=f"Invalid refresh token: {exc}",
            status_code=401,
            severity=ErrorSeverity.WARNING,
            request_id=request_id,
            request=request,
            exc=exc,
        )
        raise HTTPException(
            status_code=401,
            detail={
                "errorCode": ErrorCode.TOKEN_INVALID.value,
                "message": "Invalid refresh token",
                "requestId": request_id,
            },
        )


from volunteer_auth import router as volunteer_auth_router, set_database_dependency as set_auth_db_dep
import volunteer_api_v2
from error_admin_routes import (
    admin_error_router,
    set_database_dependency as set_admin_error_db_dep,
)

set_auth_db_dep(get_volunteer_db)
volunteer_api_v2.set_database_dependencies(get_volunteer_db, get_db, get_census_db)
set_admin_error_db_dep(get_volunteer_db)

app.include_router(volunteer_auth_router)
app.include_router(volunteer_api_v2.volunteer_router, dependencies=[Depends(get_current_user)])
# Include the CNIC check router without authentication
app.include_router(volunteer_api_v2.cnic_router)
# Admin / support endpoints (require authentication).
app.include_router(admin_error_router, dependencies=[Depends(get_current_user)])


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "healthy"}


@app.get("/debug/config", include_in_schema=False)
async def debug_config():
    return {
        "APP_ENV": APP_ENV,
        "is_production": IS_PRODUCTION,
        "is_development": IS_DEVELOPMENT,
        "use_remote_database": USE_REMOTE_DATABASE,
        "POSTGRES_HOST": POSTGRES_HOST,
        "POSTGRES_DB": POSTGRES_DB,
        "POSTGRES_PORT": POSTGRES_PORT,
        "POSTGRES_USER": POSTGRES_USER,
        "database_url_prefix": (DATABASE_URL[:50] + "...") if len(DATABASE_URL) > 50 else DATABASE_URL,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")))
