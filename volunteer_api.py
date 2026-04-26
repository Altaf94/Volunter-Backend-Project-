# ============================================
# VOLUNTEER MANAGEMENT SYSTEM - API Endpoints
# Pakistan Deedar 2026
# ============================================

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from volunteer_models import (
    Event, AccessLevel, DutyType
)
from volunteer_schemas import (
    EventResponse, AccessLevelResponse, DutyTypeWithAccessLevel
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
