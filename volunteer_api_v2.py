# ============================================
# VOLUNTEER MANAGEMENT SYSTEM - SIMPLIFIED API
# Pakistan Deedar 2026
# Matches frontend - no unnecessary master data APIs
# ============================================

import uuid
import logging
import os
from collections import defaultdict
import jwt
from datetime import datetime
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import AliasChoices, BaseModel, Field
from sqlalchemy import bindparam, func, select, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from volunteer_schemas_v2 import (
    Region, DataSource, VolunteerStatus, PrintStatus, ValidationError,
    ACCESS_LEVEL_NAMES, ACCESS_LEVEL_BAND_COLORS, DUTY_TYPE_ACCESS_LEVELS,
    get_access_level_for_duty, get_band_color,
    VolunteerUploadRow, VolunteerBulkUpload,
    ValidationResult, CNICValidationResponse,
    VolunteerResponse, VolunteerWithError,
    UploadBatchResponse, BulkValidationResult,
    VolunteerFilters, Pagination, VolunteersResponse,
    VolunteerApprovalFormData,
    DashboardStats, DashboardFilters, RegionStats, EventStats, AccessLevelStats
)
from sqlalchemy import text
from error_logging import ErrorLogger, ErrorCode, ErrorSeverity, log_and_raise_error


# Create logger
logger = logging.getLogger(__name__)


def _request_id(request: Optional[Request]) -> str:
    """Read the request_id set by RequestContextMiddleware (with fallback)."""
    if request is None:
        return str(uuid.uuid4())
    rid = getattr(request.state, "request_id", None) if hasattr(request, "state") else None
    return rid or str(uuid.uuid4())


def _user_id_from_request(request: Optional[Request]) -> Optional[int]:
    """Best-effort extraction of authenticated user id from a Bearer JWT."""
    if request is None:
        return None
    auth_header = request.headers.get("Authorization", "") if hasattr(request, "headers") else ""
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    try:
        secret = os.getenv("SECRET_KEY", "your-secret-key-here")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload.get("id")
    except Exception:
        return None


# Create router
volunteer_router = APIRouter(prefix="/api", tags=["Volunteer Management"])
cnic_router = APIRouter(prefix="/api", tags=["CNIC Verification"])


# ============================================
# DATABASE DEPENDENCIES (Set from main.py)
# ============================================

_get_volunteer_db = None
_get_main_db = None
_get_census_db = None


def set_database_dependencies(volunteer_db_func, main_db_func, census_db_func=None):
    """Set database dependency functions from main.py"""
    global _get_volunteer_db, _get_main_db, _get_census_db
    _get_volunteer_db = volunteer_db_func
    _get_main_db = main_db_func
    _get_census_db = census_db_func


async def volunteer_db_session():
    """Get volunteer database session"""
    if _get_volunteer_db is None:
        raise RuntimeError("Volunteer database not configured")
    async for session in _get_volunteer_db():
        yield session


async def main_db_session():
    """Get main database session (for CNIC validation)"""
    if _get_main_db is None:
        raise RuntimeError("Main database not configured")
    async for session in _get_main_db():
        yield session


async def census_db_session():
    """Get census database session"""
    if _get_census_db is None:
        raise RuntimeError("Census database not configured")
    async for session in _get_census_db():
        yield session


# ============================================
# HELPER FUNCTIONS
# ============================================

def generate_volunteer_id() -> str:
    """Generate unique volunteer ID"""
    return f"VID-{uuid.uuid4().hex[:6].upper()}"


def generate_batch_id() -> str:
    """Generate unique batch ID"""
    return f"batch-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"


def normalize_cnic(cnic: str) -> str:
    """Remove dashes from CNIC"""
    return cnic.replace("-", "").strip() if cnic else ""


def register_implies_approval(register: Optional[str]) -> bool:
    """True only when the checker marked census registration as an explicit yes.

    Upload columns often use ``register``; anything else (including "No" and empty)
    means not registered for approval.
    """
    v = (register or "No").strip().lower()
    return v in ("yes", "y", "true", "1")


def decision_status_after_register(register: Optional[str], decision_status: str) -> str:
    """Apply product rule: not registered cannot be Ok (only Ok/pending are downgraded)."""
    if register_implies_approval(register or "No"):
        return decision_status
    if (decision_status or "").strip().lower() in ("ok", "pending"):
        return "Rejected"
    return decision_status


def effective_decision_status_for_read(register: Optional[str], decision_status: Optional[str]) -> str:
    """Response shaping for list endpoints: align decision with register for legacy rows."""
    return decision_status_after_register(register, decision_status or "pending")


async def _resolve_name_to_id(db: AsyncSession, table: str, value: Union[int, str, None]) -> Optional[int]:
    """Resolve a numeric id or a name string to the corresponding id in `table`.

    - If value is int -> returned as-is.
    - If value is None -> returns None.
    - If value is str: tries to interpret as int first, otherwise looks up by `name` (case-insensitive).
    Raises HTTPException(400) if a provided name cannot be resolved.
    """
    if value is None:
        return None
    if isinstance(value, int):
        return value
    # try numeric string
    try:
        return int(value)
    except Exception:
        pass

    stmt = text(f"SELECT id FROM {table} WHERE lower(name)=lower(:name) LIMIT 1")
    result = await db.execute(stmt, {"name": value})
    found = result.scalar_one_or_none()
    if found is None:
        raise HTTPException(status_code=400, detail=f"{table} name '{value}' not found")
    return found


def get_event_id(event_number: int) -> str:
    """Get event ID from event number"""
    return f"event-{event_number}"


def get_duty_type_id(duty_type: str) -> str:
    """Get duty type ID from name"""
    return f"duty-{duty_type.lower().replace(' ', '-')}"


# ============================================
# CNIC VALIDATION (Uses Main Enrollment DB)
# ============================================

