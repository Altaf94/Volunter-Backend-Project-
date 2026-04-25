#!/usr/bin/env python3
# ============================================
# DIRECT ERROR LOGGING VERIFICATION SCRIPT
# Tests the error logging system directly without API
# ============================================

import asyncio
import asyncpg
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

# Database Configuration
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "NewPassword123"
DB_NAME = "northenvolunteerdb"
DB_PORT = 5432

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


async def test_direct_error_logging():
    """Test error logging by directly calling the error logger"""
    print("\n" + "="*80)
    print("DIRECT ERROR LOGGING TEST")
    print("="*80)
    
    # Create database engine
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True
    )
    
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    try:
        async with async_session_maker() as session:
            # Import the error logger
            from error_logging import ErrorLogger, ErrorCode, ErrorSeverity
            import uuid
            
            request_id = str(uuid.uuid4())
            print(f"\nRequest ID: {request_id}")
            
            # Test 1: Log CNIC_NOT_FOUND error
            print("\n--- Test 1: Logging CNIC_NOT_FOUND error ---")
            await ErrorLogger.log_error(
                db=session,
                code=ErrorCode.CNIC_NOT_FOUND,
                message="CNIC 1234567890 not found in enrollment database",
                status_code=400,
                severity=ErrorSeverity.WARNING,
                details={
                    "cnic": "1234567890",
                    "search_date": "2026-04-25",
                    "request_id": request_id
                },
                request_id=request_id
            )
            print("✅ CNIC_NOT_FOUND logged")
            
            # Test 2: Log DUPLICATE_RECORD error
            print("\n--- Test 2: Logging DUPLICATE_RECORD error ---")
            await ErrorLogger.log_error(
                db=session,
                code=ErrorCode.DUPLICATE_RECORD,
                message="Duplicate record found for CNIC 9876543210 in event 1",
                status_code=400,
                severity=ErrorSeverity.WARNING,
                details={
                    "cnic": "9876543210",
                    "event_id": 1,
                    "duty_type_id": 2,
                    "existing_record_id": 42,
                    "request_id": request_id
                },
                request_id=request_id
            )
            print("✅ DUPLICATE_RECORD logged")
            
            # Test 3: Log VALIDATION_ERROR
            print("\n--- Test 3: Logging VALIDATION_ERROR ---")
            await ErrorLogger.log_error(
                db=session,
                code=ErrorCode.VALIDATION_ERROR,
                message="Invalid decision status provided",
                status_code=400,
                severity=ErrorSeverity.ERROR,
                details={
                    "status_provided": "InvalidStatus",
                    "valid_statuses": ["Ok", "Rejected", "Discrepant-1", "Discrepant-2"],
                    "request_id": request_id
                },
                request_id=request_id
            )
            print("✅ VALIDATION_ERROR logged")
            
            # Test 4: Log DB_INSERT_FAILED error
            print("\n--- Test 4: Logging DB_INSERT_FAILED error ---")
            await ErrorLogger.log_error(
                db=session,
                code=ErrorCode.DB_INSERT_FAILED,
                message="Failed to insert maker decision record",
                status_code=500,
                severity=ErrorSeverity.ERROR,
                details={
                    "volunteer_id": 123,
                    "error_type": "foreign_key_constraint",
                    "error_detail": "violates foreign key constraint",
                    "request_id": request_id
                },
                request_id=request_id
            )
            print("✅ DB_INSERT_FAILED logged")
            
            # Test 5: Log CRITICAL error
            print("\n--- Test 5: Logging CRITICAL error ---")
            await ErrorLogger.log_error(
                db=session,
                code=ErrorCode.DB_CONNECTION_FAILED,
                message="Database connection pool exhausted",
                status_code=503,
                severity=ErrorSeverity.CRITICAL,
                details={
                    "pool_size": 20,
                    "pool_overflow": 40,
                    "active_connections": 45,
                    "request_id": request_id
                },
                request_id=request_id
            )
            print("✅ DB_CONNECTION_FAILED logged")
        
        print("\n✅ All direct logging tests completed!")
        
    except Exception as e:
        print(f"\n❌ Error during direct logging: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()
    
    return True


async def verify_logged_errors():
    """Query the error_codes table to verify logged errors"""
    print("\n" + "="*80)
    print("VERIFICATION: Querying error_codes table")
    print("="*80)
    
    try:
        conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=DB_HOST,
            port=DB_PORT
        )
        
        # Count total errors
        total_count = await conn.fetchval("SELECT COUNT(*) FROM error_codes")
        print(f"\n📊 Total errors in database: {total_count}")
        
        # Get errors by severity
        print("\n📊 Errors by Severity:")
        severity_counts = await conn.fetch("""
            SELECT severity, COUNT(*) as count
            FROM error_codes
            GROUP BY severity
            ORDER BY count DESC
        """)
        for row in severity_counts:
            print(f"   {row['severity']}: {row['count']}")
        
        # Get errors by code
        print("\n📊 Errors by Code:")
        code_counts = await conn.fetch("""
            SELECT code, COUNT(*) as count
            FROM error_codes
            GROUP BY code
            ORDER BY count DESC
            LIMIT 10
        """)
        for row in code_counts:
            print(f"   {row['code']}: {row['count']}")
        
        # Get recent errors
        print("\n📋 Last 15 Errors:")
        print("-" * 80)
        errors = await conn.fetch("""
            SELECT id, code, status, severity, message, details, created_at
            FROM error_codes
            ORDER BY created_at DESC
            LIMIT 15
        """)
        
        for i, error in enumerate(errors, 1):
            print(f"\n{i}. [{error['created_at']}]")
            print(f"   Code: {error['code']}")
            print(f"   Status: {error['status']}")
            print(f"   Severity: {error['severity']}")
            print(f"   Message: {error['message']}")
            if error['details']:
                try:
                    details = json.loads(error['details']) if isinstance(error['details'], str) else error['details']
                    details_str = json.dumps(details, indent=6)
                    print(f"   Details:\n{details_str}")
                except:
                    print(f"   Details: {error['details']}")
        
        print("\n" + "-" * 80)
        print("✅ Verification complete!")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Verification error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def check_log_files():
    """Check if log files were created"""
    print("\n" + "="*80)
    print("LOG FILES CHECK")
    print("="*80)
    
    import os
    from pathlib import Path
    
    log_dir = Path("logs")
    
    if log_dir.exists():
        print(f"\n✅ Log directory exists: {log_dir.absolute()}")
        
        log_files = list(log_dir.glob("*"))
        if log_files:
            print(f"\n📁 Log files ({len(log_files)}):")
            for log_file in sorted(log_files):
                size = log_file.stat().st_size
                print(f"   {log_file.name} ({size:,} bytes)")
                
                # Show last few lines of each file
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        print(f"      Last 3 lines:")
                        for line in lines[-3:]:
                            print(f"      {line.rstrip()}")
        else:
            print("⚠️  Log directory is empty")
    else:
        print(f"⚠️  Log directory does not exist: {log_dir.absolute()}")


async def main():
    """Run all verification tests"""
    print("\n" + "="*80)
    print("ERROR LOGGING SYSTEM VERIFICATION")
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*80)
    
    # Test direct error logging
    if await test_direct_error_logging():
        await asyncio.sleep(1)
        
        # Verify logged errors
        await verify_logged_errors()
        
        # Check log files
        await check_log_files()
    
    print("\n" + "="*80)
    print("VERIFICATION COMPLETE")
    print(f"Finished at: {datetime.now().isoformat()}")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Verification error: {str(e)}")
        import traceback
        traceback.print_exc()
