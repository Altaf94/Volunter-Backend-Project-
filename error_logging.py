# ============================================
# ERROR LOGGING AND HANDLING MODULE
# error_logging.py
#
# Two tables involved:
#   error_codes  - registry / dictionary of all known error codes
#                  (id, code UNIQUE, status, severity, message, details)
#   error_logs   - per-occurrence audit log
#                  (id, request_id, error_code, http_status, severity,
#                   message, details JSONB, user_id, endpoint, http_method,
#                   client_ip, user_agent, stack_trace, created_at)
#
# Run add_error_logging_tables.sql once to create error_logs and seed
# error_codes.
# ============================================

import json
import logging
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------

class ErrorSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCode(str, Enum):
    """Application error codes. Keep in sync with the error_codes table."""

    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CNIC_INVALID = "CNIC_INVALID"
    CNIC_NOT_FOUND = "CNIC_NOT_FOUND"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    DISCREPANT_RECORD = "DISCREPANT_RECORD"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    MISSING_FIELD = "MISSING_FIELD"

    # Auth
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    FORBIDDEN = "FORBIDDEN"

    # Resource lookup
    VOLUNTEER_NOT_FOUND = "VOLUNTEER_NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    EVENT_NOT_FOUND = "EVENT_NOT_FOUND"
    ACCESS_LEVEL_NOT_FOUND = "ACCESS_LEVEL_NOT_FOUND"
    DUTY_TYPE_NOT_FOUND = "DUTY_TYPE_NOT_FOUND"
    IMPORT_FILE_NOT_FOUND = "IMPORT_FILE_NOT_FOUND"
    NOT_FOUND = "NOT_FOUND"

    # Conflict / business rules
    DUPLICATE_USER = "DUPLICATE_USER"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    PRINTED_BADGE_LOCKED = "PRINTED_BADGE_LOCKED"

    # Database / infrastructure
    DB_CONNECTION_FAILED = "DB_CONNECTION_FAILED"
    DB_QUERY_FAILED = "DB_QUERY_FAILED"
    DB_INSERT_FAILED = "DB_INSERT_FAILED"
    DB_UPDATE_FAILED = "DB_UPDATE_FAILED"
    DB_DELETE_FAILED = "DB_DELETE_FAILED"
    DB_INTEGRITY_ERROR = "DB_INTEGRITY_ERROR"

    # External
    CENSUS_DB_ERROR = "CENSUS_DB_ERROR"
    EMAIL_SEND_FAILED = "EMAIL_SEND_FAILED"

    # Generic
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNHANDLED_EXCEPTION = "UNHANDLED_EXCEPTION"


_SEVERITY_TO_LEVEL = {
    ErrorSeverity.INFO: logging.INFO,
    ErrorSeverity.WARNING: logging.WARNING,
    ErrorSeverity.ERROR: logging.ERROR,
    ErrorSeverity.CRITICAL: logging.CRITICAL,
}


def _severity_to_log_level(severity: ErrorSeverity) -> int:
    return _SEVERITY_TO_LEVEL.get(severity, logging.ERROR)


def _safe_json(value: Any) -> Optional[str]:
    """Serialize a value to JSON; falls back to str() for non-serialisable objects."""
    if value is None:
        return None
    try:
        return json.dumps(value, default=str)
    except Exception:
        try:
            return json.dumps(str(value))
        except Exception:
            return None


def _request_meta(request: Optional[Request]) -> Dict[str, Optional[str]]:
    """Extract endpoint/method/client_ip/user_agent from a FastAPI Request."""
    if request is None:
        return {
            "endpoint": None,
            "http_method": None,
            "client_ip": None,
            "user_agent": None,
        }
    try:
        client_host = request.client.host if request.client else None
    except Exception:
        client_host = None
    try:
        ua = request.headers.get("user-agent")
    except Exception:
        ua = None
    try:
        path = request.url.path
    except Exception:
        path = None
    try:
        method = request.method
    except Exception:
        method = None
    return {
        "endpoint": path,
        "http_method": method,
        "client_ip": client_host,
        "user_agent": (ua[:512] if ua else None),
    }


# ---------------------------------------------------------------------
# Core logger
# ---------------------------------------------------------------------

