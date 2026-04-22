# ============================================
# VOLUNTEER MANAGEMENT SYSTEM - SQLAlchemy Models
# Pakistan Deedar 2026
# ============================================

import enum
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, 
    Enum as SQLEnum, ARRAY, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB


# ============================================
# ENUMS
# ============================================

class VolunteerStatusEnum(str, enum.Enum):
    PENDING = 'pending'
    OK = 'ok'
    REJECTED = 'rejected'
    DISCREPANT_SAME_EVENT = 'discrepant_same_event'
    DISCREPANT_MULTIPLE_EVENTS = 'discrepant_multiple_events'
    SUBMITTED = 'submitted'
    APPROVED = 'approved'
    PRINTED = 'printed'
    DISPATCHED = 'dispatched'


class PrintStatusEnum(str, enum.Enum):
    NOT_PRINTED = 'not_printed'
    PRINTING = 'printing'
    PRINTED = 'printed'
    DISPATCHED = 'dispatched'


class KitStatusEnum(str, enum.Enum):
    NOT_PREPARED = 'not_prepared'
    PREPARING = 'preparing'
    PREPARED = 'prepared'
    DISPATCHED = 'dispatched'
    RECEIVED = 'received'


class BatchStatusEnum(str, enum.Enum):
    PROCESSING = 'processing'
    VALIDATED = 'validated'
    SUBMITTED = 'submitted'
    APPROVED = 'approved'
    COMPLETED = 'completed'
    FAILED = 'failed'


class DispatchStatusEnum(str, enum.Enum):
    PREPARING = 'preparing'
    READY = 'ready'
    DISPATCHED = 'dispatched'
    RECEIVED = 'received'


# ============================================
# BASE CLASS
# ============================================

class VolunteerBase(DeclarativeBase):
    pass


# ============================================
# MASTER DATA MODELS
# ============================================

class VRegion(VolunteerBase):
    """6 Regions: Gilgit, Hunza, Gupis, Ishkoman, Lower Chitral, Upper Chitral"""
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    has_backup_printer: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    regional_councils: Mapped[List["VRegionalCouncil"]] = relationship("VRegionalCouncil", back_populates="region")
    volunteers: Mapped[List["Volunteer"]] = relationship("Volunteer", back_populates="region")
    upload_batches: Mapped[List["UploadBatch"]] = relationship("UploadBatch", back_populates="region")


class VRegionalCouncil(VolunteerBase):
    __tablename__ = "regional_councils"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    region_id: Mapped[int] = mapped_column(Integer, ForeignKey("regions.id"))
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    region: Mapped["VRegion"] = relationship("VRegion", back_populates="regional_councils")
    local_councils: Mapped[List["VLocalCouncil"]] = relationship("VLocalCouncil", back_populates="regional_council")


class VLocalCouncil(VolunteerBase):
    __tablename__ = "local_councils"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    regional_council_id: Mapped[str] = mapped_column(String(50), ForeignKey("regional_councils.id"))
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    regional_council: Mapped["VRegionalCouncil"] = relationship("VRegionalCouncil", back_populates="local_councils")
    jamatkhanas: Mapped[List["VJamatkhana"]] = relationship("VJamatkhana", back_populates="local_council")


