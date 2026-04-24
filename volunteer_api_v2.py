# ============================================
# VOLUNTEER MANAGEMENT SYSTEM - SIMPLIFIED API
# Pakistan Deedar 2026
# Matches frontend - no unnecessary master data APIs
# ============================================

import uuid
import logging
from datetime import datetime
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, and_, or_, update
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


# Create logger
logger = logging.getLogger(__name__)


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
        raise RuntimeError("Main database not configured")
    async for session in _get_main_db():
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

@volunteer_router.post("/enrollment/validate/{cnic}", response_model=CNICValidationResponse)
async def validate_cnic(
    cnic: str,
    main_db: AsyncSession = Depends(main_db_session)
):
    """
    Validate CNIC against enrollment/census database.
    Returns whether CNIC is registered and the person's name.
    """
    return CNICValidationResponse(
        is_valid=False,
        is_registered=False,
        name=None,
        message="Enrollment validation is unavailable in volunteer-only mode"
    )


@volunteer_router.post("/enrollment/validate-batch")
async def validate_cnic_batch(
    cnics: List[str],
    main_db: AsyncSession = Depends(main_db_session)
):
    """
    Batch validate CNICs against enrollment database.
    Returns dict of CNIC -> {isValid, isRegistered, name}
    """
    results = {}

    for cnic in cnics:
        results[cnic] = {
            "isValid": False,
            "isRegistered": False,
            "name": None,
            "message": "Enrollment validation is unavailable in volunteer-only mode",
        }

    return results


# ============================================
# VOLUNTEER UPLOAD & VALIDATION
# ============================================

# In-memory storage (replace with actual database)
# For now using simple dict - will be replaced with SQLAlchemy models
_volunteers_db = {}
_batches_db = {}


