# ============================================
# VOLUNTEER MANAGEMENT SYSTEM - SIMPLIFIED SCHEMAS
# Pakistan Deedar 2026
# Matches frontend constants - no master data APIs needed
# ============================================

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


# ============================================
# ENUMS (Match Frontend Constants)
# ============================================

class Region(str, Enum):
    GILGIT = "gilgit"
    HUNZA = "hunza"
    GUPIS = "gupis"
    ISHKOMAN = "ishkoman"
    LOWER_CHITRAL = "lower_chitral"
    UPPER_CHITRAL = "upper_chitral"


class DataSource(str, Enum):
    LOCAL_COUNCIL = "local_council"
    REGIONAL_EVENT_MANAGER = "regional_event_manager"
    ITREB = "itreb"
    HEALTH_BOARD = "health_board"


class VolunteerStatus(str, Enum):
    PENDING = "pending"
    VALID = "valid"
    REJECTED = "rejected"
    DISCREPANT = "discrepant"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    PRINTED = "printed"
    DISPATCHED = "dispatched"


class PrintStatus(str, Enum):
    NOT_PRINTED = "not_printed"
    PRINTING = "printing"
    PRINTED = "printed"
    DISPATCHED = "dispatched"


class ValidationError(str, Enum):
    CNIC_NOT_FOUND = "cnic_not_found"
    DUPLICATE_SAME_DUTY = "duplicate_same_duty"
    DISCREPANT_DIFFERENT_DUTIES = "discrepant_different_duties"
    DISCREPANT_MULTIPLE_TEAMS = "discrepant_multiple_teams"
    DISCREPANT_MULTIPLE_EVENTS = "discrepant_multiple_events"


# ============================================
# ACCESS LEVELS & DUTY TYPES (Hardcoded - Match Frontend)
# ============================================

# Access Level: 1=Stage, 2=Pandal, 3=Outside Holding Area, 4=Outside Area, 5=Health Area
ACCESS_LEVEL_NAMES = {
    1: "Stage",
    2: "Pandal",
    3: "Outside Holding Area",
    4: "Outside Area",
    5: "Health Area"
}

ACCESS_LEVEL_BAND_COLORS = {
    1: "#FFD700",  # Gold - Stage
    2: "#FF6B35",  # Orange - Pandal
    3: "#4ECDC4",  # Teal - Outside Holding
    4: "#45B7D1",  # Blue - Outside
    5: "#96CEB4"   # Green - Health
}

# Duty Type -> Access Level mapping (from frontend)
DUTY_TYPE_ACCESS_LEVELS = {
    # Stage (1)
    "Reciter": 1,
    "Volunteer": 1,
    # Health Area (5)
    "Doctor": 5,
    "Nurse": 5,
    # Pandal (2)
    "Red Carpet": 2,
    "Medical Area": 2,
    "Amaldar Area": 2,
    "Pani Services": 2,
    "Washroom": 2,
    "Security": 2,  # Note: Security exists in multiple levels
    # Outside Holding Area (3)
    "Access Control": 3,
    "Pani": 3,  # Also in Outside Area
    # Outside Area (4)
    "Transport": 4,
}


def get_access_level_for_duty(duty_type: str) -> int:
    """Get access level from duty type name"""
    return DUTY_TYPE_ACCESS_LEVELS.get(duty_type, 4)  # Default to Outside Area


def get_band_color(access_level: int) -> str:
    """Get band color for access level"""
    return ACCESS_LEVEL_BAND_COLORS.get(access_level, "#808080")


# ============================================
# VOLUNTEER UPLOAD - FROM EXCEL
# ============================================

class VolunteerUploadRow(BaseModel):
    """Single row from Excel file"""
    cnic: str
    name: str
    event_number: int = Field(..., alias="eventNumber", ge=1, le=9)
    duty_type: str = Field(..., alias="dutyType")
    access_level: int = Field(..., alias="accessLevel", ge=1, le=5)
    row_number: int = Field(..., alias="rowNumber")
    
    class Config:
        populate_by_name = True


