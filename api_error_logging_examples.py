# ============================================
# API ENDPOINT INTEGRATION EXAMPLES
# How to use error logging in your API endpoints
# ============================================

"""
EXAMPLE 1: Import and Use in Maker Decisions Endpoint
"""

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime
import uuid
import logging

from error_logging import (
    ErrorLogger, ErrorCode, ErrorSeverity, 
    log_and_raise_error
)
from volunteer_schemas_v2 import MakerDecisionUpdate

logger = logging.getLogger(__name__)


# ============================================
# UPDATED MAKER DECISIONS ENDPOINT WITH LOGGING
# ============================================

async def update_maker_decisions_with_logging(
    decisions: list[MakerDecisionUpdate],
    volunteer_db: AsyncSession = Depends(volunteer_db_session)
):
    """Update decision_status for volunteer records by maker with comprehensive logging"""
    now = datetime.utcnow()
    updated_ids = []
    request_id = str(uuid.uuid4())  # Unique request tracking ID
    
    try:
        for idx, decision in enumerate(decisions):
            try:
                # Fetch current record details
                fetch_sql = text("""
                    SELECT record_number, cnic, name, event_id, access_level_id, duty_type_id,
                           record_status, register, checker_id, import_id
                    FROM volunteer_record
                    WHERE id = :id
                """)
                
                result = await volunteer_db.execute(fetch_sql, {"id": decision.id})
                record = result.fetchone()
                
                if not record:
                    # Log volunteer not found error
                    await ErrorLogger.log_error(
                        db=volunteer_db,
                        code=ErrorCode.VOLUNTEER_NOT_FOUND,
                        message=f"Volunteer record ID {decision.id} not found",
                        status_code=404,
                        severity=ErrorSeverity.WARNING,
                        details={
                            "volunteer_id": decision.id,
                            "index": idx,
                            "request_id": request_id
                        },
                        request_id=request_id
                    )
                    continue

                # Validate decision status
                valid_statuses = ["Ok", "Rejected", "Discrepant-1", "Discrepant-2"]
                if decision.decisionStatus not in valid_statuses:
                    await ErrorLogger.log_error(
                        db=volunteer_db,
                        code=ErrorCode.VALIDATION_ERROR,
                        message=f"Invalid decision status: {decision.decisionStatus}",
                        status_code=400,
                        severity=ErrorSeverity.ERROR,
                        details={
                            "volunteer_id": decision.id,
                            "status_provided": decision.decisionStatus,
                            "valid_statuses": valid_statuses,
                            "request_id": request_id
                        },
                        request_id=request_id
                    )
                    continue

                # Update volunteer_record
                update_sql = text("""
                    UPDATE volunteer_record
                    SET decision_status = :decision_status,
                        updated_at = :updated_at
                    WHERE id = :id
                """)
                
                params = {
                    "id": decision.id,
                    "decision_status": decision.decisionStatus,
                    "updated_at": now
                }
                
                result = await volunteer_db.execute(update_sql, params)
                
                if result.rowcount > 0:
                    # Insert into maker_decisions
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
                        "maker_id": decision.makerId,
                        "decision_status": decision.decisionStatus,
                        "reason": decision.reason,
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
                    
                    # Log successful update
                    logger.info(
                        f"[{request_id}] Maker decision recorded for volunteer {decision.id}",
                        extra={
                            "volunteer_id": decision.id,
                            "decision_status": decision.decisionStatus,
                            "maker_id": decision.makerId,
                            "request_id": request_id
                        }
                    )
                
            except Exception as e:
                # Log individual record processing error
                await ErrorLogger.log_error(
                    db=volunteer_db,
                    code=ErrorCode.DB_INSERT_FAILED,
                    message=f"Failed to process decision for volunteer {decision.id}: {str(e)}",
                    status_code=500,
                    severity=ErrorSeverity.ERROR,
                    details={
                        "volunteer_id": decision.id,
                        "error": str(e),
                        "index": idx,
                        "request_id": request_id
                    },
                    request_id=request_id
                )
                logger.exception(f"Error processing decision for volunteer {decision.id}")

        await volunteer_db.commit()
        
        # Log success
        logger.info(
            f"[{request_id}] Batch decisions processed successfully",
            extra={
                "total_records": len(decisions),
                "updated_count": len(updated_ids),
                "request_id": request_id
            }
        )

        return {
            "success": True,
            "updated": len(updated_ids),
            "updatedIds": updated_ids,
            "requestId": request_id
        }
        
    except Exception as e:
        await volunteer_db.rollback()
        
        # Log batch processing error
        await ErrorLogger.log_error(
            db=volunteer_db,
            code=ErrorCode.DB_QUERY_FAILED,
            message=f"Batch decision processing failed: {str(e)}",
            status_code=500,
            severity=ErrorSeverity.CRITICAL,
            details={
                "total_records": len(decisions),
                "error": str(e),
                "request_id": request_id
            },
            request_id=request_id
        )
        
        raise HTTPException(
            status_code=500, 
            detail=f"Batch processing failed. Request ID: {request_id}"
        )


