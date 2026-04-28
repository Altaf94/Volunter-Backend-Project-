"""
Application environment and primary database settings.

- Development: local PostgreSQL via POSTGRES_* in .env (default when not on Heroku).
- Production: Heroku sets DYNO and DATABASE_URL; optional explicit APP_ENV=production.

To point local dev at the Heroku DB: set USE_HEROKU_DB=true and DATABASE_URL in .env.
"""

from __future__ import annotations

import os
import ssl
from pathlib import Path

from dotenv import load_dotenv

_PROJ = Path(__file__).resolve().parent
_DEFAULT_RDS_CA = _PROJ / "certs" / "rds-global-bundle.pem"

load_dotenv()


def env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


_raw_app_env = (os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "").strip().lower()
if not _raw_app_env:
    APP_ENV = "production" if os.environ.get("DYNO") else "development"
elif _raw_app_env in ("dev", "development", "local"):
    APP_ENV = "development"
elif _raw_app_env in ("prod", "production"):
    APP_ENV = "production"
else:
    APP_ENV = _raw_app_env

IS_PRODUCTION = APP_ENV == "production"
IS_DEVELOPMENT = APP_ENV == "development"

# Primary DB — local (development default)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "northenvolunteerdb")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")


def _local_database_url() -> str:
    return (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )


def _normalize_asyncpg_url(raw: str) -> str:
    _raw = raw.strip()
    if _raw.startswith("postgres://"):
        return _raw.replace("postgres://", "postgresql+asyncpg://", 1)
    if _raw.startswith("postgresql://") and "+asyncpg" not in _raw:
        return _raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    return _raw


# Use local DB in development unless explicitly opting in to Heroku/remote URL.
if IS_DEVELOPMENT and not env_flag("USE_HEROKU_DB"):
    DATABASE_URL = _local_database_url()
    USE_REMOTE_DATABASE = False
elif os.getenv("DATABASE_URL"):
    DATABASE_URL = _normalize_asyncpg_url(os.environ["DATABASE_URL"])
    USE_REMOTE_DATABASE = True
else:
    DATABASE_URL = _local_database_url()
    USE_REMOTE_DATABASE = False


# asyncpg: Heroku / managed Postgres URLs need TLS; local Docker/host Postgres usually does not.
def should_use_db_ssl() -> bool:
    if env_flag("DATABASE_SSL") or env_flag("USE_DATABASE_SSL"):
        return True
    if not USE_REMOTE_DATABASE:
        return False
    u = DATABASE_URL.lower()
    if "localhost" in u or "127.0.0.1" in u:
        return False
    if os.environ.get("DYNO") and os.getenv("DATABASE_URL"):
        return True
    if any(
        s in u
        for s in (
            "amazonaws.com",
            "herokudns.com",
            "heroku",
            "cockroach",
            "neon.tech",
        )
    ):
        return True
    return False


def _resolve_ssl_ca_path() -> str | None:
    for key in ("POSTGRES_SSL_ROOTCERT", "DATABASE_SSL_CA"):
        raw = (os.getenv(key) or "").strip()
        if not raw:
            continue
        p = Path(raw)
        if not p.is_absolute():
            p = _PROJ / raw
        if p.is_file():
            return str(p)
    if _DEFAULT_RDS_CA.is_file():
        return str(_DEFAULT_RDS_CA)
    return None


def _ssl_value_for_asyncpg() -> bool | ssl.SSLContext:
    """asyncpg: bool or SSLContext. RDS needs the AWS CA bundle; plain True often fails on macOS."""
    if env_flag("POSTGRES_SSL_INSECURE") or env_flag("DATABASE_SSL_INSECURE"):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    ca = _resolve_ssl_ca_path()
    if ca:
        return ssl.create_default_context(cafile=ca)
    return True


def db_engine_connect_args() -> dict:
    if not should_use_db_ssl():
        return {}
    return {"ssl": _ssl_value_for_asyncpg()}


# Off by default (fast). Set SQL_ECHO=1 to log every statement when debugging.
if os.getenv("SQL_ECHO") is not None:
    SQLALCHEMY_ECHO = env_flag("SQL_ECHO")
else:
    SQLALCHEMY_ECHO = False

# Recycle pool connections so RDS/idle timeout does not hand out dead sockets.
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "300"))
