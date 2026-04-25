# ============================================
# ERROR LOGGING AND HANDLING MODULE
# error_logging.py
# ============================================

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCode(str, Enum):
    """Application error codes"""
    # Validation errors
    CNIC_NOT_FOUND = "CNIC_NOT_FOUND"
    CNIC_INVALID = "CNIC_INVALID"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    DISCREPANT_RECORD = "DISCREPANT_RECORD"
    
    # Authorization errors
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    
    # Database errors
    DB_CONNECTION_FAILED = "DB_CONNECTION_FAILED"
    DB_QUERY_FAILED = "DB_QUERY_FAILED"
    DB_INSERT_FAILED = "DB_INSERT_FAILED"
    
    # Business logic errors
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    VOLUNTEER_NOT_FOUND = "VOLUNTEER_NOT_FOUND"
    EVENT_NOT_FOUND = "EVENT_NOT_FOUND"
    
    # Generic errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class ErrorLogger:
    """Centralized error logging system"""
    
    @staticmethod
    async def log_error(
        db: AsyncSession,
        code: ErrorCode,
        message: str,
        status_code: int = 400,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> int:
        """
        Log error to database
        
        Args:
            db: Database session
            code: Error code enum
            message: Human-readable error message
            status_code: HTTP status code
            severity: Severity level
            details: Additional error details (JSON serializable)
            request_id: Request tracking ID
            
        Returns:
            Error ID from database
        """
        try:
            # Check if error code already exists
            check_sql = text("""
                SELECT id FROM error_codes 
                WHERE code = :code
            """)
            
            result = await db.execute(check_sql, {"code": code.value})
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing error record
                update_sql = text("""
                    UPDATE error_codes
                    SET status = :status,
                        severity = :severity,
                        message = :message,
                        details = :details
                    WHERE code = :code
                    RETURNING id
                """)
                
                result = await db.execute(
                    update_sql,
                    {
                        "code": code.value,
                        "status": status_code,
                        "severity": severity.value,
                        "message": message,
                        "details": str(details) if details else None
                    }
                )
                error_id = result.scalar()
            else:
                # Insert new error record
                insert_sql = text("""
                    INSERT INTO error_codes (code, status, severity, message, details)
                    VALUES (:code, :status, :severity, :message, :details)
                    RETURNING id
                """)
                
                result = await db.execute(
                    insert_sql,
                    {
                        "code": code.value,
                        "status": status_code,
                        "severity": severity.value,
                        "message": message,
                        "details": str(details) if details else None
                    }
                )
                error_id = result.scalar()
            
            await db.commit()
            
            # Log to application logger
            logger.log(
                level=_severity_to_log_level(severity),
                msg=f"[{code.value}] {message}",
                extra={
                    "error_code": code.value,
                    "status_code": status_code,
                    "request_id": request_id,
                    "error_id": error_id,
                    "details": details
                }
            )
            
            return error_id
            
        except Exception as e:
            logger.exception(f"Failed to log error: {str(e)}")
            return -1


async def log_and_raise_error(
    db: AsyncSession,
    code: ErrorCode,
    message: str,
    status_code: int = 400,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> None:
    """
    Log error and raise HTTPException
    
    Convenience function that logs to database and raises HTTP exception
    """
    await ErrorLogger.log_error(
        db=db,
        code=code,
        message=message,
        status_code=status_code,
        severity=severity,
        details=details,
        request_id=request_id
    )
    
    raise HTTPException(status_code=status_code, detail=message)


def _severity_to_log_level(severity: ErrorSeverity) -> int:
    """Convert ErrorSeverity to Python logging level"""
    mapping = {
        ErrorSeverity.INFO: logging.INFO,
        ErrorSeverity.WARNING: logging.WARNING,
        ErrorSeverity.ERROR: logging.ERROR,
        ErrorSeverity.CRITICAL: logging.CRITICAL
    }
    return mapping.get(severity, logging.ERROR)