class VJamatkhana(VolunteerBase):
    __tablename__ = "jamatkhanas"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    local_council_id: Mapped[str] = mapped_column(String(50), ForeignKey("local_councils.id"))
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    region_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("regions.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    local_council: Mapped["VLocalCouncil"] = relationship("VLocalCouncil", back_populates="jamatkhanas")


class DataSource(VolunteerBase):
    """Data Sources: Local Council, ITREB, Health Board, Regional Event Manager"""
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    volunteers: Mapped[List["Volunteer"]] = relationship("Volunteer", back_populates="data_source")
    upload_batches: Mapped[List["UploadBatch"]] = relationship("UploadBatch", back_populates="data_source")


class UserLevel(VolunteerBase):
    """User Levels: National, Regional, Local"""
    __tablename__ = "user_levels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    can_view_all_regions: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    users: Mapped[List["VUser"]] = relationship("VUser", back_populates="level")


class UserRole(VolunteerBase):
    """User Roles: View Only, Maker, Checker"""
    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    can_upload: Mapped[bool] = mapped_column(Boolean, default=False)
    can_validate: Mapped[bool] = mapped_column(Boolean, default=False)
    can_approve: Mapped[bool] = mapped_column(Boolean, default=False)
    can_reject: Mapped[bool] = mapped_column(Boolean, default=False)
    can_print: Mapped[bool] = mapped_column(Boolean, default=False)
    can_dispatch: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view_dashboard: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view_all_regions: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    users: Mapped[List["VUser"]] = relationship("VUser", back_populates="role")


class VUser(VolunteerBase):
    """Volunteer System Users"""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20))
    role_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("user_roles.id"))
    level_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("user_levels.id"))
    region_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("regions.id"))
    local_council_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("local_councils.id"))
    data_source_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("data_sources.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    role: Mapped[Optional["UserRole"]] = relationship("UserRole", back_populates="users")
    level: Mapped[Optional["UserLevel"]] = relationship("UserLevel", back_populates="users")


class Event(VolunteerBase):
    """Events (9 Events)"""
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[Optional[str]] = mapped_column(String(200))
    event_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    total_required_volunteers: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    volunteers: Mapped[List["Volunteer"]] = relationship("Volunteer", back_populates="event")
    position_quotas: Mapped[List["EventPositionQuota"]] = relationship("EventPositionQuota", back_populates="event")


class AccessLevel(VolunteerBase):
    """Access Levels (5 Levels): Stage, Pandal, Holding Area, Outside Area, Health Area"""
    __tablename__ = "access_levels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    band_color: Mapped[Optional[str]] = mapped_column(String(20))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    duty_types: Mapped[List["DutyType"]] = relationship("DutyType", back_populates="access_level")
    volunteers: Mapped[List["Volunteer"]] = relationship("Volunteer", back_populates="access_level")
    position_quotas: Mapped[List["EventPositionQuota"]] = relationship("EventPositionQuota", back_populates="access_level")


class DutyType(VolunteerBase):
    """Duty Types (17 types mapped to Access Levels)"""
    __tablename__ = "duty_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    access_level_id: Mapped[int] = mapped_column(Integer, ForeignKey("access_levels.id"))
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    access_level: Mapped["AccessLevel"] = relationship("AccessLevel", back_populates="duty_types")
    volunteers: Mapped[List["Volunteer"]] = relationship("Volunteer", back_populates="duty_type")
    position_quotas: Mapped[List["EventPositionQuota"]] = relationship("EventPositionQuota", back_populates="duty_type")


class EventPositionQuota(VolunteerBase):
    """Fixed positions per Event/Access Level/Duty Type"""
    __tablename__ = "event_position_quotas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id"))
    access_level_id: Mapped[int] = mapped_column(Integer, ForeignKey("access_levels.id"))
    duty_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("duty_types.id"))
    required_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    filled_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('event_id', 'access_level_id', 'duty_type_id', name='uq_event_access_duty'),
    )

    # Relationships
    event: Mapped["Event"] = relationship("Event", back_populates="position_quotas")
    access_level: Mapped["AccessLevel"] = relationship("AccessLevel", back_populates="position_quotas")
    duty_type: Mapped["DutyType"] = relationship("DutyType", back_populates="position_quotas")


# ============================================
# UPLOAD & VOLUNTEER MODELS
# ============================================