class ErrorLogger:
    """Centralised error logging.

    Writes one row per occurrence into `error_logs` and ensures the code
    exists in the `error_codes` registry. Always also logs to the Python
    logger so the error appears in the file logs.
    """

    @staticmethod
    async def log_error(
        db: Optional[AsyncSession],
        code: ErrorCode,
        message: str,
        status_code: int = 400,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        user_id: Optional[int] = None,
        request: Optional[Request] = None,
        exc: Optional[BaseException] = None,
    ) -> Optional[int]:
        """Persist an error occurrence.

        Returns the inserted error_logs id, or None if persistence failed.
        Never raises - logging must never break a request.
        """

        # Always log to file/console first so we never lose information
        # even if the database is unreachable.
        log_extra = {
            "error_code": code.value,
            "http_status": status_code,
            "request_id": request_id,
            "user_id": user_id,
            "details": details,
        }
        try:
            logger.log(
                level=_severity_to_log_level(severity),
                msg=f"[{request_id or '-'}] [{code.value}] {message}",
                extra=log_extra,
            )
            if exc is not None:
                logger.log(
                    level=_severity_to_log_level(severity),
                    msg=f"[{request_id or '-'}] traceback for {code.value}",
                    exc_info=(type(exc), exc, exc.__traceback__),
                )
        except Exception:
            # Logger itself failed - swallow to avoid recursive errors.
            pass

        if db is None:
            return None

        meta = _request_meta(request)
        stack = None
        if exc is not None:
            try:
                stack = "".join(
                    traceback.format_exception(type(exc), exc, exc.__traceback__)
                )
            except Exception:
                stack = None

        details_json = _safe_json(details)

        try:
            # 1. Make sure the registry entry exists (lookup or create).
            registry_id = await ErrorLogger._ensure_registry(
                db=db,
                code=code,
                http_status=status_code,
                severity=severity,
                message=message,
            )

            # 2. Insert the per-occurrence row.
            insert_sql = text(
                """
                INSERT INTO error_logs
                    (request_id, error_code, error_code_id, http_status, severity,
                     message, details, user_id, endpoint, http_method,
                     client_ip, user_agent, stack_trace, created_at)
                VALUES
                    (:request_id, :error_code, :error_code_id, :http_status, :severity,
                     :message, CAST(:details AS JSONB), :user_id, :endpoint, :http_method,
                     :client_ip, :user_agent, :stack_trace, :created_at)
                RETURNING id
                """
            )
            params = {
                "request_id": request_id,
                "error_code": code.value,
                "error_code_id": registry_id,
                "http_status": status_code,
                "severity": severity.value,
                "message": message,
                "details": details_json,
                "user_id": user_id,
                "endpoint": meta["endpoint"],
                "http_method": meta["http_method"],
                "client_ip": meta["client_ip"],
                "user_agent": meta["user_agent"],
                "stack_trace": stack,
                "created_at": datetime.utcnow(),
            }
            result = await db.execute(insert_sql, params)
            log_id = result.scalar()
            await db.commit()
            return log_id
        except Exception as persist_exc:
            # Don't let logging take down the request. Make sure the
            # session is usable for the caller's own rollback.
            try:
                await db.rollback()
            except Exception:
                pass
            logger.exception(
                f"[{request_id or '-'}] Failed to persist error log for {code.value}: {persist_exc}"
            )
            return None

    @staticmethod
    async def _ensure_registry(
        db: AsyncSession,
        code: ErrorCode,
        http_status: int,
        severity: ErrorSeverity,
        message: str,
    ) -> Optional[int]:
        """Look up `code` in error_codes; insert it if missing. Returns id."""
        try:
            select_sql = text("SELECT id FROM error_codes WHERE code = :code")
            res = await db.execute(select_sql, {"code": code.value})
            existing_id = res.scalar_one_or_none()
            if existing_id is not None:
                return existing_id

            insert_sql = text(
                """
                INSERT INTO error_codes (code, status, severity, message, details)
                VALUES (:code, :st, :severity, :message, :details)
                ON CONFLICT (code) DO UPDATE
                    SET status = EXCLUDED.status
                RETURNING id
                """
            )
            res = await db.execute(
                insert_sql,
                {
                    "code": code.value,
                    "st": http_status,
                    "severity": severity.value,
                    "message": message[:255] if message else code.value,
                    "details": "auto-registered on first occurrence",
                },
            )
            return res.scalar()
        except Exception as ex:
            logger.warning(f"Could not ensure error_codes registry for {code.value}: {ex}")
            return None


# ---------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------

async def log_and_raise_error(
    db: Optional[AsyncSession],
    code: ErrorCode,
    message: str,
    status_code: int = 400,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    user_id: Optional[int] = None,
    request: Optional[Request] = None,
    exc: Optional[BaseException] = None,
) -> None:
    """Log to DB + file logs, then raise an HTTPException.

    The HTTPException `detail` is a structured dict so the frontend can
    render the same `errorCode` we just persisted.
    """
    await ErrorLogger.log_error(
        db=db,
        code=code,
        message=message,
        status_code=status_code,
        severity=severity,
        details=details,
        request_id=request_id,
        user_id=user_id,
        request=request,
        exc=exc,
    )
    raise HTTPException(
        status_code=status_code,
        detail={
            "errorCode": code.value,
            "message": message,
            "requestId": request_id,
        },
    )


async def log_exception(
    db: Optional[AsyncSession],
    exc: BaseException,
    code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    message: Optional[str] = None,
    status_code: int = 500,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    user_id: Optional[int] = None,
    request: Optional[Request] = None,
) -> Optional[int]:
    """Convenience wrapper used inside `except` blocks."""
    final_message = message or f"{type(exc).__name__}: {exc}"
    return await ErrorLogger.log_error(
        db=db,
        code=code,
        message=final_message,
        status_code=status_code,
        severity=severity,
        details=details,
        request_id=request_id,
        user_id=user_id,
        request=request,
        exc=exc,
    )
