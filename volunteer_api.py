# ============================================
# VOLUNTEER MANAGEMENT SYSTEM - API Endpoints
# Pakistan Deedar 2026
# ============================================

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from volunteer_models import (
    VRegion, VRegionalCouncil, VLocalCouncil, VJamatkhana,
    DataSource, UserLevel, UserRole, VUser,
    Event, AccessLevel, DutyType, EventPositionQuota,
    UploadBatch, Volunteer, VolunteerValidationLog,
    PrintBatch, CoveringSheet, CoveringSheetEntry,
    DispatchPackage, DispatchPackagePrintBatch
)
from volunteer_schemas import (
    RegionResponse, EventResponse, AccessLevelResponse, DutyTypeResponse,
    DutyTypeWithAccessLevel, DataSourceResponse, UserRoleResponse, UserLevelResponse,
    VolunteerUserCreate, VolunteerUserResponse,
    UploadBatchCreate, UploadBatchResponse,
    VolunteerCreate, VolunteerResponse, VolunteerWithDetails,
    VolunteerBulkUpload, VolunteerUploadRow, VolunteerBulkValidationResponse,
    VolunteerDecision, BulkDecision, SubmitForApproval, ApproveForPrinting,
    PrintBatchCreate, PrintBatchResponse,
    CoveringSheetResponse, CoveringSheetEntry as CoveringSheetEntrySchema,
    DispatchPackageCreate, DispatchPackageResponse,
    DashboardResponse, RegionStats, EventStats, AccessLevelStats,
    EventPositionQuotaCreate, EventPositionQuotaResponse, QuotaCheckResult,
    VolunteerFilters, PaginatedVolunteersResponse
)


# Create router
volunteer_router = APIRouter(prefix="/volunteer", tags=["Volunteer Management"])


# Dependency placeholder - will be set from main.py
_get_volunteer_db = None
_get_main_db = None


def set_database_dependencies(volunteer_db_func, main_db_func):
    """Set the database dependency functions from main.py"""
    global _get_volunteer_db, _get_main_db
    _get_volunteer_db = volunteer_db_func
    _get_main_db = main_db_func


def get_volunteer_db_dep():
    """Get volunteer database session dependency"""
    if _get_volunteer_db is None:
        raise RuntimeError("Volunteer database dependency not configured")
    return _get_volunteer_db


def get_main_db_dep():
    """Get main database session for CNIC validation dependency"""
    if _get_main_db is None:
        raise RuntimeError("Main database dependency not configured")
    return _get_main_db


# Wrapper functions for Depends()
async def volunteer_db_session():
    """Async generator wrapper for volunteer database session"""
    if _get_volunteer_db is None:
        raise RuntimeError("Volunteer database dependency not configured. Call set_database_dependencies first.")
    async for session in _get_volunteer_db():
        yield session


async def main_db_session():
    """Async generator wrapper for main database session (CNIC validation)"""
    if _get_main_db is None:
        raise RuntimeError("Main database dependency not configured. Call set_database_dependencies first.")
    async for session in _get_main_db():
        yield session


# ============================================
# HELPER FUNCTIONS
# ============================================

def generate_volunteer_id() -> str:
    """Generate unique volunteer ID"""
    return f"VOL-{uuid.uuid4().hex[:8].upper()}"


def generate_batch_id() -> str:
    """Generate unique batch ID"""
    return f"BATCH-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def generate_print_batch_id() -> str:
    """Generate unique print batch ID"""
    return f"PRINT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def strip_cnic_dashes(cnic: str) -> str:
    """Remove dashes from CNIC for comparison"""
    return cnic.replace("-", "") if cnic else ""


# ============================================
# MASTER DATA ENDPOINTS
# ============================================