class UploadBatch(VolunteerBase):
    """Excel file uploads tracking"""
    __tablename__ = "upload_batches"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    region_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("regions.id"))
    data_source_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("data_sources.id"))
    source_entity_id: Mapped[Optional[str]] = mapped_column(String(50))
    source_entity_name: Mapped[Optional[str]] = mapped_column(String(200))
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("users.id"))
    uploaded_by_name: Mapped[Optional[str]] = mapped_column(String(200))
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    valid_records: Mapped[int] = mapped_column(Integer, default=0)
    rejected_records: Mapped[int] = mapped_column(Integer, default=0)
    discrepant_records: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default='processing')
    import_datetime: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    submitted_by: Mapped[Optional[str]] = mapped_column(String(50))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    approved_by: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    region: Mapped[Optional["VRegion"]] = relationship("VRegion", back_populates="upload_batches")
    data_source: Mapped[Optional["DataSource"]] = relationship("DataSource", back_populates="upload_batches")
    volunteers: Mapped[List["Volunteer"]] = relationship("Volunteer", back_populates="upload_batch")


class Volunteer(VolunteerBase):
    """Main volunteer records"""
    __tablename__ = "volunteers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    volunteer_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    cnic: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    event_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("events.id"))
    access_level_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("access_levels.id"))
    duty_type_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("duty_types.id"))
    region_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("regions.id"))

    # Source tracking
    data_source_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("data_sources.id"))
    source_entity_id: Mapped[Optional[str]] = mapped_column(String(50))
    source_entity_name: Mapped[Optional[str]] = mapped_column(String(200))
    upload_batch_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("upload_batches.id"))
    row_number: Mapped[Optional[int]] = mapped_column(Integer)

    # Validation status
    status: Mapped[str] = mapped_column(String(30), default='pending', index=True)
    cnic_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    discrepancy_reason: Mapped[Optional[str]] = mapped_column(Text)
    conflicting_volunteer_ids: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))

    # Decision tracking
    decision_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime)
    decision_by: Mapped[Optional[str]] = mapped_column(String(50))
    decision_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Workflow timestamps
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    submitted_by: Mapped[Optional[str]] = mapped_column(String(50))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    approved_by: Mapped[Optional[str]] = mapped_column(String(50))

    # Printing & Dispatch
    print_status: Mapped[str] = mapped_column(String(20), default='not_printed', index=True)
    print_batch_id: Mapped[Optional[str]] = mapped_column(String(50))
    printed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    printed_by: Mapped[Optional[str]] = mapped_column(String(50))

    # Kit tracking
    kit_status: Mapped[str] = mapped_column(String(20), default='not_prepared')
    badge_printed: Mapped[bool] = mapped_column(Boolean, default=False)
    wristband_prepared: Mapped[bool] = mapped_column(Boolean, default=False)
    lanyard_prepared: Mapped[bool] = mapped_column(Boolean, default=False)
    band_color: Mapped[Optional[str]] = mapped_column(String(20))

    # Dispatch
    dispatch_package_id: Mapped[Optional[str]] = mapped_column(String(50))
    dispatched_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    dispatched_by: Mapped[Optional[str]] = mapped_column(String(50))

    # Receipt tracking
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    received_by: Mapped[Optional[str]] = mapped_column(String(200))
    signature_collected: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('cnic', 'event_id', 'duty_type_id', name='uq_cnic_event_duty'),
        Index('idx_volunteers_cnic', 'cnic'),
        Index('idx_volunteers_status', 'status'),
        Index('idx_volunteers_print_status', 'print_status'),
    )

    # Relationships
    event: Mapped[Optional["Event"]] = relationship("Event", back_populates="volunteers")
    access_level: Mapped[Optional["AccessLevel"]] = relationship("AccessLevel", back_populates="volunteers")
    duty_type: Mapped[Optional["DutyType"]] = relationship("DutyType", back_populates="volunteers")
    region: Mapped[Optional["VRegion"]] = relationship("VRegion", back_populates="volunteers")
    data_source: Mapped[Optional["DataSource"]] = relationship("DataSource", back_populates="volunteers")
    upload_batch: Mapped[Optional["UploadBatch"]] = relationship("UploadBatch", back_populates="volunteers")
    validation_logs: Mapped[List["VolunteerValidationLog"]] = relationship("VolunteerValidationLog", back_populates="volunteer")