# ============================================
# EXAMPLE 2: CNIC Validation with Logging
# ============================================

async def validate_cnic_with_logging(
    cnic: str,
    main_db: AsyncSession
):
    """Validate CNIC with error logging"""
    
    request_id = str(uuid.uuid4())
    
    try:
        # Normalize CNIC
        normalized = cnic.replace("-", "").strip()
        
        # Validate format
        if not normalized or not normalized.isdigit() or len(normalized) != 13:
            await ErrorLogger.log_error(
                db=main_db,
                code=ErrorCode.CNIC_INVALID,
                message=f"Invalid CNIC format: {cnic}",
                status_code=400,
                severity=ErrorSeverity.WARNING,
                details={
                    "cnic_provided": cnic,
                    "normalized": normalized,
                    "request_id": request_id
                },
                request_id=request_id
            )
            
            return {
                "is_valid": False,
                "is_registered": False,
                "name": None,
                "message": "Invalid CNIC format",
                "requestId": request_id
            }
        
        # Check enrollment database
        family_sql = text("""
            SELECT DISTINCT "IdNumber" 
            FROM "FamilyLevelDetails"
            WHERE "IdNumber" = :cnic
            LIMIT 1
        """)
        
        result = await main_db.execute(family_sql, {"cnic": normalized})
        found = result.scalar_one_or_none()
        
        if not found:
            await ErrorLogger.log_error(
                db=main_db,
                code=ErrorCode.CNIC_NOT_FOUND,
                message=f"CNIC not found in enrollment database",
                status_code=400,
                severity=ErrorSeverity.WARNING,
                details={
                    "cnic": normalized,
                    "request_id": request_id
                },
                request_id=request_id
            )
            
            return {
                "is_valid": True,  # Format valid
                "is_registered": False,  # But not registered
                "name": None,
                "message": "CNIC not found in enrollment database",
                "requestId": request_id
            }
        
        logger.info(
            f"[{request_id}] CNIC validated successfully",
            extra={
                "cnic": normalized,
                "request_id": request_id
            }
        )
        
        return {
            "is_valid": True,
            "is_registered": True,
            "name": "Registered",
            "message": "CNIC found in enrollment database",
            "requestId": request_id
        }
        
    except Exception as e:
        await ErrorLogger.log_error(
            db=main_db,
            code=ErrorCode.DB_QUERY_FAILED,
            message=f"CNIC validation failed: {str(e)}",
            status_code=500,
            severity=ErrorSeverity.ERROR,
            details={
                "cnic": cnic,
                "error": str(e),
                "request_id": request_id
            },
            request_id=request_id
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"CNIC validation error. Request ID: {request_id}"
        )


# ============================================
# EXAMPLE 3: Duplicate Detection with Logging
# ============================================

async def check_duplicate_with_logging(
    cnic: str,
    event_id: int,
    duty_type_id: int,
    volunteer_db: AsyncSession,
    request_id: str
):
    """Check for duplicate records with logging"""
    
    try:
        check_sql = text("""
            SELECT id FROM volunteer_record
            WHERE replace(coalesce(cnic,''),'-','') = :cnic
              AND event_id = :event_id
              AND duty_type_id = :duty_type_id
            LIMIT 1
        """)
        
        result = await volunteer_db.execute(
            check_sql,
            {
                "cnic": cnic.replace("-", ""),
                "event_id": event_id,
                "duty_type_id": duty_type_id
            }
        )
        
        duplicate = result.scalar_one_or_none()
        
        if duplicate:
            await ErrorLogger.log_error(
                db=volunteer_db,
                code=ErrorCode.DUPLICATE_RECORD,
                message=f"Duplicate record found for CNIC {cnic} in event {event_id}",
                status_code=400,
                severity=ErrorSeverity.WARNING,
                details={
                    "cnic": cnic,
                    "event_id": event_id,
                    "duty_type_id": duty_type_id,
                    "existing_record_id": duplicate,
                    "request_id": request_id
                },
                request_id=request_id
            )
            
            return True, duplicate
        
        return False, None
        
    except Exception as e:
        await ErrorLogger.log_error(
            db=volunteer_db,
            code=ErrorCode.DB_QUERY_FAILED,
            message=f"Duplicate check failed: {str(e)}",
            status_code=500,
            severity=ErrorSeverity.ERROR,
            details={
                "cnic": cnic,
                "error": str(e),
                "request_id": request_id
            },
            request_id=request_id
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Duplicate check failed. Request ID: {request_id}"
        )