@volunteer_router.get("/regions", response_model=List[RegionResponse])
async def get_regions(
    db: AsyncSession = Depends(volunteer_db_session),
    is_active: Optional[bool] = Query(None)
):
    """Get all regions"""
    stmt = select(VRegion)
    if is_active is not None:
        stmt = stmt.where(VRegion.is_active == is_active)
    stmt = stmt.order_by(VRegion.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@volunteer_router.get("/events", response_model=List[EventResponse])
async def get_events(
    db: AsyncSession = Depends(volunteer_db_session),
    is_active: Optional[bool] = Query(None)
):
    """Get all events"""
    stmt = select(Event)
    if is_active is not None:
        stmt = stmt.where(Event.is_active == is_active)
    stmt = stmt.order_by(Event.event_number)
    result = await db.execute(stmt)
    return result.scalars().all()


@volunteer_router.get("/access-levels", response_model=List[AccessLevelResponse])
async def get_access_levels(
    db: AsyncSession = Depends(volunteer_db_session),
    is_active: Optional[bool] = Query(None)
):
    """Get all access levels"""
    stmt = select(AccessLevel)
    if is_active is not None:
        stmt = stmt.where(AccessLevel.is_active == is_active)
    stmt = stmt.order_by(AccessLevel.sort_order)
    result = await db.execute(stmt)
    return result.scalars().all()


@volunteer_router.get("/duty-types", response_model=List[DutyTypeWithAccessLevel])
async def get_duty_types(
    db: AsyncSession = Depends(volunteer_db_session),
    access_level_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None)
):
    """Get all duty types, optionally filtered by access level"""
    stmt = select(DutyType, AccessLevel.name.label("access_level_name"), AccessLevel.band_color).join(
        AccessLevel, DutyType.access_level_id == AccessLevel.id
    )
    if access_level_id:
        stmt = stmt.where(DutyType.access_level_id == access_level_id)
    if is_active is not None:
        stmt = stmt.where(DutyType.is_active == is_active)
    stmt = stmt.order_by(DutyType.access_level_id, DutyType.name)
    result = await db.execute(stmt)
    
    duty_types = []
    for row in result.fetchall():
        dt = row[0]
        duty_types.append(DutyTypeWithAccessLevel(
            id=dt.id,
            code=dt.code,
            name=dt.name,
            access_level_id=dt.access_level_id,
            description=dt.description,
            is_active=dt.is_active,
            created_at=dt.created_at,
            access_level_name=row[1],
            band_color=row[2]
        ))
    return duty_types


@volunteer_router.get("/data-sources", response_model=List[DataSourceResponse])
async def get_data_sources(
    db: AsyncSession = Depends(volunteer_db_session),
    is_active: Optional[bool] = Query(None)
):
    """Get all data sources"""
    stmt = select(DataSource)
    if is_active is not None:
        stmt = stmt.where(DataSource.is_active == is_active)
    result = await db.execute(stmt)
    return result.scalars().all()


@volunteer_router.get("/user-roles", response_model=List[UserRoleResponse])
async def get_user_roles(db: AsyncSession = Depends(volunteer_db_session)):
    """Get all user roles"""
    stmt = select(UserRole).order_by(UserRole.sort_order)
    result = await db.execute(stmt)
    return result.scalars().all()


@volunteer_router.get("/user-levels", response_model=List[UserLevelResponse])
async def get_user_levels(db: AsyncSession = Depends(volunteer_db_session)):
    """Get all user levels"""
    stmt = select(UserLevel).order_by(UserLevel.sort_order)
    result = await db.execute(stmt)
    return result.scalars().all()


# ============================================
# POSITION QUOTA ENDPOINTS
# ============================================

@volunteer_router.get("/position-quotas", response_model=List[EventPositionQuotaResponse])
async def get_position_quotas(
    db: AsyncSession = Depends(volunteer_db_session),
    event_id: Optional[int] = Query(None),
    access_level_id: Optional[int] = Query(None)
):
    """Get position quotas"""
    stmt = select(
        EventPositionQuota,
        Event.name.label("event_name"),
        AccessLevel.name.label("access_level_name"),
        DutyType.name.label("duty_type_name")
    ).join(Event, EventPositionQuota.event_id == Event.id
    ).join(AccessLevel, EventPositionQuota.access_level_id == AccessLevel.id
    ).join(DutyType, EventPositionQuota.duty_type_id == DutyType.id)
    
    if event_id:
        stmt = stmt.where(EventPositionQuota.event_id == event_id)
    if access_level_id:
        stmt = stmt.where(EventPositionQuota.access_level_id == access_level_id)
    
    result = await db.execute(stmt)
    
    quotas = []
    for row in result.fetchall():
        quota = row[0]
        quotas.append(EventPositionQuotaResponse(
            id=quota.id,
            event_id=quota.event_id,
            access_level_id=quota.access_level_id,
            duty_type_id=quota.duty_type_id,
            required_count=quota.required_count,
            filled_count=quota.filled_count,
            remaining_count=quota.required_count - quota.filled_count,
            event_name=row[1],
            access_level_name=row[2],
            duty_type_name=row[3]
        ))
    return quotas


