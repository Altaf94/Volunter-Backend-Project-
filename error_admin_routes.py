# ============================================
# ADMIN ENDPOINTS: query the error_logs table
# error_admin_routes.py
#
# Designed to give support / engineering instant visibility into what
# users are hitting in production:
#
#   GET /api/admin/errors                  list recent errors
#   GET /api/admin/errors/summary          counts by code/severity
#   GET /api/admin/errors/by-request/{id}  trace one request_id end-to-end
#   GET /api/admin/error-codes             show the error_codes registry
# ============================================

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


admin_error_router = APIRouter(prefix="/api/admin", tags=["Admin: Error Logs"])


_get_db = None


def set_database_dependency(db_func):
    global _get_db
    _get_db = db_func


async def _db_session():
    if _get_db is None:
        raise RuntimeError("Admin error router DB dependency not configured")
    async for session in _get_db():
        yield session


def _row_to_dict(row) -> dict:
    m = row._mapping
    out = {}
    for k, v in m.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


@admin_error_router.get("/errors")
async def list_errors(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    severity: Optional[str] = Query(None, description="filter by severity: info|warning|error|critical"),
    code: Optional[str] = Query(None, description="filter by error code"),
    user_id: Optional[int] = Query(None, description="filter by user id"),
    request_id: Optional[str] = Query(None, description="filter by request id"),
    since_minutes: Optional[int] = Query(
        None, description="only rows newer than now() - <since_minutes> minutes"
    ),
    db: AsyncSession = Depends(_db_session),
):
    """List the most recent error_logs rows with simple filters."""
    where = []
    params: dict = {"limit": limit, "offset": offset}
    if severity:
        where.append("severity = :severity")
        params["severity"] = severity
    if code:
        where.append("error_code = :code")
        params["code"] = code
    if user_id is not None:
        where.append("user_id = :user_id")
        params["user_id"] = user_id
    if request_id:
        where.append("request_id = :request_id")
        params["request_id"] = request_id
    if since_minutes is not None:
        where.append("created_at >= NOW() - (:since_minutes::int * INTERVAL '1 minute')")
        params["since_minutes"] = since_minutes

    where_clause = ("WHERE " + " AND ".join(where)) if where else ""
    sql = text(
        f"""
        SELECT id, request_id, error_code, http_status, severity, message, details,
               user_id, endpoint, http_method, client_ip, user_agent, stack_trace, created_at
        FROM error_logs
        {where_clause}
        ORDER BY id DESC
        LIMIT :limit OFFSET :offset
        """
    )

    try:
        result = await db.execute(sql, params)
        rows = [_row_to_dict(r) for r in result.fetchall()]
    except Exception as exc:
        logger.exception("Failed to read error_logs")
        raise HTTPException(
            status_code=500,
            detail={
                "errorCode": "DB_QUERY_FAILED",
                "message": f"Failed to read error_logs: {exc}",
            },
        )

    return {"items": rows, "limit": limit, "offset": offset, "count": len(rows)}


@admin_error_router.get("/errors/summary")
async def errors_summary(
    request: Request,
    since_hours: int = Query(24, ge=1, le=24 * 30),
    db: AsyncSession = Depends(_db_session),
):
    """Aggregate counts to spot recurring problems quickly."""
    try:
        by_code = await db.execute(
            text(
                """
                SELECT error_code, severity, COUNT(*)::int AS count, MAX(created_at) AS last_seen
                FROM error_logs
                WHERE created_at >= NOW() - (:since_hours::int * INTERVAL '1 hour')
                GROUP BY error_code, severity
                ORDER BY count DESC, last_seen DESC
                """
            ),
            {"since_hours": since_hours},
        )
        by_severity = await db.execute(
            text(
                """
                SELECT severity, COUNT(*)::int AS count
                FROM error_logs
                WHERE created_at >= NOW() - (:since_hours::int * INTERVAL '1 hour')
                GROUP BY severity
                ORDER BY count DESC
                """
            ),
            {"since_hours": since_hours},
        )
        by_endpoint = await db.execute(
            text(
                """
                SELECT endpoint, http_method, COUNT(*)::int AS count
                FROM error_logs
                WHERE created_at >= NOW() - (:since_hours::int * INTERVAL '1 hour')
                  AND endpoint IS NOT NULL
                GROUP BY endpoint, http_method
                ORDER BY count DESC
                LIMIT 20
                """
            ),
            {"since_hours": since_hours},
        )
        total = await db.execute(
            text(
                """
                SELECT COUNT(*)::int FROM error_logs
                WHERE created_at >= NOW() - (:since_hours::int * INTERVAL '1 hour')
                """
            ),
            {"since_hours": since_hours},
        )
    except Exception as exc:
        logger.exception("Failed to summarise error_logs")
        raise HTTPException(
            status_code=500,
            detail={
                "errorCode": "DB_QUERY_FAILED",
                "message": f"Failed to summarise error_logs: {exc}",
            },
        )

    return {
        "windowHours": since_hours,
        "total": total.scalar() or 0,
        "bySeverity": [_row_to_dict(r) for r in by_severity.fetchall()],
        "byCode": [_row_to_dict(r) for r in by_code.fetchall()],
        "topEndpoints": [_row_to_dict(r) for r in by_endpoint.fetchall()],
    }


@admin_error_router.get("/errors/by-request/{request_id}")
async def errors_by_request(
    request_id: str,
    db: AsyncSession = Depends(_db_session),
):
    """Return everything we logged against a single request_id - perfect when
    a user reports an issue and gives us the X-Request-ID header value."""
    try:
        result = await db.execute(
            text(
                """
                SELECT id, request_id, error_code, http_status, severity, message, details,
                       user_id, endpoint, http_method, client_ip, user_agent, stack_trace, created_at
                FROM error_logs
                WHERE request_id = :rid
                ORDER BY id ASC
                """
            ),
            {"rid": request_id},
        )
        rows = [_row_to_dict(r) for r in result.fetchall()]
    except Exception as exc:
        logger.exception("Failed to fetch errors by request_id")
        raise HTTPException(
            status_code=500,
            detail={
                "errorCode": "DB_QUERY_FAILED",
                "message": f"Failed to fetch errors: {exc}",
            },
        )

    return {"requestId": request_id, "items": rows, "count": len(rows)}


@admin_error_router.get("/error-codes")
async def list_error_codes(db: AsyncSession = Depends(_db_session)):
    """Return the static registry of known error codes."""
    try:
        result = await db.execute(
            text(
                "SELECT id, code, status AS http_status, severity, message, details, created_at "
                "FROM error_codes ORDER BY code"
            )
        )
        rows = [_row_to_dict(r) for r in result.fetchall()]
    except Exception as exc:
        logger.exception("Failed to read error_codes registry")
        raise HTTPException(
            status_code=500,
            detail={
                "errorCode": "DB_QUERY_FAILED",
                "message": f"Failed to read error_codes registry: {exc}",
            },
        )
    return {"items": rows, "count": len(rows)}