@volunteer_router.post("/import-batch")
async def import_batch_new(
    request: Request,
    batch_data: dict,
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Import batch to import_file table.

    Accepts: fileName, recordCount.
    Table columns: id, user_id, import_at, file_name, record_count, status,
    created_at, updated_at.
    """
    request_id = _request_id(request)
    user_id = _user_id_from_request(request) or 5
    now = datetime.utcnow()

    logger.info(
        f"[{request_id}] /import-batch user_id={user_id} file={batch_data.get('fileName')} "
        f"records={batch_data.get('recordCount')}"
    )

    try:
        insert_stmt = text("""
            INSERT INTO import_file
            (user_id, import_at, file_name, record_count, status, created_at, updated_at)
            VALUES
            (:user_id, :import_at, :file_name, :record_count, :status, :created_at, :updated_at)
            RETURNING id
        """)

        result = await volunteer_db.execute(
            insert_stmt,
            {
                "user_id": user_id,
                "import_at": now,
                "file_name": batch_data.get("fileName", "unknown"),
                "record_count": batch_data.get("recordCount", 0),
                "status": "pending",
                "created_at": now,
                "updated_at": now
            }
        )

        import_file_id = result.scalar()
        await volunteer_db.commit()

        logger.info(
            f"[{request_id}] /import-batch inserted import_file id={import_file_id}"
        )

        return {
            "success": True,
            "message": "Batch imported successfully",
            "importFileId": import_file_id,
            "fileName": batch_data.get("fileName"),
            "recordCount": batch_data.get("recordCount", 0),
            "status": "pending",
            "importAt": now.isoformat(),
            "createdAt": now.isoformat(),
            "requestId": request_id,
        }

    except Exception as exc:
        await volunteer_db.rollback()
        await ErrorLogger.log_error(
            db=volunteer_db,
            code=ErrorCode.DB_INSERT_FAILED,
            message=f"Failed to import batch: {exc}",
            status_code=500,
            severity=ErrorSeverity.ERROR,
            details={
                "file_name": batch_data.get("fileName"),
                "record_count": batch_data.get("recordCount"),
                "user_id": user_id,
            },
            request_id=request_id,
            user_id=user_id,
            request=request,
            exc=exc,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "errorCode": ErrorCode.DB_INSERT_FAILED.value,
                "message": "Failed to import batch",
                "requestId": request_id,
            },
        )


# ============================================
# OLD UPLOAD ENDPOINT (kept for compatibility)
# ============================================

# ============================================
# DASHBOARD
# ============================================

@volunteer_router.get("/event-access-level-duty-requirements")
async def get_event_access_level_duty_requirements(
    request: Request,
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Return event access-level duty requirements with related names.

    This returns strings (names) for event, access level and duty type
    and a list of band type names (if any) instead of numeric IDs.
    """
    request_id = _request_id(request)
    logger.info(f"[{request_id}] /event-access-level-duty-requirements")
    sql = text("""
    SELECT
        r.id,
        e.name AS event_name,
        al.name AS access_level_name,
        dt.name AS duty_type_name,
        r.required_count,
        r.remaining,
        COALESCE(array_remove(array_agg(bt.name), NULL), ARRAY[]::text[]) AS band_types
    FROM event_access_level_duty_requirements r
    JOIN events e ON e.id = r.event_id
    JOIN access_levels al ON al.id = r.access_level_id
    JOIN duty_types dt ON dt.id = r.duty_type_id
    LEFT JOIN band_type_access_level_duty_type btmap
      ON btmap.access_level_id = r.access_level_id
     AND btmap.duty_type_id = r.duty_type_id
    LEFT JOIN band_types bt ON bt.id = btmap.band_type_id
    GROUP BY r.id, e.name, al.name, dt.name, r.required_count, r.remaining
    ORDER BY e.name, al.name, dt.name
    """)

    try:
        result = await volunteer_db.execute(sql)
        rows = result.fetchall()
    except Exception as exc:
        await ErrorLogger.log_error(
            db=volunteer_db,
            code=ErrorCode.DB_QUERY_FAILED,
            message=f"Failed to load event/access-level/duty requirements: {exc}",
            status_code=500,
            severity=ErrorSeverity.ERROR,
            request_id=request_id,
            request=request,
            exc=exc,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "errorCode": ErrorCode.DB_QUERY_FAILED.value,
                "message": "Could not load duty requirements",
                "requestId": request_id,
            },
        )

    # Build hierarchical structure: event -> accessLevels -> duties
    events_map = {}
    for row in rows:
        m = row._mapping
        event_name = m.get("event_name")
        access_name = m.get("access_level_name")
        duty_name = m.get("duty_type_name")
        required = m.get("required_count")
        remaining = m.get("remaining")
        band_types = list(m.get("band_types") or [])

        if event_name not in events_map:
            events_map[event_name] = {
                "event": event_name,
                "accessLevels": {}
            }

        ev = events_map[event_name]

        if access_name not in ev["accessLevels"]:
            ev["accessLevels"][access_name] = {
                "accessLevel": access_name,
                "duties": {}
            }

        al = ev["accessLevels"][access_name]

        # Each duty is unique per event/access level
        al["duties"][duty_name] = {
            "dutyType": duty_name,
            "requiredCount": required,
            "remaining": remaining,
            "bandTypes": band_types
        }

    # Convert maps to lists for output
    out = []
    for ev_name, ev_data in events_map.items():
        access_levels_list = []
        for al_name, al_data in ev_data["accessLevels"].items():
            duties_list = list(al_data["duties"].values())
            access_levels_list.append({
                "accessLevel": al_data["accessLevel"],
                "duties": duties_list
            })

        out.append({
            "event": ev_data["event"],
            "accessLevels": access_levels_list
        })

    return out


# ============================================
# ============================================
# QUERY BY USER / IMPORT


class VolunteerRecordQuery(BaseModel):
    userId: int = Field(..., alias="userId")
    limit: Optional[int] = Field(
        None,
        ge=1,
        le=20_000,
        description="Optional max rows. Omit to return all matches (slower for large data).",
    )
    offset: int = Field(0, ge=0, description="Row offset when using limit (ORDER BY vr.id).")