@volunteer_router.post("/volunteers/upload", response_model=UploadBatchResponse)
async def upload_volunteers(
    upload: VolunteerBulkUpload,
    volunteer_db: AsyncSession = Depends(volunteer_db_session),
    main_db: AsyncSession = Depends(main_db_session)
):
    """
    Upload volunteers from Excel file.
    Performs validation:
    1. Validate CNIC against enrollment database
    2. Check for duplicates (same CNIC + same event + same duty)
    3. Check for discrepancies (same CNIC, different duties in same event)
    4. Check for multiple events (same CNIC across different events)
    """
    batch_id = generate_batch_id()
    now = datetime.utcnow()
    
    # Create batch record
    batch = {
        "id": batch_id,
        "fileName": upload.file_name,
        "region": upload.region,
        "uploadedBy": "current-user",  # TODO: Get from auth
        "uploadedByName": "Current User",
        "totalRecords": len(upload.volunteers),
        "validRecords": 0,
        "rejectedRecords": 0,
        "discrepantRecords": 0,
        "status": "processing",
        "source": upload.source,
        "sourceEntityId": upload.source_entity_id,
        "sourceEntityName": upload.source_entity_name,
        "createdAt": now,
        "processedAt": None
    }
    
    valid_volunteers = []
    rejected_volunteers = []
    discrepant_volunteers = []
    
    # Get all CNICs for batch validation
    all_cnics = [row.cnic for row in upload.volunteers]
    
    # Batch validate CNICs - mark all as valid for now
    cnic_validation = {}
    
    for cnic in all_cnics:
        # Simple CNIC format validation
        normalized = normalize_cnic(cnic)
        # Accept any CNIC that normalizes correctly
        cnic_validation[cnic] = {"valid": True, "name": None}
    
    # Track volunteers by CNIC for duplicate/discrepancy detection
    cnic_records = {}  # cnic -> list of (event_number, duty_type, volunteer_id)
    
    # First pass: Load existing volunteers with same CNICs from database
    # TODO: Query actual database for existing records
    
    # Process each row
    for row in upload.volunteers:
        normalized_cnic = normalize_cnic(row.cnic)
        event_id = get_event_id(row.event_number)
        duty_type_id = get_duty_type_id(row.duty_type)
        access_level = row.access_level or get_access_level_for_duty(row.duty_type)
        band_color = get_band_color(access_level)
        
        volunteer_id = generate_volunteer_id()
        
        volunteer = {
            "id": f"vol-{uuid.uuid4().hex[:8]}",
            "volunteerId": volunteer_id,
            "cnic": row.cnic,
            "name": row.name,
            "eventId": event_id,
            "eventNumber": row.event_number,
            "dutyTypeId": duty_type_id,
            "dutyTypeName": row.duty_type,
            "accessLevel": access_level,
            "accessLevelName": ACCESS_LEVEL_NAMES.get(access_level, f"Level {access_level}"),
            "region": upload.region,
            "source": upload.source,
            "sourceEntityId": upload.source_entity_id,
            "sourceEntityName": upload.source_entity_name,
            "uploadBatchId": batch_id,
            "status": VolunteerStatus.PENDING,
            "validationErrors": [],
            "printStatus": PrintStatus.NOT_PRINTED,
            "cnicVerified": False,
            "createdAt": now
        }
        
        errors = []
        
        # 1. Check CNIC validation
        cnic_check = cnic_validation.get(row.cnic, {"valid": False})
        if not cnic_check["valid"]:
            errors.append(ValidationResult(
                is_valid=False,
                error_type=ValidationError.CNIC_NOT_FOUND,
                error_message="CNIC not found in enrollment database"
            ))
            volunteer["status"] = VolunteerStatus.REJECTED
            volunteer["validationErrors"] = errors
            rejected_volunteers.append(volunteer)
            continue
        else:
            volunteer["cnicVerified"] = True
        
        # 2. Check for duplicates and discrepancies
        if normalized_cnic in cnic_records:
            existing = cnic_records[normalized_cnic]
            
            for prev_event, prev_duty, prev_id in existing:
                if prev_event == row.event_number and prev_duty == row.duty_type:
                    # Exact duplicate - same CNIC, same event, same duty
                    errors.append(ValidationResult(
                        is_valid=False,
                        error_type=ValidationError.DUPLICATE_SAME_DUTY,
                        error_message="Duplicate: Same CNIC, event, and duty type already exists",
                        conflicting_records=[prev_id]
                    ))
                    volunteer["status"] = VolunteerStatus.REJECTED
                    break
                elif prev_event == row.event_number and prev_duty != row.duty_type:
                    # Discrepant - same CNIC, same event, different duty
                    errors.append(ValidationResult(
                        is_valid=False,
                        error_type=ValidationError.DISCREPANT_DIFFERENT_DUTIES,
                        error_message="Discrepant: Same CNIC with different duties in same event",
                        conflicting_records=[prev_id]
                    ))
                    volunteer["status"] = VolunteerStatus.DISCREPANT
                elif prev_event != row.event_number:
                    # Multiple events - same CNIC, different events
                    errors.append(ValidationResult(
                        is_valid=False,
                        error_type=ValidationError.DISCREPANT_MULTIPLE_EVENTS,
                        error_message="Discrepant: Same CNIC appears in multiple events",
                        conflicting_records=[prev_id]
                    ))
                    volunteer["status"] = VolunteerStatus.DISCREPANT
        
        volunteer["validationErrors"] = errors
        
        # Track this volunteer
        if normalized_cnic not in cnic_records:
            cnic_records[normalized_cnic] = []
        cnic_records[normalized_cnic].append((row.event_number, row.duty_type, volunteer["id"]))
        
        # Categorize result
        if volunteer["status"] == VolunteerStatus.REJECTED:
            rejected_volunteers.append(volunteer)
        elif volunteer["status"] == VolunteerStatus.DISCREPANT:
            discrepant_volunteers.append(volunteer)
        else:
            volunteer["status"] = VolunteerStatus.VALID
            valid_volunteers.append(volunteer)
        
        # Store volunteer
        _volunteers_db[volunteer["id"]] = volunteer
    
    # Update batch counts
    batch["validRecords"] = len(valid_volunteers)
    batch["rejectedRecords"] = len(rejected_volunteers)
    batch["discrepantRecords"] = len(discrepant_volunteers)
    batch["status"] = "completed"
    batch["processedAt"] = datetime.utcnow()
    
    _batches_db[batch_id] = batch
    
