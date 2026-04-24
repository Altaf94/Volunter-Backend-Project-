import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

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
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check existing
    q = await db.execute(text("SELECT id, email FROM users WHERE email = :email"), {"email": payload.email})
    if q.first():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    password_hash = pwd_context.hash(payload.password)
    now = datetime.utcnow()
    # Validate role_id: required and must exist in roles table
    role_id_val = payload.role_id
    try:
        role_q = await db.execute(text("SELECT id FROM roles WHERE id = :id"), {"id": role_id_val})
        if not role_q.first():
            raise HTTPException(status_code=400, detail=f"Role id {role_id_val} not found")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to validate role_id")

    # Validate scope: required and must be 'national' or 'regional'
    if payload.scope not in ("national", "regional"):
        raise HTTPException(status_code=400, detail="Invalid scope; must be 'national' or 'regional'")
    scope_val = payload.scope

    # Accept region_id as provided (required). regions table may not exist; store numeric id.
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
    result = await db.execute(insert_sql, params)
    await db.commit()
    row = result.first()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create user")
    return {"id": row[0], "email": row[1], "full_name": row[2]}


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    q = await db.execute(text("SELECT id, email, password_hash, full_name, role_id, scope, region_id, is_active FROM users WHERE email = :email"), {"email": payload.email})
    row = q.first()
    if not row:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    user_id, email, password_hash, full_name, role_id, scope, region_id, is_active = row
    if not is_active:
        raise HTTPException(status_code=401, detail="User account is inactive")
    if not pwd_context.verify(payload.password, password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

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
async def refresh_token(token_data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(token_data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
        email = payload.get("email")
        if email is None:
            raise HTTPException(status_code=400, detail="Invalid refresh token")

        q = await db.execute(text("SELECT id, email, full_name, role_id, scope, region_id, is_active FROM users WHERE email = :email"), {"email": email})
        row = q.first()
        if not row:
            raise HTTPException(status_code=400, detail="User not found")
        user_id, email, full_name, role_id, scope, region_id, is_active = row
        if not is_active:
            raise HTTPException(status_code=401, detail="User account is inactive")

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        claims = {"sub": email, "id": user_id, "role": role_id, "name": full_name, "scope": scope, "region_id": region_id}
        access_token = create_access_token(data=claims, expires_delta=access_token_expires)
        refresh_token_val = create_refresh_token(data={"email": email, "id": user_id, "role": role_id, "name": full_name})

        return {"access_token": access_token, "refresh_token": refresh_token_val, "token_type": "bearer"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
