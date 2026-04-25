# Error Logging System Documentation

## Overview

A comprehensive error logging and tracking system for the Volunteer Management API that:
- Logs all errors to the `error_codes` database table
- Tracks errors with unique codes, severity levels, and HTTP status codes
- Provides request ID tracking for debugging
- Integrates with Python's standard logging module
- Supports structured logging with contextual data

## Components

### 1. `error_logging.py` - Core Logging Module

Main classes and functions:

#### `ErrorCode` Enum
Pre-defined error codes for your application:
```python
ErrorCode.CNIC_NOT_FOUND        # CNIC validation failed
ErrorCode.DUPLICATE_RECORD      # Duplicate volunteer record
ErrorCode.VOLUNTEER_NOT_FOUND   # Volunteer ID not found
ErrorCode.DB_INSERT_FAILED      # Database insert failed
ErrorCode.VALIDATION_ERROR      # Validation failed
```

#### `ErrorSeverity` Enum
Four severity levels:
- `INFO` - Informational
- `WARNING` - Warning condition
- `ERROR` - Error condition
- `CRITICAL` - Critical error

#### `ErrorLogger` Class
Static methods for logging:

```python
# Basic usage
await ErrorLogger.log_error(
    db=db_session,
    code=ErrorCode.CNIC_NOT_FOUND,
    message="CNIC not found in enrollment database",
    status_code=400,
    severity=ErrorSeverity.WARNING,
    details={"cnic": "1234567890", "search_date": "2026-04-25"},
    request_id="req-12345"
)

# Or use convenience function
await log_and_raise_error(
    db=db_session,
    code=ErrorCode.VOLUNTEER_NOT_FOUND,
    message="Volunteer record not found",
    status_code=404,
    severity=ErrorSeverity.ERROR
)
```

### 2. `logging_config.py` - Configuration

Set up Python logging with:
- Console output (INFO level)
- File output (DEBUG level)
- Error file (ERROR+ level)
- Rotating file handlers (10MB max per file)

**Usage in main.py:**
```python
from logging_config import setup_logging

# At application startup
setup_logging()
```

### 3. `api_error_logging_examples.py` - Integration Examples

Complete examples of integrating logging into API endpoints.

## Database Schema

The `error_codes` table stores all logged errors:

```sql
CREATE TABLE error_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,           -- Error code (e.g., CNIC_NOT_FOUND)
    status INTEGER,                             -- HTTP status code (e.g., 400, 500)
    severity VARCHAR(20) NOT NULL,              -- Severity level
    message VARCHAR(255) NOT NULL,              -- Human-readable message
    details TEXT,                               -- Additional JSON details
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Integration Examples

### Example 1: Volunteer Record Validation

```python
from error_logging import ErrorLogger, ErrorCode, ErrorSeverity

async def validate_volunteer_record(record_data, db):
    request_id = str(uuid.uuid4())
    
    # Check if CNIC already exists
    existing = await db.execute(
        text("SELECT id FROM volunteer_record WHERE cnic = :cnic"),
        {"cnic": record_data.cnic}
    )
    
    if existing.scalar():
        await ErrorLogger.log_error(
            db=db,
            code=ErrorCode.DUPLICATE_RECORD,
            message=f"Duplicate CNIC: {record_data.cnic}",
            status_code=400,
            severity=ErrorSeverity.WARNING,
            details={
                "cnic": record_data.cnic,
                "event_id": record_data.event_id,
                "request_id": request_id
            },
            request_id=request_id
        )
        raise HTTPException(status_code=400, detail="Duplicate CNIC")
```

### Example 2: Database Operation with Error Handling

```python
async def update_volunteer_status(volunteer_id, new_status, db):
    request_id = str(uuid.uuid4())
    
    try:
        result = await db.execute(
            text("UPDATE volunteer_record SET status = :status WHERE id = :id"),
            {"status": new_status, "id": volunteer_id}
        )
        await db.commit()
        
        logger.info(f"[{request_id}] Updated volunteer {volunteer_id} status")
        
    except Exception as e:
        await ErrorLogger.log_error(
            db=db,
            code=ErrorCode.DB_INSERT_FAILED,
            message=f"Failed to update volunteer {volunteer_id}",
            status_code=500,
            severity=ErrorSeverity.CRITICAL,
            details={
                "volunteer_id": volunteer_id,
                "new_status": new_status,
                "error": str(e),
                "request_id": request_id
            },
            request_id=request_id
        )
        raise HTTPException(status_code=500, detail=f"Update failed. Request: {request_id}")