@volunteer_router.get("/volunteers/validation/{batch_id}", response_model=BulkValidationResult)
async def get_validation_results(
    batch_id: str,
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Get validation results for a batch"""
    if batch_id not in _batches_db:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    batch_volunteers = [v for v in _volunteers_db.values() if v.get("uploadBatchId") == batch_id]
    
    valid = [v for v in batch_volunteers if v["status"] == VolunteerStatus.VALID]
    rejected = [v for v in batch_volunteers if v["status"] == VolunteerStatus.REJECTED]
    discrepant = [v for v in batch_volunteers if v["status"] == VolunteerStatus.DISCREPANT]
    
    return BulkValidationResult(
        batch_id=batch_id,
        total_records=len(batch_volunteers),
        valid_records=valid,
        rejected_records=rejected,
        discrepant_records=discrepant
    )


# ============================================
# VOLUNTEER CRUD
# ============================================

@volunteer_router.get("/volunteers", response_model=VolunteersResponse)
async def get_volunteers(
    region: Optional[Region] = Query(None),
    status: Optional[VolunteerStatus] = Query(None),
    event_id: Optional[str] = Query(None, alias="eventId"),
    access_level: Optional[int] = Query(None, alias="accessLevel"),
    cnic: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    batch_id: Optional[str] = Query(None, alias="batchId"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100, alias="pageSize"),
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Get paginated list of volunteers with filters"""
    # Filter volunteers
    filtered = list(_volunteers_db.values())
    
    if region:
        filtered = [v for v in filtered if v.get("region") == region]
    if status:
        filtered = [v for v in filtered if v.get("status") == status]
    if event_id:
        filtered = [v for v in filtered if v.get("eventId") == event_id]
    if access_level:
        filtered = [v for v in filtered if v.get("accessLevel") == access_level]
    if cnic:
        filtered = [v for v in filtered if cnic in v.get("cnic", "")]
    if name:
        filtered = [v for v in filtered if name.lower() in v.get("name", "").lower()]
    if batch_id:
        filtered = [v for v in filtered if v.get("uploadBatchId") == batch_id]
    
    # Paginate
    total = len(filtered)
    total_pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = start + page_size
    page_data = filtered[start:end]
    
    return VolunteersResponse(
        data=page_data,
        pagination=Pagination(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )
    )


@volunteer_router.get("/volunteers/{volunteer_id}", response_model=VolunteerResponse)
async def get_volunteer(
    volunteer_id: str,
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Get a specific volunteer"""
    volunteer = _volunteers_db.get(volunteer_id)
    if not volunteer:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    return volunteer


@volunteer_router.get("/volunteers/cnic/{cnic}")
async def get_volunteers_by_cnic(
    cnic: str,
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Get all volunteers with a specific CNIC"""
    normalized = normalize_cnic(cnic)
    matches = [v for v in _volunteers_db.values() 
               if normalize_cnic(v.get("cnic", "")) == normalized]
    return matches


# ============================================
# APPROVAL WORKFLOW
# ============================================

@volunteer_router.post("/volunteers/approve")
async def approve_volunteers(
    data: VolunteerApprovalFormData,
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Approve or reject volunteers"""
    now = datetime.utcnow()
    updated = 0
    
    for vol_id in data.volunteer_ids:
        if vol_id in _volunteers_db:
            volunteer = _volunteers_db[vol_id]
            
            if data.action == "approve":
                volunteer["status"] = VolunteerStatus.APPROVED
                volunteer["approvedAt"] = now
                volunteer["approvedBy"] = "current-user"  # TODO: Get from auth
            else:
                volunteer["status"] = VolunteerStatus.REJECTED
                volunteer["validationErrors"].append(ValidationResult(
                    is_valid=False,
                    error_message=data.reason or "Rejected by user"
                ))
            
            updated += 1
    
    return {
        "success": True,
        "message": f"{updated} volunteers {data.action}d successfully"
    }


@volunteer_router.post("/volunteers/submit")
async def submit_volunteers(
    volunteer_ids: List[str],
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Submit volunteers for checker approval"""
    now = datetime.utcnow()
    updated = 0
    
    for vol_id in volunteer_ids:
        if vol_id in _volunteers_db:
            volunteer = _volunteers_db[vol_id]
            
            # Only submit valid/approved volunteers
            if volunteer["status"] in [VolunteerStatus.VALID, VolunteerStatus.APPROVED]:
                volunteer["status"] = VolunteerStatus.SUBMITTED
                volunteer["submittedAt"] = now
                volunteer["submittedBy"] = "current-user"
                updated += 1
    
    return {
        "success": True,
        "message": f"{updated} volunteers submitted successfully"
    }


# ============================================
# NEW SIMPLE UPLOAD ENDPOINT
# ============================================

@volunteer_router.post("/import-batch")
async def import_batch_new(
    batch_data: dict,
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """
    NEW ENDPOINT - Import batch to import_file table.
    Accepts: fileName, recordCount
    Table columns: id, user_id, import_at, file_name, record_count, status, created_at, updated_at
    """
    now = datetime.utcnow()
    
    try:
        # Insert directly into import_file table using raw SQL
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
                "user_id": 5,  # Default to user 5 (from login)
                "import_at": now,
                "file_name": batch_data.get("fileName", "unknown"),
                "record_count": batch_data.get("recordCount", 0),
                "status": "pending",
                "created_at": now,
                "updated_at": now
            }
        )
        
        # Get the inserted ID
        import_file_id = result.scalar()
        await volunteer_db.commit()
        
        return {
            "success": True,
            "message": "Batch imported successfully",
            "importFileId": import_file_id,
            "fileName": batch_data.get("fileName"),
            "recordCount": batch_data.get("recordCount", 0),
            "status": "pending",
            "importAt": now.isoformat(),
            "createdAt": now.isoformat()
        }
    
    except Exception as e:
        await volunteer_db.rollback()
# ============================================
# OLD UPLOAD ENDPOINT (kept for compatibility)
# ============================================

# ============================================
# DASHBOARD
# ============================================

@volunteer_router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(
    region: Optional[Region] = Query(None),
    event_number: Optional[int] = Query(None, alias="eventNumber"),
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Get dashboard statistics"""
    # Filter volunteers
    filtered = list(_volunteers_db.values())
    
    if region:
        filtered = [v for v in filtered if v.get("region") == region]
    if event_number:
        filtered = [v for v in filtered if v.get("eventNumber") == event_number]
    
    # Calculate totals
    total_required = 9 * 3500  # 9 events × 3500 volunteers
    total_received = len(filtered)
    total_valid = len([v for v in filtered if v["status"] == VolunteerStatus.VALID])
    total_rejected = len([v for v in filtered if v["status"] == VolunteerStatus.REJECTED])
    total_discrepant = len([v for v in filtered if v["status"] == VolunteerStatus.DISCREPANT])
    total_approved = len([v for v in filtered if v["status"] == VolunteerStatus.APPROVED])
    total_printed = len([v for v in filtered if v["status"] == VolunteerStatus.PRINTED])
    total_dispatched = len([v for v in filtered if v["status"] == VolunteerStatus.DISPATCHED])
    
    received_pct = (total_received / total_required * 100) if total_required > 0 else 0
    printed_pct = (total_printed / total_required * 100) if total_required > 0 else 0
    
    # Stats by region
    by_region = []
    for r in Region:
        r_vols = [v for v in filtered if v.get("region") == r]
        by_region.append(RegionStats(
            region=r,
            total=len(r_vols),
            valid=len([v for v in r_vols if v["status"] == VolunteerStatus.VALID]),
            rejected=len([v for v in r_vols if v["status"] == VolunteerStatus.REJECTED]),
            discrepant=len([v for v in r_vols if v["status"] == VolunteerStatus.DISCREPANT]),
            approved=len([v for v in r_vols if v["status"] == VolunteerStatus.APPROVED]),
            printed=len([v for v in r_vols if v["status"] == VolunteerStatus.PRINTED]),
            dispatched=len([v for v in r_vols if v["status"] == VolunteerStatus.DISPATCHED])
        ))
    
    # Stats by event
    by_event = []
    for i in range(1, 10):
        e_vols = [v for v in filtered if v.get("eventNumber") == i]
        required = 4350 if i == 9 else 3500
        received = len(e_vols)
        by_event.append(EventStats(
            event_number=i,
            event_name=f"Didar Mubarak - Event {i}",
            required=required,
            received=received,
            valid=len([v for v in e_vols if v["status"] == VolunteerStatus.VALID]),
            approved=len([v for v in e_vols if v["status"] == VolunteerStatus.APPROVED]),
            printed=len([v for v in e_vols if v["status"] == VolunteerStatus.PRINTED]),
            percentage=(received / required * 100) if required > 0 else 0
        ))
    
    # Stats by access level
    by_access_level = []
    for level in range(1, 6):
        l_vols = [v for v in filtered if v.get("accessLevel") == level]
        by_access_level.append(AccessLevelStats(
            access_level=level,
            access_level_name=ACCESS_LEVEL_NAMES.get(level, f"Level {level}"),
            band_color=ACCESS_LEVEL_BAND_COLORS.get(level, "#808080"),
            required=0,  # TODO: Get from quotas
            received=len(l_vols),
            valid=len([v for v in l_vols if v["status"] == VolunteerStatus.VALID]),
            printed=len([v for v in l_vols if v["status"] == VolunteerStatus.PRINTED])
        ))
    
    return DashboardStats(
        total_required=total_required,
        total_received=total_received,
        total_valid=total_valid,
        total_rejected=total_rejected,
        total_discrepant=total_discrepant,
        total_approved=total_approved,
        total_printed=total_printed,
        total_dispatched=total_dispatched,
        received_percentage=round(received_pct, 2),
        printed_percentage=round(printed_pct, 2),
        by_region=by_region,
        by_event=by_event,
        by_access_level=by_access_level
    )


# ============================================
# UPLOAD BATCHES
# ============================================

@volunteer_router.get("/batches")
async def get_batches(
    region: Optional[Region] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100, alias="pageSize"),
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Get upload batches"""
    filtered = list(_batches_db.values())
    
    if region:
        filtered = [b for b in filtered if b.get("region") == region]
    if status:
        filtered = [b for b in filtered if b.get("status") == status]
    
    # Sort by createdAt desc
    filtered.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
    
    # Paginate
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    
    return {
        "data": filtered[start:end],
        "pagination": {
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size
        }
    }


@volunteer_router.get("/batches/{batch_id}")
async def get_batch(
    batch_id: str,
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Get a specific batch"""
    if batch_id not in _batches_db:
        raise HTTPException(status_code=404, detail="Batch not found")
    return _batches_db[batch_id]


# ============================================
# EVENT ACCESS LEVEL DUTY REQUIREMENTS
# ============================================


@volunteer_router.get("/event-access-level-duty-requirements")
async def get_event_access_level_duty_requirements(
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Return event access-level duty requirements with related names.

    This returns strings (names) for event, access level and duty type
    and a list of band type names (if any) instead of numeric IDs.
    """
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

    result = await volunteer_db.execute(sql)
    rows = result.fetchall()

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


@volunteer_router.post("/volunteers/by-import-or-user")
async def get_volunteers_by_user_or_import(
    query: VolunteerRecordQuery,
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Return volunteer_record rows filtered by `checker_id` (userId).

    Request body: { "userId": int }
    Returns event, access level, and duty type names instead of IDs.
    """
    sql = """
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
    """
    params = {"userId": query.userId}

    stmt = text(sql)
    result = await volunteer_db.execute(stmt, params)
    rows = result.fetchall()

    out = []
    for r in rows:
        m = r._mapping
        out.append({
            "id": m.get("id"),
            "recordNumber": m.get("record_number"),
            "cnic": m.get("cnic"),
            "name": m.get("name"),
            "register": m.get("register"),
            "eventName": m.get("event_name"),
            "accessLevelName": m.get("access_level_name"),
            "dutyTypeName": m.get("duty_type_name"),
            "recordStatus": m.get("record_status"),
            "decisionStatus": m.get("decision_status"),
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
async def check_cnic_usage_batch(
    query: CNICBatchQuery,
    census_db: AsyncSession = Depends(census_db_session)
):
    """Check which CNICs are NOT found in census database.
    
    Checks both FamilyLevelDetails.IdNumber and form.HouseHoldCNIC tables.
    Returns only CNICs that don't exist in either table.
    
    Request body: { "cnics": ["3710123456789", "3710987654321", ...] }
    Response: { "notFound": ["3710123456789"], "found": ["3710987654321"] }
    """
    if not query.cnics:
        return {"notFound": [], "found": []}
    
    # Normalize CNICs (remove dashes)
    normalized_cnics = [cnic.replace("-", "").strip() for cnic in query.cnics]
    
    try:
        # Check in FamilyLevelDetails table
        family_sql = text("""
            SELECT DISTINCT "IdNumber" 
            FROM "FamilyLevelDetails"
            WHERE "IdNumber" = ANY(:cnics)
        """)
        family_result = await census_db.execute(family_sql, {"cnics": normalized_cnics})
        family_found = set(row[0] for row in family_result.fetchall())
        
        # Try to check in form table (may not exist)
        form_found = set()
        try:
            form_sql = text("""
                SELECT DISTINCT "HouseHoldCNIC"
                FROM "form"
                WHERE "HouseHoldCNIC" = ANY(:cnics)
            """)
            form_result = await census_db.execute(form_sql, {"cnics": normalized_cnics})
            form_found = set(row[0] for row in form_result.fetchall())
        except Exception as form_error:
            logger.warning(f"Could not query form table: {str(form_error)}")
        
        # Combine all found CNICs
        all_found = family_found.union(form_found)
        
        # Find CNICs not in either table
        not_found = [cnic for cnic in normalized_cnics if cnic not in all_found]
        found = [cnic for cnic in normalized_cnics if cnic in all_found]
        
        return {
            "notFound": not_found,
            "found": found,
            "totalChecked": len(normalized_cnics),
            "totalFound": len(found),
            "totalNotFound": len(not_found)
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking CNIC usage: {str(e)}"
        )


# SINGLE VOLUNTEER RECORD INSERT
# ============================================


class VolunteerRecordCreate(BaseModel):
    sno: int = Field(..., alias="Sno")
    userId: int = Field(..., alias="userId")
    cnic: Optional[str] = None
    name: Optional[str] = None
    # `event`, `accessLevel`, `dutyType` may be provided as numeric IDs or as names (strings).
    event: Optional[Union[int, str]] = None
    access_level: Optional[Union[int, str]] = Field(None, alias="accessLevel")
    duty_type: Optional[Union[int, str]] = Field(None, alias="dutyType")
    import_id: Optional[int] = Field(None, alias="importId")
    decision_status: Optional[str] = Field("pending", alias="decisionStatus")
    register: Optional[str] = Field(None, alias="register")


@volunteer_router.post("/volunteers/record")
async def create_volunteer_record(
    record: VolunteerRecordCreate,
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Insert a single volunteer record into `volunteer_record` table.

    Fields expected from frontend: Sno, userId, cnic, name, event, Access level, Duty Type
    """
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

    # Resolve names to IDs when strings are provided
    event_id = await _resolve_name_to_id(volunteer_db, "events", record.event)
    access_level_id = await _resolve_name_to_id(volunteer_db, "access_levels", record.access_level)
    duty_type_id = await _resolve_name_to_id(volunteer_db, "duty_types", record.duty_type)

    params = {
        "record_number": record.sno,
        "cnic": record.cnic,
        "name": record.name,
        "event_id": event_id,
        "access_level_id": access_level_id,
        "duty_type_id": duty_type_id,
        "record_status": "maker",
        "decision_status": record.decision_status,
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
        return {"success": True, "id": inserted_id}
    except Exception as e:
        await volunteer_db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@volunteer_router.post("/volunteers/records")
async def create_volunteer_records(
    records: List[VolunteerRecordCreate],
    volunteer_db: AsyncSession = Depends(volunteer_db_session),
    census_db: AsyncSession = Depends(census_db_session)
):
    """Bulk insert multiple volunteer records in one call. Accepts large lists (1000+ items)."""
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

        # Normalize CNICs and pre-check enrollment in census DB
        cnics = [normalize_cnic(r.cnic or "") for r in records]
        normalized_unique = list({c for c in cnics if c})

        family_sql = text("""
            SELECT DISTINCT "IdNumber" 
            FROM "FamilyLevelDetails"
            WHERE "IdNumber" = ANY(:cnics)
        """)
        family_found = set()
        try:
            fam_res = await census_db.execute(family_sql, {"cnics": normalized_unique})
            family_found = set(row[0] for row in fam_res.fetchall())
        except Exception:
            # census DB may not be available; treat as unknown (assume found=False)
            family_found = set()

        form_found = set()
        try:
            form_sql = text("""
                SELECT DISTINCT "HouseHoldCNIC"
                FROM "form"
                WHERE "HouseHoldCNIC" = ANY(:cnics)
            """)
            form_res = await census_db.execute(form_sql, {"cnics": normalized_unique})
            form_found = set(row[0] for row in form_res.fetchall())
        except Exception:
            form_found = set()

        enrollment_found = family_found.union(form_found)

        # Load existing volunteer_record rows for these CNICs
        existing_rows = {}
        if normalized_unique:
            ex_sql = text("""
                SELECT id, cnic, event_id, access_level_id, duty_type_id, record_status
                FROM volunteer_record
                WHERE replace(coalesce(cnic,''),'-','') = ANY(:cnics)
            """)
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

            # If enrollment not found -> mark all incoming as Rejected
            if cnic and cnic not in enrollment_found:
                for inc in incs:
                    inc["decision_status"] = "Rejected"
                    inc["reason"] = "CNIC not found in enrollment"
                continue

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

        return {"success": True, "inserted": len(inserted_ids), "ids": inserted_ids}
    except HTTPException:
        await volunteer_db.rollback()
        raise
    except Exception as e:
        await volunteer_db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "success": True,
        "totalProcessed": len(records),
        "approved": len(approved_ids),
        "discrepant1": len(discrepant_1_ids),
        "discrepant2": len(discrepant_2_ids),
        "approvedIds": approved_ids,
        "discrepant1Ids": discrepant_1_ids,
        "discrepant2Ids": discrepant_2_ids,
    }