class VolunteerBulkUpload(BaseModel):
    """Bulk upload request from frontend"""
    file_name: str = Field(..., alias="fileName")
    region: Region
    source: DataSource
    source_entity_id: str = Field(..., alias="sourceEntityId")
    source_entity_name: str = Field("", alias="sourceEntityName")
    volunteers: List[VolunteerUploadRow]
    
    class Config:
        populate_by_name = True


# ============================================
# VALIDATION RESULTS
# ============================================

class ValidationResult(BaseModel):
    """Validation result for a single volunteer"""
    is_valid: bool = Field(..., alias="isValid")
    error_type: Optional[ValidationError] = Field(None, alias="errorType")
    error_message: Optional[str] = Field(None, alias="errorMessage")
    conflicting_records: Optional[List[str]] = Field(None, alias="conflictingRecords")
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        populate_by_name = True


class CNICValidationResponse(BaseModel):
    """Response from CNIC validation against census DB"""
    is_valid: bool = Field(..., alias="isValid")
    is_registered: bool = Field(..., alias="isRegistered")
    name: Optional[str] = None
    message: Optional[str] = None
    
    class Config:
        populate_by_name = True


# ============================================
# VOLUNTEER RESPONSE
# ============================================

class VolunteerResponse(BaseModel):
    """Volunteer record response"""
    id: str
    volunteer_id: str = Field(..., alias="volunteerId")
    cnic: str
    name: str
    event_id: str = Field(..., alias="eventId")
    event_number: int = Field(..., alias="eventNumber")
    duty_type_id: str = Field(..., alias="dutyTypeId")
    duty_type_name: str = Field(..., alias="dutyTypeName")
    access_level: int = Field(..., alias="accessLevel")
    access_level_name: str = Field(..., alias="accessLevelName")
    region: Region
    source: DataSource
    source_entity_id: str = Field(..., alias="sourceEntityId")
    source_entity_name: str = Field(..., alias="sourceEntityName")
    upload_batch_id: str = Field(..., alias="uploadBatchId")
    status: VolunteerStatus
    validation_errors: List[ValidationResult] = Field([], alias="validationErrors")
    print_status: PrintStatus = Field(..., alias="printStatus")
    print_batch_id: Optional[str] = Field(None, alias="printBatchId")
    package_id: Optional[str] = Field(None, alias="packageId")
    cnic_verified: bool = Field(..., alias="cnicVerified")
    submitted_at: Optional[datetime] = Field(None, alias="submittedAt")
    submitted_by: Optional[str] = Field(None, alias="submittedBy")
    approved_at: Optional[datetime] = Field(None, alias="approvedAt")
    approved_by: Optional[str] = Field(None, alias="approvedBy")
    printed_at: Optional[datetime] = Field(None, alias="printedAt")
    printed_by: Optional[str] = Field(None, alias="printedBy")
    dispatched_at: Optional[datetime] = Field(None, alias="dispatchedAt")
    dispatched_by: Optional[str] = Field(None, alias="dispatchedBy")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class VolunteerWithError(VolunteerResponse):
    """Volunteer with validation errors"""
    errors: List[ValidationResult] = []


# ============================================
# UPLOAD BATCH
# ============================================

class UploadBatchResponse(BaseModel):
    """Upload batch response"""
    id: str
    file_name: str = Field(..., alias="fileName")
    region: Region
    uploaded_by: str = Field(..., alias="uploadedBy")
    uploaded_by_name: str = Field(..., alias="uploadedByName")
    total_records: int = Field(..., alias="totalRecords")
    valid_records: int = Field(..., alias="validRecords")
    rejected_records: int = Field(..., alias="rejectedRecords")
    discrepant_records: int = Field(..., alias="discrepantRecords")
    status: str  # 'processing' | 'completed' | 'failed'
    source: DataSource
    source_entity_id: str = Field(..., alias="sourceEntityId")
    source_entity_name: str = Field(..., alias="sourceEntityName")
    created_at: datetime = Field(..., alias="createdAt")
    processed_at: Optional[datetime] = Field(None, alias="processedAt")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class BulkValidationResult(BaseModel):
    """Result of bulk upload validation"""
    batch_id: str = Field(..., alias="batchId")
    total_records: int = Field(..., alias="totalRecords")
    valid_records: List[VolunteerResponse] = Field(..., alias="validRecords")
    rejected_records: List[VolunteerWithError] = Field(..., alias="rejectedRecords")
    discrepant_records: List[VolunteerWithError] = Field(..., alias="discrepantRecords")
    
    class Config:
        populate_by_name = True