class VolunteerRecordCreate(BaseModel):
    """Payload for creating one volunteer record."""
    sno: int = Field(..., validation_alias=AliasChoices("sno", "Sno"))
    userId: int = Field(..., alias="userId")
    cnic: str
    name: str
    event: Union[int, str]
    access_level: Union[int, str] = Field(..., alias="accessLevel")
    duty_type: Union[int, str] = Field(..., alias="dutyType")
    decision_status: str = Field("pending", alias="decisionStatus")
    register: Optional[str] = "No"
    import_id: Optional[int] = Field(None, alias="importId")

    class Config:
        populate_by_name = True


@volunteer_router.post("/volunteers/by-import-or-user")
async def get_volunteers_by_user_or_import(
    request: Request,
    query: VolunteerRecordQuery,
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Return volunteer_record rows filtered by `checker_id` (userId).

    Request body: { "userId": int }
    Returns event, access level, and duty type names instead of IDs.
    """
    request_id = _request_id(request)
    logger.info(
        f"[{request_id}] /volunteers/by-import-or-user userId={query.userId} "
        f"limit={query.limit} offset={query.offset}"
    )
    base_sql = """
    SELECT
        vr.id,
        vr.record_number,
        vr.cnic,
        vr.name,
        vr.register,
        e.name as event_name,
        al.name as access_level_name,
        dt.name as duty_type_name,
        vr.record_status,
        vr.decision_status,
        vr.checker_id,
        vr.import_id,
        vr.created_at,
        vr.updated_at
    FROM volunteer_record vr
    LEFT JOIN events e ON e.id = vr.event_id
    LEFT JOIN access_levels al ON al.id = vr.access_level_id
    LEFT JOIN duty_types dt ON dt.id = vr.duty_type_id
    WHERE vr.checker_id = :userId
    ORDER BY vr.id
    """
    params: dict = {"userId": query.userId}
    if query.limit is not None:
        sql = base_sql + " LIMIT :limit OFFSET :offset"
        params["limit"] = query.limit
        params["offset"] = query.offset
    else:
        sql = base_sql

    stmt = text(sql)
    try:
        result = await volunteer_db.execute(stmt, params)
        rows = result.fetchall()
    except Exception as exc:
        await ErrorLogger.log_error(
            db=volunteer_db,
            code=ErrorCode.DB_QUERY_FAILED,
            message=f"Failed to load volunteers for userId={query.userId}: {exc}",
            status_code=500,
            severity=ErrorSeverity.ERROR,
            details={"user_id": query.userId},
            request_id=request_id,
            user_id=query.userId,
            request=request,
            exc=exc,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "errorCode": ErrorCode.DB_QUERY_FAILED.value,
                "message": "Could not load volunteer records",
                "requestId": request_id,
            },
        )

    out = []
    for r in rows:
        m = r._mapping
        reg = m.get("register")
        out.append({
            "id": m.get("id"),
            "recordNumber": m.get("record_number"),
            "cnic": m.get("cnic"),
            "name": m.get("name"),
            "register": reg,
            "eventName": m.get("event_name"),
            "accessLevelName": m.get("access_level_name"),
            "dutyTypeName": m.get("duty_type_name"),
            "recordStatus": m.get("record_status"),
            "decisionStatus": effective_decision_status_for_read(reg, m.get("decision_status")),
            "checkerId": m.get("checker_id"),
            "importId": m.get("import_id"),
            "createdAt": m.get("created_at").isoformat() if m.get("created_at") else None,
            "updatedAt": m.get("updated_at").isoformat() if m.get("updated_at") else None,
        })

    return out


# ============================================
# CNIC USAGE CHECK (Census Database)
# ============================================

class CNICBatchQuery(BaseModel):
    cnics: List[str] = Field(..., description="List of CNICs to check")


@cnic_router.post("/cnic-usage/batch")
async def cnic_usage_batch(
    request: Request,
    payload: CNICBatchQuery,
    census_db: AsyncSession = Depends(census_db_session),
    volunteer_db: AsyncSession = Depends(volunteer_db_session),
):
    """Check CNICs against census: ``FamilyLevelDetails`` (IdNumber) and ``Form`` (head + family CNICs)."""
    request_id = _request_id(request)
    normalized_cnics = [normalize_cnic(c) for c in payload.cnics if normalize_cnic(c)]
    _c_host = os.getenv("CENSUS_HOST", "jamat-postgres.postgres.database.azure.com")
    _c_db = os.getenv("CENSUS_DB", "census_db_updated")
    logger.info(
        f"[{request_id}] /cnic-usage/batch raw={len(payload.cnics)} normalized={len(normalized_cnics)} "
        f"census={_c_host} db={_c_db} (set CENSUS_* in .env if this is not the DB you are checking in SQL tools)"
    )
    if not normalized_cnics:
        return {"success": True, "results": [], "requestId": request_id}

    # FamilyLevelDetails: one row per person (IdNumber).
    sql_fld = text("""
        SELECT
            replace(coalesce(btrim("IdNumber"::text), ''), '-', '') AS cnic_norm,
            COUNT(*)::int AS cnt
        FROM "FamilyLevelDetails"
        WHERE replace(coalesce(btrim("IdNumber"::text), ''), '-', '') IN :cnics
        GROUP BY replace(coalesce(btrim("IdNumber"::text), ''), '-', '')
    """).bindparams(bindparam("cnics", expanding=True))

    # Form: ``HouseHoldCNIC`` and each element of ``FamilyMembersCNICInPakistan`` (distinct FormId per CNIC).
    sql_form_hh = text("""
        SELECT
            replace(coalesce(btrim(f."HouseHoldCNIC"::text), ''), '-', '') AS cnic_norm,
            f."FormId" AS form_id
        FROM "Form" f
        WHERE replace(coalesce(btrim(f."HouseHoldCNIC"::text), ''), '-', '') IN :cnics
    """).bindparams(bindparam("cnics", expanding=True))
    sql_form_fam = text("""
        SELECT
            replace(coalesce(btrim(m::text), ''), '-', '') AS cnic_norm,
            f."FormId" AS form_id
        FROM "Form" f
        CROSS JOIN LATERAL unnest(
            COALESCE(f."FamilyMembersCNICInPakistan", ARRAY[]::varchar(20)[])
        ) AS t(m)
        WHERE replace(coalesce(btrim(m::text), ''), '-', '') IN :cnics
    """).bindparams(bindparam("cnics", expanding=True))

    try:
        # Only these strings are valid matches for this request (avoids any stray key confusion).
        allowed = set(normalized_cnics)
        res_fld = await census_db.execute(sql_fld, {"cnics": normalized_cnics})
        counts_fld = {
            str(row[0]): row[1]
            for row in res_fld.fetchall()
            if row[0] is not None and str(row[0]) in allowed
        }
        # Distinct form ids per cnic (head row + family array may reference same form)
        form_ids = defaultdict(set)  # cnic -> distinct FormId strings
        for r in (await census_db.execute(sql_form_hh, {"cnics": normalized_cnics})).fetchall():
            c_norm, fid = (str(r[0]), r[1]) if r[0] else (None, None)
            if c_norm and c_norm in allowed:
                form_ids[c_norm].add(str(fid) if fid is not None else "")
        for r in (await census_db.execute(sql_form_fam, {"cnics": normalized_cnics})).fetchall():
            c_norm, fid = (str(r[0]), r[1]) if r[0] else (None, None)
            if c_norm and c_norm in allowed:
                form_ids[c_norm].add(str(fid) if fid is not None else "")
        counts_form = {c: len(ids) for c, ids in form_ids.items() if c in allowed and ids}

        out_results = []
        for cnic in normalized_cnics:
            n_fld = counts_fld.get(cnic, 0)
            n_form = counts_form.get(cnic, 0)
            out_results.append(
                {
                    "cnic": cnic,
                    "familyLevelDetails": {
                        "present": n_fld > 0,
                        "matchCount": n_fld,
                    },
                    "form": {
                        "present": n_form > 0,
                        "matchCount": n_form,
                    },
                    "isUsed": n_fld > 0 or n_form > 0,
                    "usageCount": n_fld + n_form,
                }
            )

        return {
            "success": True,
            "results": out_results,
            "requestId": request_id,
            # Same connection as main.py CENSUS_* so you can compare with your SQL client.
            "meta": {
                "censusHost": _c_host,
                "censusDatabase": _c_db,
            },
        }
    except Exception as exc:
        # Log against the volunteer (primary) DB - census DB sessions are
        # external and we don't want to mix our log table with that schema.
        await ErrorLogger.log_error(
            db=volunteer_db,
            code=ErrorCode.CENSUS_DB_ERROR,
            message=f"Failed to check CNIC usage in census DB: {exc}",
            status_code=502,
            severity=ErrorSeverity.ERROR,
            details={"cnic_count": len(normalized_cnics)},
            request_id=request_id,
            request=request,
            exc=exc,
        )
        raise HTTPException(
            status_code=502,
            detail={
                "errorCode": ErrorCode.CENSUS_DB_ERROR.value,
                "message": "Failed to check CNIC usage",
                "requestId": request_id,
            },
        )


@volunteer_router.post("/volunteers/record")
async def create_volunteer_record(
    request: Request,
    record: VolunteerRecordCreate,
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Insert a single volunteer record into `volunteer_record` table.

    Fields expected from frontend: Sno, userId, cnic, name, event, Access level, Duty Type
    """
    request_id = _request_id(request)
    logger.info(
        f"[{request_id}] /volunteers/record sno={record.sno} cnic={record.cnic} userId={record.userId}"
    )
    now = datetime.utcnow()
    insert_sql = text("""
        INSERT INTO volunteer_record
        (record_number, cnic, name, event_id, access_level_id, duty_type_id,
         record_status, decision_status, register, checker_id, import_id, created_at, updated_at)
        VALUES
        (:record_number, :cnic, :name, :event_id, :access_level_id, :duty_type_id,
         :record_status, :decision_status, :register, :checker_id, :import_id, :created_at, :updated_at)
        RETURNING id
    """)

    try:
        event_id = await _resolve_name_to_id(volunteer_db, "events", record.event)
        access_level_id = await _resolve_name_to_id(volunteer_db, "access_levels", record.access_level)
        duty_type_id = await _resolve_name_to_id(volunteer_db, "duty_types", record.duty_type)
    except HTTPException as http_exc:
        # _resolve_name_to_id raises 400 with a useful message; log it.
        await ErrorLogger.log_error(
            db=volunteer_db,
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Could not resolve lookup for record sno={record.sno}: {http_exc.detail}",
            status_code=http_exc.status_code,
            severity=ErrorSeverity.WARNING,
            details={
                "sno": record.sno,
                "cnic": record.cnic,
                "event": str(record.event),
                "access_level": str(record.access_level),
                "duty_type": str(record.duty_type),
            },
            request_id=request_id,
            user_id=record.userId,
            request=request,
        )
        raise

    params = {
        "record_number": record.sno,
        "cnic": record.cnic,
        "name": record.name,
        "event_id": event_id,
        "access_level_id": access_level_id,
        "duty_type_id": duty_type_id,
        "record_status": "maker",
        "decision_status": decision_status_after_register(
            record.register, record.decision_status or "pending"
        ),
        "register": record.register or "No",
        "checker_id": record.userId,
        "import_id": record.import_id,
        "created_at": now,
        "updated_at": now
    }

    try:
        result = await volunteer_db.execute(insert_sql, params)
        inserted_id = result.scalar()
        await volunteer_db.commit()
        logger.info(
            f"[{request_id}] /volunteers/record inserted id={inserted_id} sno={record.sno}"
        )
        return {"success": True, "id": inserted_id, "requestId": request_id}
    except Exception as exc:
        await volunteer_db.rollback()
        await ErrorLogger.log_error(
            db=volunteer_db,
            code=ErrorCode.DB_INSERT_FAILED,
            message=f"Failed to insert volunteer_record for sno={record.sno}: {exc}",
            status_code=500,
            severity=ErrorSeverity.ERROR,
            details={
                "sno": record.sno,
                "cnic": record.cnic,
                "user_id": record.userId,
                "import_id": record.import_id,
            },
            request_id=request_id,
            user_id=record.userId,
            request=request,
            exc=exc,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "errorCode": ErrorCode.DB_INSERT_FAILED.value,
                "message": "Failed to insert volunteer record",
                "requestId": request_id,
            },
        )