```

### Example 3: Maker Decisions with Logging

```python
@volunteer_router.post("/volunteers/maker-decisions")
async def update_maker_decisions(
    decisions: List[MakerDecisionUpdate],
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    request_id = str(uuid.uuid4())
    updated_ids = []
    
    try:
        for decision in decisions:
            # Check if volunteer exists
            volunteer = await volunteer_db.execute(
                text("SELECT id FROM volunteer_record WHERE id = :id"),
                {"id": decision.id}
            )
            
            if not volunteer.scalar():
                await ErrorLogger.log_error(
                    db=volunteer_db,
                    code=ErrorCode.VOLUNTEER_NOT_FOUND,
                    message=f"Volunteer {decision.id} not found",
                    status_code=404,
                    severity=ErrorSeverity.WARNING,
                    details={"volunteer_id": decision.id, "request_id": request_id},
                    request_id=request_id
                )
                continue
            
            # Update record
            await volunteer_db.execute(
                text("UPDATE volunteer_record SET decision_status = :status WHERE id = :id"),
                {"status": decision.decisionStatus, "id": decision.id}
            )
            updated_ids.append(decision.id)
        
        await volunteer_db.commit()
        
        logger.info(
            f"[{request_id}] Processed {len(updated_ids)} decisions",
            extra={"updated_count": len(updated_ids), "request_id": request_id}
        )
        
        return {
            "success": True,
            "updated": len(updated_ids),
            "updatedIds": updated_ids,
            "requestId": request_id
        }
        
    except Exception as e:
        await volunteer_db.rollback()
        
        await ErrorLogger.log_error(
            db=volunteer_db,
            code=ErrorCode.DB_QUERY_FAILED,
            message=f"Batch decision processing failed",
            status_code=500,
            severity=ErrorSeverity.CRITICAL,
            details={"error": str(e), "request_id": request_id},
            request_id=request_id
        )
        
        raise HTTPException(status_code=500, detail=f"Failed. Request: {request_id}")
```

## Setup Instructions

### 1. Add to `main.py`

```python
from logging_config import setup_logging

# At application startup
app = FastAPI()

# Initialize logging
setup_logging()

logger = logging.getLogger(__name__)
logger.info("Application started")
```

### 2. Import in API Endpoints

```python
from error_logging import ErrorLogger, ErrorCode, ErrorSeverity, log_and_raise_error
import uuid
import logging

logger = logging.getLogger(__name__)
```

### 3. Use in Endpoints

```python
# Generate request ID
request_id = str(uuid.uuid4())

# Log error if something fails
await ErrorLogger.log_error(
    db=db,
    code=ErrorCode.VALIDATION_ERROR,
    message="Invalid input",
    request_id=request_id
)
```

## Querying Logged Errors

### Get all errors
```sql
SELECT * FROM error_codes ORDER BY created_at DESC;
```

### Get errors by code
```sql
SELECT * FROM error_codes WHERE code = 'CNIC_NOT_FOUND' ORDER BY created_at DESC;
```

### Get errors by severity
```sql
SELECT * FROM error_codes WHERE severity = 'error' ORDER BY created_at DESC;
```

### Get recent errors
```sql
SELECT * FROM error_codes 
WHERE created_at >= NOW() - INTERVAL '1 day'
ORDER BY created_at DESC;
```

## Log File Structure

Logs are stored in the `logs/` directory:
- `volunteer_api_YYYYMMDD.log` - Daily application log (DEBUG+)
- `errors.log` - Error-only log (ERROR+)

Each log entry includes:
- Timestamp
- Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Logger name
- Function name and line number
- Message
- Extra context data

## Best Practices

1. **Always use request IDs**: Generate UUID for each request to track operations
2. **Choose appropriate severity**: Use WARNING for expected issues, ERROR for unexpected
3. **Include context**: Always include relevant IDs and data in the `details` dict
4. **Handle gracefully**: Log errors but handle them appropriately for the user
5. **Don't log sensitive data**: Avoid logging passwords, full credit cards, etc.
6. **Use consistent error codes**: Define codes upfront in ErrorCode enum

## Status Codes Reference

| Code | Meaning | When to Use |
|------|---------|------------|
| 400 | Bad Request | Validation errors, duplicate records |
| 401 | Unauthorized | Authentication failed |
| 403 | Forbidden | Authorization failed |
| 404 | Not Found | Resource not found |
| 500 | Server Error | Database errors, unexpected exceptions |
| 503 | Service Unavailable | Database connection failed |

## Future Enhancements

- Email alerts for CRITICAL errors
- Error statistics dashboard
- Automated error cleanup (archive old errors)
- Integration with monitoring tools (Sentry, New Relic)
- Slack notifications for specific error codes