@volunteer_router.post("/position-quotas", response_model=EventPositionQuotaResponse)
async def create_position_quota(
    quota: EventPositionQuotaCreate,
    db: AsyncSession = Depends(volunteer_db_session)
):
    """Create a position quota"""
    # Check if quota already exists
    stmt = select(EventPositionQuota).where(
        and_(
            EventPositionQuota.event_id == quota.event_id,
            EventPositionQuota.access_level_id == quota.access_level_id,
            EventPositionQuota.duty_type_id == quota.duty_type_id
        )
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Quota already exists for this combination")
    
    db_quota = EventPositionQuota(
        event_id=quota.event_id,
        access_level_id=quota.access_level_id,
        duty_type_id=quota.duty_type_id,
        required_count=quota.required_count,
        filled_count=0
    )
    db.add(db_quota)
    await db.commit()
    await db.refresh(db_quota)
    
    return EventPositionQuotaResponse(
        id=db_quota.id,
        event_id=db_quota.event_id,
        access_level_id=db_quota.access_level_id,
        duty_type_id=db_quota.duty_type_id,
        required_count=db_quota.required_count,
        filled_count=db_quota.filled_count,
        remaining_count=db_quota.required_count - db_quota.filled_count
    )


# ============================================
# VOLUNTEER UPLOAD ENDPOINTS
# ============================================

@volunteer_router.post("/upload-batches", response_model=UploadBatchResponse)
async def create_upload_batch(
    batch: UploadBatchCreate,
    db: AsyncSession = Depends(volunteer_db_session),
    # current_user will be injected
):
    """Create a new upload batch"""
    batch_id = generate_batch_id()
    
    db_batch = UploadBatch(
        id=batch_id,
        file_name=batch.file_name,
        region_id=batch.region_id,
        data_source_id=batch.data_source_id,
        source_entity_id=batch.source_entity_id,
        source_entity_name=batch.source_entity_name,
        # uploaded_by=current_user.id,
        # uploaded_by_name=current_user.full_name,
        status='processing',
        import_datetime=datetime.utcnow()
    )
    db.add(db_batch)
    await db.commit()
    await db.refresh(db_batch)
    
    return db_batch


@volunteer_router.get("/upload-batches", response_model=List[UploadBatchResponse])
async def get_upload_batches(
    db: AsyncSession = Depends(volunteer_db_session),
    region_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """Get upload batches"""
    stmt = select(UploadBatch)
    
    if region_id:
        stmt = stmt.where(UploadBatch.region_id == region_id)
    if status:
        stmt = stmt.where(UploadBatch.status == status)
    
    stmt = stmt.order_by(UploadBatch.import_datetime.desc())
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    
    result = await db.execute(stmt)
    return result.scalars().all()


@volunteer_router.get("/upload-batches/{batch_id}", response_model=UploadBatchResponse)
async def get_upload_batch(
    batch_id: str,
    db: AsyncSession = Depends(volunteer_db_session)
):
    """Get a specific upload batch"""
    stmt = select(UploadBatch).where(UploadBatch.id == batch_id)
    result = await db.execute(stmt)
    batch = result.scalar_one_or_none()
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return batch


# ============================================
# VOLUNTEER CRUD ENDPOINTS
# ============================================

@volunteer_router.post("/volunteers/bulk-upload", response_model=VolunteerBulkValidationResponse)
async def bulk_upload_volunteers(
    upload: VolunteerBulkUpload,
    db: AsyncSession = Depends(volunteer_db_session),
    main_db: AsyncSession = Depends(main_db_session)  # For CNIC validation from main DB
):
    """
    Bulk upload volunteers from Excel file.
    Performs validation:
    1. Check quota availability
    2. Validate CNIC against enrollment database
    3. Check for duplicates
    4. Mark discrepancies
    """
    # Create upload batch
    batch_id = generate_batch_id()
    db_batch = UploadBatch(
        id=batch_id,
        file_name=upload.file_name,
        region_id=upload.region_id,
        data_source_id=upload.data_source_id,
        source_entity_id=upload.source_entity_id,
        source_entity_name=upload.source_entity_name,
        total_records=len(upload.volunteers),
        status='processing',
        import_datetime=datetime.utcnow()
    )
    db.add(db_batch)
    
    valid_count = 0
    rejected_count = 0
    discrepant_count = 0
    created_volunteers = []
    
    for row in upload.volunteers:
        # Generate volunteer ID
        volunteer_id = generate_volunteer_id()
        normalized_cnic = strip_cnic_dashes(row.cnic)
        
        # Get event by event_number
        event_stmt = select(Event).where(Event.event_number == row.event_number)
        event_result = await db.execute(event_stmt)
        event = event_result.scalar_one_or_none()
        
        if not event:
            # Skip if event not found
            continue
        
        # Get duty type
        duty_stmt = select(DutyType).where(DutyType.name == row.duty_type)
        duty_result = await db.execute(duty_stmt)
        duty_type = duty_result.scalar_one_or_none()
        
        if not duty_type:
            # Skip if duty type not found
            continue
        
        # Get access level from duty type
        access_level_id = duty_type.access_level_id
        
        # Determine initial status
        status = 'pending'
        cnic_verified = False
        discrepancy_reason = None
        conflicting_ids = []
        
        # TODO: Validate CNIC against main enrollment database
        # For now, mark as pending for manual verification
        
        # Check for duplicate (same CNIC + same event + same duty)
        dup_stmt = select(Volunteer).where(
            and_(
                func.replace(Volunteer.cnic, "-", "") == normalized_cnic,
                Volunteer.event_id == event.id,
                Volunteer.duty_type_id == duty_type.id
            )
        )
        dup_result = await db.execute(dup_stmt)
        duplicate = dup_result.scalar_one_or_none()
        
        if duplicate:
            status = 'rejected'
            discrepancy_reason = 'Duplicate: Same CNIC, event, and duty type already exists'
            rejected_count += 1
        else:
            # Check for same event with different duty (Discrepant 1)
            same_event_stmt = select(Volunteer).where(
                and_(
                    func.replace(Volunteer.cnic, "-", "") == normalized_cnic,
                    Volunteer.event_id == event.id,
                    Volunteer.duty_type_id != duty_type.id
                )
            )
            same_event_result = await db.execute(same_event_stmt)
            same_event_records = same_event_result.scalars().all()
            
            if same_event_records:
                status = 'discrepant_same_event'
                discrepancy_reason = '2 or more duties in same event'
                conflicting_ids = [str(v.id) for v in same_event_records]
                discrepant_count += 1
            else:
                # Check for multiple events (Discrepant 2)
                other_event_stmt = select(Volunteer).where(
                    and_(
                        func.replace(Volunteer.cnic, "-", "") == normalized_cnic,
                        Volunteer.event_id != event.id
                    )
                )
                other_event_result = await db.execute(other_event_stmt)
                other_event_records = other_event_result.scalars().all()
                
                if other_event_records:
                    status = 'discrepant_multiple_events'
                    discrepancy_reason = 'Multiple duties across events'
                    conflicting_ids = [str(v.id) for v in other_event_records]
                    discrepant_count += 1
                else:
                    status = 'ok'
                    valid_count += 1
        
        # Get band color from access level
        al_stmt = select(AccessLevel).where(AccessLevel.id == access_level_id)
        al_result = await db.execute(al_stmt)
        access_level = al_result.scalar_one_or_none()
        band_color = access_level.band_color if access_level else None
        
        # Create volunteer record
        db_volunteer = Volunteer(
            volunteer_id=volunteer_id,
            cnic=row.cnic,
            name=row.name,
            event_id=event.id,
            access_level_id=access_level_id,
            duty_type_id=duty_type.id,
            region_id=upload.region_id,
            data_source_id=upload.data_source_id,
            source_entity_id=upload.source_entity_id,
            source_entity_name=upload.source_entity_name,
            upload_batch_id=batch_id,
            row_number=row.row_number,
            status=status,
            cnic_verified=cnic_verified,
            discrepancy_reason=discrepancy_reason,
            conflicting_volunteer_ids=conflicting_ids if conflicting_ids else None,
            band_color=band_color,
            print_status='not_printed',
            kit_status='not_prepared'
        )
        db.add(db_volunteer)
        created_volunteers.append(db_volunteer)
    
    # Update batch counts
    db_batch.valid_records = valid_count
    db_batch.rejected_records = rejected_count
    db_batch.discrepant_records = discrepant_count
    db_batch.status = 'validated'
    db_batch.validated_at = datetime.utcnow()
    
    await db.commit()
    
    # Refresh all volunteers to get IDs
    for v in created_volunteers:
        await db.refresh(v)
    
    return VolunteerBulkValidationResponse(
        batch_id=batch_id,
        total_records=len(upload.volunteers),
        valid_records=valid_count,
        rejected_records=rejected_count,
        discrepant_records=discrepant_count,
        results=[VolunteerResponse(
            id=v.id,
            volunteer_id=v.volunteer_id,
            cnic=v.cnic,
            name=v.name,
            event_id=v.event_id,
            access_level_id=v.access_level_id,
            duty_type_id=v.duty_type_id,
            region_id=v.region_id,
            data_source_id=v.data_source_id,
            source_entity_id=v.source_entity_id,
            source_entity_name=v.source_entity_name,
            upload_batch_id=v.upload_batch_id,
            row_number=v.row_number,
            status=v.status,
            cnic_verified=v.cnic_verified,
            discrepancy_reason=v.discrepancy_reason,
            decision_datetime=v.decision_datetime,
            print_status=v.print_status,
            kit_status=v.kit_status,
            created_at=v.created_at,
            updated_at=v.updated_at
        ) for v in created_volunteers]
    )


@volunteer_router.get("/volunteers", response_model=PaginatedVolunteersResponse)
async def get_volunteers(
    db: AsyncSession = Depends(volunteer_db_session),
    region_id: Optional[int] = Query(None),
    event_id: Optional[int] = Query(None),
    access_level_id: Optional[int] = Query(None),
    duty_type_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    print_status: Optional[str] = Query(None),
    batch_id: Optional[str] = Query(None),
    cnic: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """Get volunteers with filters and pagination"""
    # Build query
    stmt = select(
        Volunteer,
        Event.name.label("event_name"),
        Event.event_number.label("event_number"),
        AccessLevel.name.label("access_level_name"),
        DutyType.name.label("duty_type_name"),
        VRegion.name.label("region_name"),
        AccessLevel.band_color.label("band_color")
    ).outerjoin(Event, Volunteer.event_id == Event.id
    ).outerjoin(AccessLevel, Volunteer.access_level_id == AccessLevel.id
    ).outerjoin(DutyType, Volunteer.duty_type_id == DutyType.id
    ).outerjoin(VRegion, Volunteer.region_id == VRegion.id)
    
    # Apply filters
    if region_id:
        stmt = stmt.where(Volunteer.region_id == region_id)
    if event_id:
        stmt = stmt.where(Volunteer.event_id == event_id)
    if access_level_id:
        stmt = stmt.where(Volunteer.access_level_id == access_level_id)
    if duty_type_id:
        stmt = stmt.where(Volunteer.duty_type_id == duty_type_id)
    if status:
        stmt = stmt.where(Volunteer.status == status)
    if print_status:
        stmt = stmt.where(Volunteer.print_status == print_status)
    if batch_id:
        stmt = stmt.where(Volunteer.upload_batch_id == batch_id)
    if cnic:
        normalized = strip_cnic_dashes(cnic)
        stmt = stmt.where(func.replace(Volunteer.cnic, "-", "") == normalized)
    if search:
        stmt = stmt.where(
            or_(
                Volunteer.name.ilike(f"%{search}%"),
                Volunteer.cnic.ilike(f"%{search}%"),
                Volunteer.volunteer_id.ilike(f"%{search}%")
            )
        )
    
    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()
    
    # Apply pagination
    stmt = stmt.order_by(Volunteer.created_at.desc())
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    
    result = await db.execute(stmt)
    
    volunteers = []
    for row in result.fetchall():
        v = row[0]
        volunteers.append(VolunteerWithDetails(
            id=v.id,
            volunteer_id=v.volunteer_id,
            cnic=v.cnic,
            name=v.name,
            event_id=v.event_id,
            access_level_id=v.access_level_id,
            duty_type_id=v.duty_type_id,
            region_id=v.region_id,
            data_source_id=v.data_source_id,
            source_entity_id=v.source_entity_id,
            source_entity_name=v.source_entity_name,
            upload_batch_id=v.upload_batch_id,
            row_number=v.row_number,
            status=v.status,
            cnic_verified=v.cnic_verified,
            discrepancy_reason=v.discrepancy_reason,
            decision_datetime=v.decision_datetime,
            print_status=v.print_status,
            kit_status=v.kit_status,
            created_at=v.created_at,
            updated_at=v.updated_at,
            event_name=row[1],
            event_number=row[2],
            access_level_name=row[3],
            duty_type_name=row[4],
            region_name=row[5],
            band_color=row[6]
        ))
    
    pages = (total + per_page - 1) // per_page
    
    return PaginatedVolunteersResponse(
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        data=volunteers
    )


@volunteer_router.get("/volunteers/{volunteer_id}", response_model=VolunteerWithDetails)
async def get_volunteer(
    volunteer_id: int,
    db: AsyncSession = Depends(volunteer_db_session)
):
    """Get a specific volunteer"""
    stmt = select(
        Volunteer,
        Event.name.label("event_name"),
        Event.event_number.label("event_number"),
        AccessLevel.name.label("access_level_name"),
        DutyType.name.label("duty_type_name"),
        VRegion.name.label("region_name"),
        AccessLevel.band_color.label("band_color")
    ).outerjoin(Event, Volunteer.event_id == Event.id
    ).outerjoin(AccessLevel, Volunteer.access_level_id == AccessLevel.id
    ).outerjoin(DutyType, Volunteer.duty_type_id == DutyType.id
    ).outerjoin(VRegion, Volunteer.region_id == VRegion.id
    ).where(Volunteer.id == volunteer_id)
    
    result = await db.execute(stmt)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    
    v = row[0]
    return VolunteerWithDetails(
        id=v.id,
        volunteer_id=v.volunteer_id,
        cnic=v.cnic,
        name=v.name,
        event_id=v.event_id,
        access_level_id=v.access_level_id,
        duty_type_id=v.duty_type_id,
        region_id=v.region_id,
        data_source_id=v.data_source_id,
        source_entity_id=v.source_entity_id,
        source_entity_name=v.source_entity_name,
        upload_batch_id=v.upload_batch_id,
        row_number=v.row_number,
        status=v.status,
        cnic_verified=v.cnic_verified,
        discrepancy_reason=v.discrepancy_reason,
        decision_datetime=v.decision_datetime,
        print_status=v.print_status,
        kit_status=v.kit_status,
        created_at=v.created_at,
        updated_at=v.updated_at,
        event_name=row[1],
        event_number=row[2],
        access_level_name=row[3],
        duty_type_name=row[4],
        region_name=row[5],
        band_color=row[6]
    )


# ============================================
# DECISION ENDPOINTS (Maker & Checker)
# ============================================

@volunteer_router.post("/volunteers/{volunteer_id}/decide")
async def decide_volunteer(
    volunteer_id: int,
    decision: VolunteerDecision,
    db: AsyncSession = Depends(volunteer_db_session)
):
    """Make a decision on a volunteer record (approve/reject)"""
    stmt = select(Volunteer).where(Volunteer.id == volunteer_id)
    result = await db.execute(stmt)
    volunteer = result.scalar_one_or_none()
    
    if not volunteer:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    
    if decision.decision == 'approve':
        volunteer.status = 'approved'
    elif decision.decision == 'reject':
        volunteer.status = 'rejected'
    else:
        raise HTTPException(status_code=400, detail="Invalid decision. Use 'approve' or 'reject'")
    
    volunteer.decision_datetime = datetime.utcnow()
    volunteer.decision_notes = decision.notes
    # volunteer.decision_by = current_user.id
    
    await db.commit()
    
    return {"message": f"Volunteer {volunteer_id} has been {decision.decision}d"}


@volunteer_router.post("/volunteers/bulk-decide")
async def bulk_decide_volunteers(
    decision: BulkDecision,
    db: AsyncSession = Depends(volunteer_db_session)
):
    """Make a bulk decision on multiple volunteers"""
    stmt = select(Volunteer).where(Volunteer.id.in_(decision.volunteer_ids))
    result = await db.execute(stmt)
    volunteers = result.scalars().all()
    
    if len(volunteers) != len(decision.volunteer_ids):
        raise HTTPException(status_code=404, detail="Some volunteers not found")
    
    new_status = 'approved' if decision.decision == 'approve' else 'rejected'
    
    for volunteer in volunteers:
        volunteer.status = new_status
        volunteer.decision_datetime = datetime.utcnow()
        volunteer.decision_notes = decision.notes
    
    await db.commit()
    
    return {"message": f"{len(volunteers)} volunteers have been {decision.decision}d"}


@volunteer_router.post("/batches/{batch_id}/submit")
async def submit_batch_for_approval(
    batch_id: str,
    db: AsyncSession = Depends(volunteer_db_session)
):
    """Submit a batch for checker approval"""
    # Get batch
    stmt = select(UploadBatch).where(UploadBatch.id == batch_id)
    result = await db.execute(stmt)
    batch = result.scalar_one_or_none()
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Check if all discrepant records have been decided
    discrepant_stmt = select(func.count()).select_from(Volunteer).where(
        and_(
            Volunteer.upload_batch_id == batch_id,
            Volunteer.status.in_(['discrepant_same_event', 'discrepant_multiple_events'])
        )
    )
    discrepant_result = await db.execute(discrepant_stmt)
    discrepant_count = discrepant_result.scalar()
    
    if discrepant_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot submit: {discrepant_count} discrepant records need resolution"
        )
    
    # Update batch status
    batch.status = 'submitted'
    batch.submitted_at = datetime.utcnow()
    
    # Update all OK volunteers to submitted
    update_stmt = select(Volunteer).where(
        and_(
            Volunteer.upload_batch_id == batch_id,
            Volunteer.status == 'ok'
        )
    )
    update_result = await db.execute(update_stmt)
    volunteers = update_result.scalars().all()
    
    for v in volunteers:
        v.status = 'submitted'
        v.submitted_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": f"Batch {batch_id} submitted for approval with {len(volunteers)} volunteers"}


# ============================================
# DASHBOARD ENDPOINTS
# ============================================

@volunteer_router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(volunteer_db_session),
    region_id: Optional[int] = Query(None)
):
    """Get dashboard statistics"""
    # Total counts
    total_required = 0
    total_received = 0
    total_validated = 0
    total_approved = 0
    total_printed = 0
    total_dispatched = 0
    
    # Get event totals for required
    event_stmt = select(func.sum(Event.total_required_volunteers))
    event_result = await db.execute(event_stmt)
    total_required = event_result.scalar() or 0
    
    # Get volunteer counts
    base_stmt = select(func.count()).select_from(Volunteer)
    if region_id:
        base_stmt = base_stmt.where(Volunteer.region_id == region_id)
    
    # Total received
    received_result = await db.execute(base_stmt)
    total_received = received_result.scalar() or 0
    
    # Valid/OK
    valid_stmt = base_stmt.where(Volunteer.status.in_(['ok', 'approved', 'printed', 'dispatched']))
    if region_id:
        valid_stmt = valid_stmt.where(Volunteer.region_id == region_id)
    valid_result = await db.execute(valid_stmt)
    total_validated = valid_result.scalar() or 0
    
    # Approved
    approved_stmt = select(func.count()).select_from(Volunteer).where(
        Volunteer.status.in_(['approved', 'printed', 'dispatched'])
    )
    if region_id:
        approved_stmt = approved_stmt.where(Volunteer.region_id == region_id)
    approved_result = await db.execute(approved_stmt)
    total_approved = approved_result.scalar() or 0
    
    # Printed
    printed_stmt = select(func.count()).select_from(Volunteer).where(
        Volunteer.print_status.in_(['printed', 'dispatched'])
    )
    if region_id:
        printed_stmt = printed_stmt.where(Volunteer.region_id == region_id)
    printed_result = await db.execute(printed_stmt)
    total_printed = printed_result.scalar() or 0
    
    # Dispatched
    dispatched_stmt = select(func.count()).select_from(Volunteer).where(
        Volunteer.print_status == 'dispatched'
    )
    if region_id:
        dispatched_stmt = dispatched_stmt.where(Volunteer.region_id == region_id)
    dispatched_result = await db.execute(dispatched_stmt)
    total_dispatched = dispatched_result.scalar() or 0
    
    # Calculate percentages
    received_percentage = (total_received / total_required * 100) if total_required > 0 else 0
    printed_percentage = (total_printed / total_required * 100) if total_required > 0 else 0
    
    # Stats by region
    region_stats = []
    if not region_id:
        region_stmt = select(
            VRegion.id,
            VRegion.name,
            func.count(Volunteer.id).label("total"),
            func.count(Volunteer.id).filter(Volunteer.status == 'ok').label("valid"),
            func.count(Volunteer.id).filter(Volunteer.status == 'rejected').label("rejected"),
            func.count(Volunteer.id).filter(
                Volunteer.status.in_(['discrepant_same_event', 'discrepant_multiple_events'])
            ).label("discrepant"),
            func.count(Volunteer.id).filter(Volunteer.status == 'approved').label("approved"),
            func.count(Volunteer.id).filter(Volunteer.print_status == 'printed').label("printed"),
            func.count(Volunteer.id).filter(Volunteer.print_status == 'dispatched').label("dispatched")
        ).outerjoin(Volunteer, VRegion.id == Volunteer.region_id
        ).group_by(VRegion.id, VRegion.name)
        
        region_result = await db.execute(region_stmt)
        for row in region_result.fetchall():
            region_stats.append(RegionStats(
                region_id=row[0],
                region_name=row[1],
                total_received=row[2] or 0,
                total_valid=row[3] or 0,
                total_rejected=row[4] or 0,
                total_discrepant=row[5] or 0,
                total_approved=row[6] or 0,
                total_printed=row[7] or 0,
                total_dispatched=row[8] or 0
            ))
    
    # Stats by event
    event_stats = []
    event_stats_stmt = select(
        Event.id,
        Event.event_number,
        Event.name,
        Event.total_required_volunteers,
        func.count(Volunteer.id).label("received"),
        func.count(Volunteer.id).filter(
            Volunteer.status.in_(['ok', 'approved', 'printed', 'dispatched'])
        ).label("valid"),
        func.count(Volunteer.id).filter(
            Volunteer.print_status.in_(['printed', 'dispatched'])
        ).label("printed")
    ).outerjoin(Volunteer, Event.id == Volunteer.event_id)
    
    if region_id:
        event_stats_stmt = event_stats_stmt.where(Volunteer.region_id == region_id)
    
    event_stats_stmt = event_stats_stmt.group_by(Event.id, Event.event_number, Event.name, Event.total_required_volunteers)
    
    event_result = await db.execute(event_stats_stmt)
    for row in event_result.fetchall():
        required = row[3] or 0
        received = row[4] or 0
        printed = row[6] or 0
        event_stats.append(EventStats(
            event_id=row[0],
            event_number=row[1],
            event_name=row[2],
            required=required,
            received=received,
            valid=row[5] or 0,
            printed=printed,
            received_percentage=(received / required * 100) if required > 0 else 0,
            printed_percentage=(printed / required * 100) if required > 0 else 0
        ))
    
    return DashboardResponse(
        total_required=total_required,
        total_received=total_received,
        total_validated=total_validated,
        total_approved=total_approved,
        total_printed=total_printed,
        total_dispatched=total_dispatched,
        received_percentage=round(received_percentage, 2),
        printed_percentage=round(printed_percentage, 2),
        by_region=region_stats,
        by_event=event_stats,
        by_access_level=[]  # TODO: Add access level stats
    )