@volunteer_router.post("/volunteers/records")
async def create_volunteer_records(
    request: Request,
    records: List[VolunteerRecordCreate],
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Bulk insert multiple volunteer records in one call. Accepts large lists (1000+ items)."""
    request_id = _request_id(request)
    logger.info(
        f"[{request_id}] /volunteers/records bulk insert count={len(records)}"
    )
    now = datetime.utcnow()
    insert_sql = text("""
        INSERT INTO volunteer_record
        (record_number, cnic, name, event_id, access_level_id, duty_type_id,
         record_status, decision_status, register, checker_id, import_id, created_at, updated_at)
        VALUES
        (:record_number, :cnic, :name, :event_id, :access_level_id, :duty_type_id,
         :record_status, :decision_status, :register, :checker_id, :import_id, :created_at, :updated_at)
        RETURNING id
    """)
    inserted_ids = []
    try:
        # Resolve IDs caches
        event_cache = {}
        access_cache = {}
        duty_cache = {}

        # Normalize CNICs for duplicate/discrepancy checks
        cnics = [normalize_cnic(r.cnic or "") for r in records]
        normalized_unique = list({c for c in cnics if c})

        # Load existing volunteer_record rows for these CNICs
        existing_rows = {}
        if normalized_unique:
            ex_sql = text("""
                SELECT id, cnic, event_id, access_level_id, duty_type_id, record_status
                FROM volunteer_record
                WHERE replace(coalesce(cnic,''),'-','') IN :cnics
            """).bindparams(bindparam("cnics", expanding=True))
            ex_res = await volunteer_db.execute(ex_sql, {"cnics": normalized_unique})
            for row in ex_res.fetchall():
                cid = str(row[1]).replace('-', '') if row[1] else ''
                existing_rows.setdefault(cid, []).append({
                    "id": row[0],
                    "event_id": row[2],
                    "access_level_id": row[3],
                    "duty_type_id": row[4],
                    "record_status": row[5]
                })

        # Build combined view per CNIC to classify discrepant across events and within event
        # First, resolve ids for incoming records
        incoming = []
        for idx, rec in enumerate(records):
            # Resolve event/access/duty ids (cache)
            if rec.event in event_cache:
                event_id = event_cache[rec.event]
            else:
                event_id = await _resolve_name_to_id(volunteer_db, "events", rec.event)
                event_cache[rec.event] = event_id

            if rec.access_level in access_cache:
                access_level_id = access_cache[rec.access_level]
            else:
                access_level_id = await _resolve_name_to_id(volunteer_db, "access_levels", rec.access_level)
                access_cache[rec.access_level] = access_level_id

            if rec.duty_type in duty_cache:
                duty_type_id = duty_cache[rec.duty_type]
            else:
                duty_type_id = await _resolve_name_to_id(volunteer_db, "duty_types", rec.duty_type)
                duty_cache[rec.duty_type] = duty_type_id

            normalized = normalize_cnic(rec.cnic or "")
            incoming.append({
                "idx": idx,
                "rec": rec,
                "cnic_norm": normalized,
                "event_id": event_id,
                "access_level_id": access_level_id,
                "duty_type_id": duty_type_id,
                "decision_status": "pending",
                "reason": None
            })

        # Group existing+incoming by CNIC and event to detect duplicates/discrepancies
        by_cnic = {}
        for inc in incoming:
            c = inc["cnic_norm"]
            by_cnic.setdefault(c, {"incoming": [], "existing": []})
            by_cnic[c]["incoming"].append(inc)
        for c, rows in existing_rows.items():
            by_cnic.setdefault(c, {"incoming": [], "existing": []})
            by_cnic[c]["existing"].extend(rows)

        # Classification
        for cnic, group in by_cnic.items():
            incs = group["incoming"]
            exs = group["existing"]

            # Collect events present across existing and incoming
            events_present = set([e["event_id"] for e in exs if e.get("event_id")])
            events_present.update([i["event_id"] for i in incs if i.get("event_id")])

            # If CNIC appears in multiple events (including existing rows) -> mark incoming in other events as Discrepant-2
            if len(events_present) > 1:
                # mark incoming records that are in events where other event exists as Discrepant-2
                for inc in incs:
                    # if there exists any existing record with different event_id OR another incoming with different event
                    other_events = {e for e in events_present if e != inc["event_id"]}
                    if other_events:
                        inc["decision_status"] = "Discrepant-2"
                        inc["reason"] = "Multiple duties across events"

            # For each event, check duplicates and differing duties
            # Build map of (event_id) -> set of (access_level_id,duty_type_id)
            event_map = {}
            for ex in exs:
                k = ex.get("event_id")
                event_map.setdefault(k, set()).add((ex.get("access_level_id"), ex.get("duty_type_id")))
            for inc in incs:
                k = inc.get("event_id")
                event_map.setdefault(k, set()).add((inc.get("access_level_id"), inc.get("duty_type_id")))

            for event_id, combos in event_map.items():
                if len(combos) >= 2:
                    # multiple different duties in same event -> mark one as Discrepant-1 and rest Discrepant-2
                    # prefer existing as Discrepant-1 if present; otherwise first incoming becomes Discrepant-1
                    # mark incoming ones appropriately
                    # find incoming for this event
                    incs_for_event = [i for i in incs if i["event_id"] == event_id]
                    if not incs_for_event:
                        continue
                    # If any existing row exists for this event, mark first existing as Discrepant-1 and incoming as Discrepant-2
                    ex_for_event = [e for e in exs if e.get("event_id") == event_id]
                    if ex_for_event:
                        # incoming -> Discrepant-2
                        for inc in incs_for_event:
                            # But if identical access/duty exists in existing -> it's a duplicate -> Reject
                            same_exists = any((e.get("access_level_id"), e.get("duty_type_id")) == (inc.get("access_level_id"), inc.get("duty_type_id")) for e in ex_for_event)
                            if same_exists:
                                inc["decision_status"] = "Rejected"
                                inc["reason"] = "Duplicate: same event and duty already exists"
                            else:
                                # Check if any existing printed -> reject
                                if any(e.get("record_status") == "printed" for e in ex_for_event):
                                    inc["decision_status"] = "Rejected"
                                    inc["reason"] = "Existing printed badge prevents additional duty"
                                else:
                                    inc["decision_status"] = "Discrepant-2"
                                    inc["reason"] = "Different duties in same event"
                    else:
                        # No existing rows; multiple incoming in same event with different duties
                        # pick the first incoming as Discrepant-1, rest Discrepant-2
                        sorted_inc = incs_for_event
                        if sorted_inc:
                            sorted_inc[0]["decision_status"] = "Discrepant-1"
                            sorted_inc[0]["reason"] = "Multiple duties in same event"
                        for inc in sorted_inc[1:]:
                            inc["decision_status"] = "Discrepant-2"
                            inc["reason"] = "Multiple duties in same event"

            # Now check duplicates exact same event+access+duty against existing rows
            for inc in incs:
                if inc["decision_status"] != "pending":
                    # already classified
                    continue
                ex_for_event = [e for e in exs if e.get("event_id") == inc["event_id"]]
                if any((e.get("access_level_id"), e.get("duty_type_id")) == (inc.get("access_level_id"), inc.get("duty_type_id")) for e in ex_for_event):
                    inc["decision_status"] = "Rejected"
                    inc["reason"] = "Duplicate: same event and duty already exists"
                else:
                    # Also check if any existing printed in same event forbids additional duty
                    if any(e.get("record_status") == "printed" for e in ex_for_event):
                        inc["decision_status"] = "Rejected"
                        inc["reason"] = "Existing printed badge prevents additional duty"
                    else:
                        # If still pending, mark Ok
                        if inc["decision_status"] == "pending":
                            inc["decision_status"] = "Ok"
                            inc["reason"] = None

        # Not registered in census (register is not an explicit yes) => cannot be Ok
        for inc in incoming:
            before = inc["decision_status"]
            after = decision_status_after_register(inc["rec"].register, before)
            inc["decision_status"] = after
            if (
                after == "Rejected"
                and before in ("Ok", "pending")
                and not register_implies_approval(inc["rec"].register or "No")
            ):
                inc["reason"] = "Not registered"

        # Insert all incoming records with computed decision_status
        for inc in incoming:
            rec = inc["rec"]
            params = {
                "record_number": rec.sno,
                "cnic": rec.cnic,
                "name": rec.name,
                "event_id": inc["event_id"],
                "access_level_id": inc["access_level_id"],
                "duty_type_id": inc["duty_type_id"],
                "record_status": "maker",
                "decision_status": inc["decision_status"],
                "register": rec.register or "No",
                "checker_id": rec.userId,
                "import_id": rec.import_id,
                "created_at": now,
                "updated_at": now
            }
            result = await volunteer_db.execute(insert_sql, params)
            inserted_id = result.scalar()
            inserted_ids.append(inserted_id)

        await volunteer_db.commit()

        # Audit summary of decisions for this batch.
        status_summary: dict = {}
        for inc in incoming:
            status_summary[inc["decision_status"]] = status_summary.get(inc["decision_status"], 0) + 1
        logger.info(
            f"[{request_id}] /volunteers/records inserted={len(inserted_ids)} status_summary={status_summary}"
        )

        return {
            "success": True,
            "inserted": len(inserted_ids),
            "ids": inserted_ids,
            "statusSummary": status_summary,
            "requestId": request_id,
        }
    except HTTPException:
        await volunteer_db.rollback()
        raise
    except Exception as exc:
        await volunteer_db.rollback()
        await ErrorLogger.log_error(
            db=volunteer_db,
            code=ErrorCode.DB_INSERT_FAILED,
            message=f"Bulk insert volunteer_records failed: {exc}",
            status_code=500,
            severity=ErrorSeverity.ERROR,
            details={"record_count": len(records)},
            request_id=request_id,
            request=request,
            exc=exc,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "errorCode": ErrorCode.DB_INSERT_FAILED.value,
                "message": "Bulk volunteer record insert failed",
                "requestId": request_id,
            },
        )


# ============================================
# MAKER DECISIONS
# ============================================

class MakerDecisionUpdate(BaseModel):
    """Maker decision - matches exactly what the frontend sends"""
    id: int = Field(..., description="Volunteer record ID")
    recordNumber: int = Field(..., description="Record number")
    cnic: str = Field(..., description="CNIC")
    name: str = Field(..., description="Volunteer name")
    register: str = Field(..., description="Register status")
    eventName: str = Field(..., description="Event name")
    accessLevelName: str = Field(..., description="Access level")
    dutyTypeName: str = Field(..., description="Duty type")
    recordStatus: str = Field(..., description="Current record status")
    decisionStatus: str = Field(..., description="Decision status set by maker")
    checkerId: int = Field(..., description="Checker ID")
    importId: int = Field(..., description="Import ID")


class CheckerSubmitDecision(BaseModel):
    """One maker_decisions row update from checker submit.

    The ``maker_decisions`` row id may be sent as ``decisionId``, ``id``, or ``Id``.
    """

    model_config = {"populate_by_name": True}

    decisionId: int = Field(
        ...,
        validation_alias=AliasChoices("decisionId", "id", "Id"),
        description="maker_decisions.id (audit row id)",
    )
    decisionStatus: Optional[str] = Field(
        None, description="Checker-final decision status (optional)"
    )
    reason: Optional[str] = Field(None, description="Optional checker reason")


class CheckerSubmitPayload(BaseModel):
    """Checker submit body: top-level ``importId`` plus a ``decisions`` array."""

    model_config = {"populate_by_name": True}

    importId: Optional[int] = Field(
        None,
        description="If set, only update rows that belong to this import (safety check).",
    )
    decisions: List[CheckerSubmitDecision] = Field(
        ...,
        min_length=1,
        description="Updates to apply in ``maker_decisions``",
    )


@volunteer_router.post("/volunteers/maker-decisions")
async def update_maker_decisions(
    request: Request,
    decisions: List[MakerDecisionUpdate],
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Persist a batch of maker decisions.

    The frontend sends an array of decisions. Each one is recorded against
    the maker_decisions audit table. The maker id is taken from the JWT
    token (the `MakerDecisionUpdate` payload itself does NOT carry it).

    The volunteer_record.decision_status is intentionally NOT updated here
    – it was decided at upload time and must not be overwritten by a
    maker action.
    """
    request_id = _request_id(request)
    maker_id = _user_id_from_request(request) or 0

    logger.info(
        f"[{request_id}] /volunteers/maker-decisions count={len(decisions)} maker_id={maker_id}"
    )

    now = datetime.utcnow()
    updated_ids: list = []
    skipped_ids: list = []

    try:
        for idx, decision in enumerate(decisions):
            try:
                fetch_sql = text("""
                    SELECT record_number, cnic, name, event_id, access_level_id, duty_type_id,
                           record_status, register, checker_id, import_id
                    FROM volunteer_record
                    WHERE id = :id
                """)
                result = await volunteer_db.execute(fetch_sql, {"id": decision.id})
                record = result.fetchone()

                if not record:
                    skipped_ids.append(decision.id)
                    await ErrorLogger.log_error(
                        db=volunteer_db,
                        code=ErrorCode.VOLUNTEER_NOT_FOUND,
                        message=f"Volunteer record ID {decision.id} not found",
                        status_code=404,
                        severity=ErrorSeverity.WARNING,
                        details={
                            "volunteer_id": decision.id,
                            "index": idx,
                            "decision_status": decision.decisionStatus,
                        },
                        request_id=request_id,
                        user_id=maker_id or None,
                        request=request,
                    )
                    continue

                insert_sql = text("""
                    INSERT INTO maker_decisions
                    (volunteer_record_id, maker_id, decision_status, reason,
                     record_number, cnic, name, event_id, access_level_id, duty_type_id,
                     record_status, register, checker_id, import_id, created_at, updated_at)
                    VALUES
                    (:volunteer_record_id, :maker_id, :decision_status, :reason,
                     :record_number, :cnic, :name, :event_id, :access_level_id, :duty_type_id,
                     :record_status, :register, :checker_id, :import_id, :created_at, :updated_at)
                """)
                insert_params = {
                    "volunteer_record_id": decision.id,
                    "maker_id": maker_id,
                    "decision_status": decision.decisionStatus,
                    "reason": None,
                    "record_number": record[0],
                    "cnic": record[1],
                    "name": record[2],
                    "event_id": record[3],
                    "access_level_id": record[4],
                    "duty_type_id": record[5],
                    "record_status": record[6],
                    "register": record[7],
                    "checker_id": record[8],
                    "import_id": record[9],
                    "created_at": now,
                    "updated_at": now
                }
                await volunteer_db.execute(insert_sql, insert_params)
                updated_ids.append(decision.id)

                logger.info(
                    f"[{request_id}] maker decision id={decision.id} status={decision.decisionStatus} maker_id={maker_id}"
                )

            except Exception as exc:
                await ErrorLogger.log_error(
                    db=volunteer_db,
                    code=ErrorCode.DB_INSERT_FAILED,
                    message=f"Failed to record maker decision for volunteer {decision.id}: {exc}",
                    status_code=500,
                    severity=ErrorSeverity.ERROR,
                    details={
                        "volunteer_id": decision.id,
                        "decision_status": decision.decisionStatus,
                        "index": idx,
                    },
                    request_id=request_id,
                    user_id=maker_id or None,
                    request=request,
                    exc=exc,
                )
                logger.exception(
                    f"[{request_id}] Error processing decision for volunteer {decision.id}"
                )

        await volunteer_db.commit()

        logger.info(
            f"[{request_id}] /volunteers/maker-decisions done updated={len(updated_ids)} "
            f"skipped={len(skipped_ids)} total={len(decisions)}"
        )

        return {
            "success": True,
            "updated": len(updated_ids),
            "updatedIds": updated_ids,
            "skipped": len(skipped_ids),
            "skippedIds": skipped_ids,
            "requestId": request_id,
        }

    except Exception as exc:
        await volunteer_db.rollback()
        await ErrorLogger.log_error(
            db=volunteer_db,
            code=ErrorCode.DB_QUERY_FAILED,
            message=f"Batch maker-decisions processing failed: {exc}",
            status_code=500,
            severity=ErrorSeverity.CRITICAL,
            details={"total_records": len(decisions)},
            request_id=request_id,
            user_id=maker_id or None,
            request=request,
            exc=exc,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "errorCode": ErrorCode.DB_QUERY_FAILED.value,
                "message": "Batch processing failed",
                "requestId": request_id,
            },
        )