# ============================================
# VOLUNTEER LIST / FILTERS
# ============================================

class VolunteerFilters(BaseModel):
    """Filters for volunteer list"""
    region: Optional[Region] = None
    status: Optional[VolunteerStatus] = None
    event_id: Optional[str] = Field(None, alias="eventId")
    access_level: Optional[int] = Field(None, alias="accessLevel")
    cnic: Optional[str] = None
    name: Optional[str] = None
    batch_id: Optional[str] = Field(None, alias="batchId")
    page: int = 1
    page_size: int = Field(10, alias="pageSize")
    
    class Config:
        populate_by_name = True


class Pagination(BaseModel):
    """Pagination info"""
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    total_pages: int = Field(..., alias="totalPages")
    has_next: bool = Field(..., alias="hasNext")
    has_previous: bool = Field(..., alias="hasPrevious")
    
    class Config:
        populate_by_name = True


class VolunteersResponse(BaseModel):
    """Paginated volunteers response"""
    data: List[VolunteerResponse]
    pagination: Pagination
    
    class Config:
        populate_by_name = True


# ============================================
# APPROVAL / DECISION
# ============================================

class VolunteerApprovalFormData(BaseModel):
    """Approve/reject volunteers"""
    volunteer_ids: List[str] = Field(..., alias="volunteerIds")
    action: str  # 'approve' | 'reject'
    reason: Optional[str] = None
    
    class Config:
        populate_by_name = True


# ============================================
# DASHBOARD
# ============================================

class RegionStats(BaseModel):
    """Stats per region"""
    region: Region
    total: int
    valid: int
    rejected: int
    discrepant: int
    approved: int
    printed: int
    dispatched: int


class EventStats(BaseModel):
    """Stats per event"""
    event_number: int = Field(..., alias="eventNumber")
    event_name: str = Field(..., alias="eventName")
    required: int
    received: int
    valid: int
    approved: int
    printed: int
    percentage: float
    
    class Config:
        populate_by_name = True


class AccessLevelStats(BaseModel):
    """Stats per access level"""
    access_level: int = Field(..., alias="accessLevel")
    access_level_name: str = Field(..., alias="accessLevelName")
    band_color: str = Field(..., alias="bandColor")
    required: int
    received: int
    valid: int
    printed: int
    
    class Config:
        populate_by_name = True


class DashboardStats(BaseModel):
    """Dashboard statistics"""
    total_required: int = Field(..., alias="totalRequired")
    total_received: int = Field(..., alias="totalReceived")
    total_valid: int = Field(..., alias="totalValid")
    total_rejected: int = Field(..., alias="totalRejected")
    total_discrepant: int = Field(..., alias="totalDiscrepant")
    total_approved: int = Field(..., alias="totalApproved")
    total_printed: int = Field(..., alias="totalPrinted")
    total_dispatched: int = Field(..., alias="totalDispatched")
    received_percentage: float = Field(..., alias="receivedPercentage")
    printed_percentage: float = Field(..., alias="printedPercentage")
    by_region: List[RegionStats] = Field(..., alias="byRegion")
    by_event: List[EventStats] = Field(..., alias="byEvent")
    by_access_level: List[AccessLevelStats] = Field(..., alias="byAccessLevel")
    
    class Config:
        populate_by_name = True


class DashboardFilters(BaseModel):
    """Dashboard filters"""
    region: Optional[Region] = None
    event_number: Optional[int] = Field(None, alias="eventNumber")
    
    class Config:
        populate_by_name = True