class VolunteerValidationLog(VolunteerBase):
    """Audit trail for validation decisions"""
    __tablename__ = "volunteer_validation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    volunteer_id: Mapped[int] = mapped_column(Integer, ForeignKey("volunteers.id"))
    validation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    result: Mapped[str] = mapped_column(String(50), nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(50))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    details: Mapped[Optional[dict]] = mapped_column(JSONB)
    validated_by: Mapped[Optional[str]] = mapped_column(String(50))
    validated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    volunteer: Mapped["Volunteer"] = relationship("Volunteer", back_populates="validation_logs")


# ============================================
# PRINTING & DISPATCH MODELS
# ============================================

class PrintBatch(VolunteerBase):
    """Print batch tracking"""
    __tablename__ = "print_batches"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    region_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("regions.id"))
    access_level_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("access_levels.id"))
    band_color: Mapped[Optional[str]] = mapped_column(String(20))
    total_badges: Mapped[int] = mapped_column(Integer, default=0)
    printed_by: Mapped[Optional[str]] = mapped_column(String(50))
    printed_by_name: Mapped[Optional[str]] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    labels_printed: Mapped[bool] = mapped_column(Boolean, default=False)
    labels_printed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    cover_sheet_printed: Mapped[bool] = mapped_column(Boolean, default=False)
    cover_sheet_printed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    covering_sheets: Mapped[List["CoveringSheet"]] = relationship("CoveringSheet", back_populates="print_batch")


class CoveringSheet(VolunteerBase):
    """Covering sheets for dispatch"""
    __tablename__ = "covering_sheets"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    print_batch_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("print_batches.id"))
    region_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("regions.id"))
    event_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("events.id"))
    access_level_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("access_levels.id"))
    access_level_name: Mapped[Optional[str]] = mapped_column(String(100))
    band_color: Mapped[Optional[str]] = mapped_column(String(20))
    total_entries: Mapped[int] = mapped_column(Integer, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    generated_by: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    print_batch: Mapped[Optional["PrintBatch"]] = relationship("PrintBatch", back_populates="covering_sheets")
    entries: Mapped[List["CoveringSheetEntry"]] = relationship("CoveringSheetEntry", back_populates="covering_sheet")


class CoveringSheetEntry(VolunteerBase):
    """Individual entries in covering sheet"""
    __tablename__ = "covering_sheet_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    covering_sheet_id: Mapped[str] = mapped_column(String(50), ForeignKey("covering_sheets.id"))
    volunteer_id: Mapped[int] = mapped_column(Integer, ForeignKey("volunteers.id"))
    cnic: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    duty_type: Mapped[Optional[str]] = mapped_column(String(100))
    receiving_signature: Mapped[Optional[str]] = mapped_column(Text)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    covering_sheet: Mapped["CoveringSheet"] = relationship("CoveringSheet", back_populates="entries")


class DispatchPackage(VolunteerBase):
    """Dispatch package tracking"""
    __tablename__ = "dispatch_packages"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    region_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("regions.id"))
    destination_source_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("data_sources.id"))
    destination_entity_id: Mapped[Optional[str]] = mapped_column(String(50))
    destination_entity_name: Mapped[Optional[str]] = mapped_column(String(200))
    total_badges: Mapped[int] = mapped_column(Integer, default=0)
    total_wristbands: Mapped[int] = mapped_column(Integer, default=0)
    total_lanyards: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default='preparing')
    prepared_by: Mapped[Optional[str]] = mapped_column(String(50))
    prepared_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    dispatched_by: Mapped[Optional[str]] = mapped_column(String(50))
    dispatched_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    received_by: Mapped[Optional[str]] = mapped_column(String(200))
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DispatchPackagePrintBatch(VolunteerBase):
    """Junction table for dispatch packages and print batches"""
    __tablename__ = "dispatch_package_print_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dispatch_package_id: Mapped[str] = mapped_column(String(50), ForeignKey("dispatch_packages.id"))
    print_batch_id: Mapped[str] = mapped_column(String(50), ForeignKey("print_batches.id"))
    covering_sheet_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("covering_sheets.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('dispatch_package_id', 'print_batch_id', name='uq_dispatch_print'),
    )