@volunteer_router.post("/volunteers/maker-decisions/submit")
async def submit_checker_maker_decisions(
    request: Request,
    payload: CheckerSubmitPayload,
    volunteer_db: AsyncSession = Depends(volunteer_db_session),
):
    """Checker submit: update rows in maker_decisions.

    Body format::

        {
          "importId": 116,
          "decisions": [
            { "Id": 9162, "decisionStatus": "Ok", "reason": "..." },
            { "decisionId": 9163, "decisionStatus": "Reject", "reason": "..." }
          ]
        }

    Each decision row is identified by ``decisionId`` or ``id`` or ``Id`` (same value:
    ``maker_decisions.id``). When ``importId`` is set, only rows for that import are
    updated.
    """
    request_id = _request_id(request)
    checker_id = _user_id_from_request(request) or 0
    now = datetime.utcnow()

    logger.info(
        f"[{request_id}] /volunteers/maker-decisions/submit count={len(payload.decisions)} "
        f"checker_id={checker_id} importId={payload.importId!r}"
    )

    updated_ids: list = []
    skipped_ids: list = []
    try:
        for idx, item in enumerate(payload.decisions):
            try:
                if payload.importId is not None:
                    exists_sql = text(
                        """
                        SELECT id
                        FROM maker_decisions
                        WHERE id = :id AND import_id = :import_id
                        LIMIT 1
                        """
                    )
                    exists_params = {"id": item.decisionId, "import_id": payload.importId}
                else:
                    exists_sql = text(
                        """
                        SELECT id
                        FROM maker_decisions
                        WHERE id = :id
                        LIMIT 1
                        """
                    )
                    exists_params = {"id": item.decisionId}

                found = (await volunteer_db.execute(exists_sql, exists_params)).scalar_one_or_none()
                if found is None:
                    skipped_ids.append(item.decisionId)
                    continue

                update_sql = text(
                    """
                    UPDATE maker_decisions
                    SET
                        decision_status = COALESCE(:decision_status, decision_status),
                        reason = COALESCE(:reason, reason),
                        checker_id = :checker_id,
                        updated_at = :updated_at
                    WHERE id = :id
                    """
                )
                await volunteer_db.execute(
                    update_sql,
                    {
                        "id": item.decisionId,
                        "decision_status": item.decisionStatus,
                        "reason": item.reason,
                        "checker_id": checker_id or None,
                        "updated_at": now,
                    },
                )
                updated_ids.append(item.decisionId)
            except Exception as exc:
                skipped_ids.append(item.decisionId)
                await ErrorLogger.log_error(
                    db=volunteer_db,
                    code=ErrorCode.DB_UPDATE_FAILED,
                    message=f"Failed checker submit update for maker_decision {item.decisionId}: {exc}",
                    status_code=500,
                    severity=ErrorSeverity.ERROR,
                    details={
                        "decision_id": item.decisionId,
                        "index": idx,
                        "import_id": payload.importId,
                    },
                    request_id=request_id,
                    user_id=checker_id or None,
                    request=request,
                    exc=exc,
                )

        await volunteer_db.commit()
        return {
            "success": True,
            "updated": len(updated_ids),
            "updatedIds": updated_ids,
            "skipped": len(skipped_ids),
            "skippedIds": skipped_ids,
            "requestId": request_id,
        }
    except Exception as exc:
        await volunteer_db.rollback()
        await ErrorLogger.log_error(
            db=volunteer_db,
            code=ErrorCode.DB_QUERY_FAILED,
            message=f"Checker submit batch failed: {exc}",
            status_code=500,
            severity=ErrorSeverity.CRITICAL,
            details={
                "total_records": len(payload.decisions),
                "import_id": payload.importId,
            },
            request_id=request_id,
            user_id=checker_id or None,
            request=request,
            exc=exc,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "errorCode": ErrorCode.DB_QUERY_FAILED.value,
                "message": "Checker submit failed",
                "requestId": request_id,
            },
        )


