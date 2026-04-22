# ============================================
# VOLUNTEER MANAGEMENT SYSTEM - Pydantic Schemas
# Pakistan Deedar 2026
# ============================================

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ============================================
# REGION SCHEMAS
# ============================================

class RegionBase(BaseModel):
    code: str
    name: str
    is_active: bool = True
    has_backup_printer: bool = False


class RegionCreate(RegionBase):
    pass


class RegionResponse(RegionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================
# EVENT SCHEMAS
# ============================================

class EventBase(BaseModel):
    event_number: int
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    event_date: Optional[datetime] = None
    is_active: bool = True
    total_required_volunteers: int = 0


class EventCreate(EventBase):
    pass


class EventResponse(EventBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================
# ACCESS LEVEL SCHEMAS
# ============================================

class AccessLevelBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    band_color: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True


class AccessLevelResponse(AccessLevelBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# DUTY TYPE SCHEMAS
# ============================================

class DutyTypeBase(BaseModel):
    code: str
    name: str
    access_level_id: int
    description: Optional[str] = None
    is_active: bool = True


class DutyTypeResponse(DutyTypeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DutyTypeWithAccessLevel(DutyTypeResponse):
    access_level_name: Optional[str] = None
    band_color: Optional[str] = None


# ============================================
# DATA SOURCE SCHEMAS
# ============================================

class DataSourceBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool = True


class DataSourceResponse(DataSourceBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# USER ROLE & LEVEL SCHEMAS
# ============================================

class UserRoleResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    can_upload: bool
    can_validate: bool
    can_approve: bool
    can_reject: bool
    can_print: bool
    can_dispatch: bool
    can_view_dashboard: bool
    can_view_all_regions: bool

    class Config:
        from_attributes = True


class UserLevelResponse(BaseModel):
    id: int
    code: str
    name: str
    can_view_all_regions: bool

    class Config:
        from_attributes = True


# ============================================
# VOLUNTEER USER SCHEMAS
# ============================================

class VolunteerUserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    phone_number: Optional[str] = None
    role_id: int
    level_id: int
    region_id: Optional[int] = None
    local_council_id: Optional[str] = None
    data_source_id: Optional[int] = None


class VolunteerUserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone_number: Optional[str] = None
    role_id: Optional[int] = None
    level_id: Optional[int] = None
    region_id: Optional[int] = None
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# UPLOAD BATCH SCHEMAS
# ============================================

class UploadBatchCreate(BaseModel):
    file_name: str
    region_id: int
    data_source_id: int
    source_entity_id: Optional[str] = None
    source_entity_name: Optional[str] = None


class UploadBatchResponse(BaseModel):
    id: str
    file_name: str
    region_id: Optional[int] = None
    data_source_id: Optional[int] = None
    source_entity_id: Optional[str] = None
    source_entity_name: Optional[str] = None
    uploaded_by: Optional[str] = None
    uploaded_by_name: Optional[str] = None
    total_records: int
    valid_records: int
    rejected_records: int
    discrepant_records: int
    status: str
    import_datetime: datetime
    validated_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# VOLUNTEER SCHEMAS
# ============================================

class VolunteerUploadRow(BaseModel):
    """Single row from Excel upload"""
    cnic: str
    name: str
    event_number: int
    access_level: int
    duty_type: str
    row_number: Optional[int] = None


class VolunteerBulkUpload(BaseModel):
    """Bulk upload request"""
    file_name: str
    region_id: int
    data_source_id: int
    source_entity_id: Optional[str] = None
    source_entity_name: Optional[str] = None
    volunteers: List[VolunteerUploadRow]


class VolunteerCreate(BaseModel):
    cnic: str
    name: str
    event_id: int
    access_level_id: int
    duty_type_id: int
    region_id: int
    data_source_id: Optional[int] = None
    source_entity_id: Optional[str] = None
    source_entity_name: Optional[str] = None


class VolunteerResponse(BaseModel):
    id: int
    volunteer_id: str
    cnic: str
    name: str
    event_id: Optional[int] = None
    access_level_id: Optional[int] = None
    duty_type_id: Optional[int] = None
    region_id: Optional[int] = None
    data_source_id: Optional[int] = None
    source_entity_id: Optional[str] = None
    source_entity_name: Optional[str] = None
    upload_batch_id: Optional[str] = None
    row_number: Optional[int] = None
    status: str
    cnic_verified: bool
    discrepancy_reason: Optional[str] = None
    decision_datetime: Optional[datetime] = None
    print_status: str
    kit_status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VolunteerWithDetails(VolunteerResponse):
    """Volunteer with related entity names"""
    event_name: Optional[str] = None
    event_number: Optional[int] = None
    access_level_name: Optional[str] = None
    duty_type_name: Optional[str] = None
    region_name: Optional[str] = None
    band_color: Optional[str] = None


class VolunteerValidationResult(BaseModel):
    """Result of CNIC validation"""
    cnic: str
    is_valid: bool
    is_registered: bool
    name: Optional[str] = None
    message: Optional[str] = None


class VolunteerBulkValidationResponse(BaseModel):
    """Response for bulk validation"""
    batch_id: str
    total_records: int
    valid_records: int
    rejected_records: int
    discrepant_records: int
    results: List[VolunteerResponse]


# ============================================
# DECISION SCHEMAS
# ============================================

class VolunteerDecision(BaseModel):
    """Decision on a volunteer record"""
    volunteer_id: int
    decision: str  # 'approve', 'reject'
    notes: Optional[str] = None


class BulkDecision(BaseModel):
    """Bulk decision on multiple volunteers"""
    volunteer_ids: List[int]
    decision: str  # 'approve', 'reject'
    notes: Optional[str] = None


class SubmitForApproval(BaseModel):
    """Submit batch for checker approval"""
    batch_id: str


class ApproveForPrinting(BaseModel):
    """Approve volunteers for printing"""
    volunteer_ids: List[int]


# ============================================
# PRINT & DISPATCH SCHEMAS
# ============================================

class PrintBatchCreate(BaseModel):
    region_id: int
    access_level_id: int
    volunteer_ids: List[int]


class PrintBatchResponse(BaseModel):
    id: str
    region_id: Optional[int] = None
    access_level_id: Optional[int] = None
    band_color: Optional[str] = None
    total_badges: int
    printed_by: Optional[str] = None
    printed_by_name: Optional[str] = None
    status: str
    labels_printed: bool
    cover_sheet_printed: bool
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CoveringSheetEntry(BaseModel):
    cnic: str
    name: str
    duty_type: Optional[str] = None
    receiving_signature: Optional[str] = None


class CoveringSheetResponse(BaseModel):
    id: str
    print_batch_id: Optional[str] = None
    event_id: Optional[int] = None
    access_level_id: Optional[int] = None
    access_level_name: Optional[str] = None
    band_color: Optional[str] = None
    total_entries: int
    entries: List[CoveringSheetEntry] = []
    generated_at: datetime

    class Config:
        from_attributes = True


class DispatchPackageCreate(BaseModel):
    region_id: int
    destination_source_id: int
    destination_entity_id: Optional[str] = None
    destination_entity_name: Optional[str] = None
    print_batch_ids: List[str]
    notes: Optional[str] = None


class DispatchPackageResponse(BaseModel):
    id: str
    region_id: Optional[int] = None
    destination_source_id: Optional[int] = None
    destination_entity_id: Optional[str] = None
    destination_entity_name: Optional[str] = None
    total_badges: int
    total_wristbands: int
    total_lanyards: int
    status: str
    prepared_at: Optional[datetime] = None
    dispatched_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# DASHBOARD SCHEMAS
# ============================================

class RegionStats(BaseModel):
    region_id: int
    region_name: str
    total_received: int
    total_valid: int
    total_rejected: int
    total_discrepant: int
    total_approved: int
    total_printed: int
    total_dispatched: int


class EventStats(BaseModel):
    event_id: int
    event_number: int
    event_name: str
    required: int
    received: int
    valid: int
    printed: int
    received_percentage: float
    printed_percentage: float


class AccessLevelStats(BaseModel):
    access_level_id: int
    access_level_name: str
    band_color: str
    required: int
    filled: int
    remaining: int


class DashboardResponse(BaseModel):
    total_required: int
    total_received: int
    total_validated: int
    total_approved: int
    total_printed: int
    total_dispatched: int
    received_percentage: float
    printed_percentage: float
    by_region: List[RegionStats] = []
    by_event: List[EventStats] = []
    by_access_level: List[AccessLevelStats] = []


# ============================================
# POSITION QUOTA SCHEMAS
# ============================================

class EventPositionQuotaCreate(BaseModel):
    event_id: int
    access_level_id: int
    duty_type_id: int
    required_count: int


class EventPositionQuotaResponse(BaseModel):
    id: int
    event_id: int
    access_level_id: int
    duty_type_id: int
    required_count: int
    filled_count: int
    remaining_count: int
    event_name: Optional[str] = None
    access_level_name: Optional[str] = None
    duty_type_name: Optional[str] = None

    class Config:
        from_attributes = True


class QuotaCheckResult(BaseModel):
    """Result of quota check before upload"""
    can_proceed: bool
    errors: List[str] = []
    quota_status: List[EventPositionQuotaResponse] = []


# ============================================
# FILTER & PAGINATION SCHEMAS
# ============================================

class VolunteerFilters(BaseModel):
    region_id: Optional[int] = None
    event_id: Optional[int] = None
    access_level_id: Optional[int] = None
    duty_type_id: Optional[int] = None
    status: Optional[str] = None
    print_status: Optional[str] = None
    batch_id: Optional[str] = None
    cnic: Optional[str] = None
    search: Optional[str] = None


class PaginatedVolunteersResponse(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
    data: List[VolunteerWithDetails]
