import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from error_logging import ErrorCode, ErrorLogger, ErrorSeverity

logger = logging.getLogger(__name__)


def _request_id(request: Optional[Request]) -> str:
    if request is None:
        return str(uuid.uuid4())
    rid = getattr(request.state, "request_id", None) if hasattr(request, "state") else None
    return rid or str(uuid.uuid4())


def _err(error_code: ErrorCode, message: str, request_id: str, status_code: int):
    return HTTPException(
        status_code=status_code,
        detail={
            "errorCode": error_code.value,
            "message": message,
            "requestId": request_id,
        },
    )

# Load config from env
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/api/volunteers/auth", tags=["Volunteer Auth"])

# Database dependency will be set by main.py using set_database_dependency
_get_db = None


def set_database_dependency(db_func):
    global _get_db
    _get_db = db_func


async def get_db():
    if _get_db is None:
        raise RuntimeError("Database not configured for volunteer_auth")
    async for session in _get_db():
        yield session


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role_id: int
    scope: str
    region_id: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/register", response_model=dict)
async def register(
    request: Request,
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    request_id = _request_id(request)
    logger.info(f"[{request_id}] /auth/register email={payload.email} role_id={payload.role_id}")

    q = await db.execute(text("SELECT id, email FROM users WHERE email = :email"), {"email": payload.email})
    if q.first():
        await ErrorLogger.log_error(
            db=db,
            code=ErrorCode.DUPLICATE_USER,
            message="User with this email already exists",
            status_code=400,
            severity=ErrorSeverity.WARNING,
            details={"email": payload.email},
            request_id=request_id,
            request=request,
        )
        raise _err(ErrorCode.DUPLICATE_USER, "User with this email already exists", request_id, 400)

    password_hash = pwd_context.hash(payload.password)
    now = datetime.utcnow()

    role_id_val = payload.role_id
    try:
        role_q = await db.execute(text("SELECT id FROM roles WHERE id = :id"), {"id": role_id_val})
        if not role_q.first():
            await ErrorLogger.log_error(
                db=db,
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Role id {role_id_val} not found",
                status_code=400,
                severity=ErrorSeverity.WARNING,
                details={"role_id": role_id_val, "email": payload.email},
                request_id=request_id,
                request=request,
            )
            raise _err(ErrorCode.VALIDATION_ERROR, f"Role id {role_id_val} not found", request_id, 400)
    except HTTPException:
        raise
    except Exception as exc:
        await ErrorLogger.log_error(
            db=db,
            code=ErrorCode.DB_QUERY_FAILED,
            message=f"Failed to validate role_id: {exc}",
            status_code=400,
            severity=ErrorSeverity.ERROR,
            details={"role_id": role_id_val, "email": payload.email},
            request_id=request_id,
            request=request,
            exc=exc,
        )
        raise _err(ErrorCode.DB_QUERY_FAILED, "Failed to validate role_id", request_id, 400)

    if payload.scope not in ("national", "regional"):
        await ErrorLogger.log_error(
            db=db,
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid scope; must be 'national' or 'regional'",
            status_code=400,
            severity=ErrorSeverity.WARNING,
            details={"scope": payload.scope, "email": payload.email},
            request_id=request_id,
            request=request,
        )
        raise _err(
            ErrorCode.VALIDATION_ERROR,
            "Invalid scope; must be 'national' or 'regional'",
            request_id,
            400,
        )
    scope_val = payload.scope

    region_id_val = payload.region_id
    insert_sql = text(
        """
        INSERT INTO users (email, password_hash, full_name, role_id, scope, region_id, is_active, created_at, updated_at)
        VALUES (:email, :password_hash, :full_name, :role_id, :scope, :region_id, true, :created_at, :updated_at)
        RETURNING id, email, full_name, role_id, scope, region_id, is_active, created_at, updated_at
        """
    )
    params = {
        "email": payload.email,
        "password_hash": password_hash,
        "full_name": payload.full_name,
        "role_id": role_id_val,
        "scope": scope_val,
        "region_id": region_id_val,
        "created_at": now,
        "updated_at": now,
    }
    try:
        result = await db.execute(insert_sql, params)
        await db.commit()
        row = result.first()
    except Exception as exc:
        await db.rollback()
        await ErrorLogger.log_error(
            db=db,
            code=ErrorCode.DB_INSERT_FAILED,
            message=f"Failed to create user: {exc}",
            status_code=500,
            severity=ErrorSeverity.ERROR,
            details={"email": payload.email},
            request_id=request_id,
            request=request,
            exc=exc,
        )
        raise _err(ErrorCode.DB_INSERT_FAILED, "Failed to create user", request_id, 500)

    if not row:
        await ErrorLogger.log_error(
            db=db,
            code=ErrorCode.DB_INSERT_FAILED,
            message="User insert returned no row",
            status_code=500,
            severity=ErrorSeverity.ERROR,
            details={"email": payload.email},
            request_id=request_id,
            request=request,
        )
        raise _err(ErrorCode.DB_INSERT_FAILED, "Failed to create user", request_id, 500)

    logger.info(f"[{request_id}] /auth/register created user id={row[0]} email={row[1]}")
    return {"id": row[0], "email": row[1], "full_name": row[2], "requestId": request_id}


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    request_id = _request_id(request)
    logger.info(f"[{request_id}] /auth/login email={payload.email}")
    q = await db.execute(
        text(
            "SELECT id, email, password_hash, full_name, role_id, scope, region_id, is_active "
            "FROM users WHERE email = :email"
        ),
        {"email": payload.email},
    )
    row = q.first()
    if not row:
        await ErrorLogger.log_error(
            db=db,
            code=ErrorCode.INVALID_CREDENTIALS,
            message="Login failed: user not found",
            status_code=400,
            severity=ErrorSeverity.WARNING,
            details={"email": payload.email},
            request_id=request_id,
            request=request,
        )
        raise _err(ErrorCode.INVALID_CREDENTIALS, "Incorrect email or password", request_id, 400)
    user_id, email, password_hash, full_name, role_id, scope, region_id, is_active = row
    if not is_active:
        await ErrorLogger.log_error(
            db=db,
            code=ErrorCode.ACCOUNT_INACTIVE,
            message="Login failed: account inactive",
            status_code=401,
            severity=ErrorSeverity.WARNING,
            details={"email": email, "user_id": user_id},
            request_id=request_id,
            user_id=user_id,
            request=request,
        )
        raise _err(ErrorCode.ACCOUNT_INACTIVE, "User account is inactive", request_id, 401)
    if not pwd_context.verify(payload.password, password_hash):
        await ErrorLogger.log_error(
            db=db,
            code=ErrorCode.INVALID_CREDENTIALS,
            message="Login failed: bad password",
            status_code=400,
            severity=ErrorSeverity.WARNING,
            details={"email": email, "user_id": user_id},
            request_id=request_id,
            user_id=user_id,
            request=request,
        )
        raise _err(ErrorCode.INVALID_CREDENTIALS, "Incorrect email or password", request_id, 400)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Include scope and region_id in token claims so frontend gets user's scope/region
    claims = {"sub": email, "id": user_id, "role": role_id, "name": full_name, "scope": scope, "region_id": region_id}
    access_token = create_access_token(
        data=claims,
        expires_delta=access_token_expires,
    )
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_refresh_token(
        data={"email": email, "id": user_id, "role": role_id, "name": full_name},
        expires_delta=refresh_token_expires,
    )

    # update last_login
    try:
        await db.execute(text("UPDATE users SET last_login = :last_login, updated_at = :updated_at WHERE id = :id"), {"last_login": datetime.utcnow(), "updated_at": datetime.utcnow(), "id": user_id})
        await db.commit()
    except Exception:
        pass

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


# Refresh token endpoint so frontend can call /api/volunteers/auth/refresh
class TokenRefresh(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db),
):
    request_id = _request_id(request)
    try:
        payload = jwt.decode(token_data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            await ErrorLogger.log_error(
                db=db,
                code=ErrorCode.TOKEN_INVALID,
                message="Refresh failed: wrong token type",
                status_code=400,
                severity=ErrorSeverity.WARNING,
                details={"token_type": payload.get("type")},
                request_id=request_id,
                request=request,
            )
            raise _err(ErrorCode.TOKEN_INVALID, "Invalid token type", request_id, 400)
        email = payload.get("email")
        if email is None:
            raise _err(ErrorCode.TOKEN_INVALID, "Invalid refresh token", request_id, 400)

        q = await db.execute(
            text(
                "SELECT id, email, full_name, role_id, scope, region_id, is_active "
                "FROM users WHERE email = :email"
            ),
            {"email": email},
        )
        row = q.first()
        if not row:
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
            raise _err(ErrorCode.USER_NOT_FOUND, "User not found", request_id, 400)
        user_id, email, full_name, role_id, scope, region_id, is_active = row
        if not is_active:
            raise _err(ErrorCode.ACCOUNT_INACTIVE, "User account is inactive", request_id, 401)

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        claims = {"sub": email, "id": user_id, "role": role_id, "name": full_name, "scope": scope, "region_id": region_id}
        access_token = create_access_token(data=claims, expires_delta=access_token_expires)
        refresh_token_val = create_refresh_token(data={"email": email, "id": user_id, "role": role_id, "name": full_name})

        return {"access_token": access_token, "refresh_token": refresh_token_val, "token_type": "bearer"}
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError as exc:
        await ErrorLogger.log_error(
            db=db,
            code=ErrorCode.TOKEN_EXPIRED,
            message="Refresh token has expired",
            status_code=401,
            severity=ErrorSeverity.WARNING,
            request_id=request_id,
            request=request,
            exc=exc,
        )
        raise _err(ErrorCode.TOKEN_EXPIRED, "Refresh token has expired", request_id, 401)
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
        raise _err(ErrorCode.TOKEN_INVALID, "Invalid refresh token", request_id, 401)