@volunteer_router.get("/volunteers/maker-decisions")
async def get_maker_decisions_by_import(
    request: Request,
    import_id: Optional[int] = Query(
        None,
        alias="importId",
        description="If set, return only decisions for this import (still grouped under that key).",
    ),
    volunteer_db: AsyncSession = Depends(volunteer_db_session),
):
    """Return `maker_decisions` rows grouped by `import_id`.

    Each key in ``byImportId`` is the import file id (string). The value is a list
    of decision objects for that import, ordered by audit row id. Use optional
    query parameter ``importId`` to return a single group.
    """
    request_id = _request_id(request)
    logger.info(
        f"[{request_id}] GET /volunteers/maker-decisions importId={import_id!r}"
    )

    base_sql = """
    SELECT
        md.id,
        md.volunteer_record_id,
        md.decision_status,
        md.reason,
        md.record_number,
        md.cnic,
        md.name,
        e.name AS event_name,
        al.name AS access_level_name,
        dt.name AS duty_type_name,
        md.record_status,
        md.register,
        md.checker_id,
        md.import_id,
        md.created_at,
        md.updated_at,
        mk.full_name AS maker_name
    FROM maker_decisions md
    LEFT JOIN events e ON e.id = md.event_id
    LEFT JOIN access_levels al ON al.id = md.access_level_id
    LEFT JOIN duty_types dt ON dt.id = md.duty_type_id
    LEFT JOIN users mk ON mk.id = md.maker_id
    """
    if import_id is not None:
        sql = text(base_sql + " WHERE md.import_id = :import_id ORDER BY md.id")
        params = {"import_id": import_id}
    else:
        sql = text(base_sql + " ORDER BY md.import_id NULLS LAST, md.id")
        params = {}

    try:
        result = await volunteer_db.execute(sql, params)
        rows = result.fetchall()
    except Exception as exc:
        await ErrorLogger.log_error(
            db=volunteer_db,
            code=ErrorCode.DB_QUERY_FAILED,
            message=f"Failed to load maker decisions: {exc}",
            status_code=500,
            severity=ErrorSeverity.ERROR,
            details={"import_id": import_id},
            request_id=request_id,
            request=request,
            exc=exc,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "errorCode": ErrorCode.DB_QUERY_FAILED.value,
                "message": "Could not load maker decisions",
                "requestId": request_id,
            },
        )

    by_import: dict = {}
    for r in rows:
        m = r._mapping
        iid = m.get("import_id")
        key = str(iid) if iid is not None else "null"
        if key not in by_import:
            by_import[key] = []
        by_import[key].append(
            {
                "decisionId": m.get("id"),
                "id": m.get("volunteer_record_id"),
                "recordNumber": m.get("record_number"),
                "cnic": m.get("cnic"),
                "name": m.get("name"),
                "register": m.get("register"),
                "eventName": m.get("event_name"),
                "accessLevelName": m.get("access_level_name"),
                "dutyTypeName": m.get("duty_type_name"),
                "recordStatus": m.get("record_status"),
                "decisionStatus": m.get("decision_status"),
                "reason": m.get("reason"),
                "makerId": m.get("maker_name"),
                "checkerId": m.get("checker_id"),
                "importId": m.get("import_id"),
                "createdAt": m.get("created_at").isoformat()
                if m.get("created_at")
                else None,
                "updatedAt": m.get("updated_at").isoformat()
                if m.get("updated_at")
                else None,
            }
        )

    return {
        "requestId": request_id,
        "byImportId": by_import,
    }
