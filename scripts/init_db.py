#!/usr/bin/env python3
"""
Database initialization script for JamatKhana API
This script can be used to set up the database schema and initial data
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the parent directory to the path so we can import from main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import engine, Base, RegionalCouncil, LocalCouncil, JamatKhana, UserRole, UserStatus, EnumeratorStatus, CheckerStatus, RejectReason, User

async def init_database():
    """Initialize the database with tables and initial data"""
    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Database tables created successfully")
        
        # Insert initial data
        await insert_initial_data()
        
        print("✅ Database initialization completed successfully!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        raise

async def insert_initial_data():
    """Insert initial data into the database"""
    async with engine.begin() as conn:
        # Insert roles
        roles_data = [
            {"Id": 1, "Name": "Enumerator"},
            {"Id": 2, "Name": "Checker"},
            {"Id": 3, "Name": "Admin"}
        ]
        
        for role_data in roles_data:
            await conn.execute(
                UserRole.__table__.insert().on_conflict_do_nothing(),
                role_data
            )
        
        # Insert user statuses
        statuses_data = [
            {"Id": 1, "Name": "Active"},
            {"Id": 2, "Name": "Inactive"},
            {"Id": 3, "Name": "Suspended"}
        ]
        
        for status_data in statuses_data:
            await conn.execute(
                UserStatus.__table__.insert().on_conflict_do_nothing(),
                status_data
            )
        
        # Insert enumerator statuses
        enum_statuses_data = [
            {"Id": 1, "Name": "Pending"},
            {"Id": 2, "Name": "In Progress"},
            {"Id": 3, "Name": "Completed"},
            {"Id": 4, "Name": "Rejected"}
        ]
        
        for status_data in enum_statuses_data:
            await conn.execute(
                EnumeratorStatus.__table__.insert().on_conflict_do_nothing(),
                status_data
            )
        
        # Insert checker statuses
        checker_statuses_data = [
            {"Id": 1, "Name": "Pending"},
            {"Id": 2, "Name": "Under Review"},
            {"Id": 3, "Name": "Approved"},
            {"Id": 4, "Name": "Rejected"}
        ]
        
        for status_data in checker_statuses_data:
            await conn.execute(
                CheckerStatus.__table__.insert().on_conflict_do_nothing(),
                status_data
            )
        
        # Insert reject reasons
        reject_reasons_data = [
            {"Id": 1, "Reason": "Incomplete Information"},
            {"Id": 2, "Reason": "Invalid Data"},
            {"Id": 3, "Reason": "Duplicate Entry"},
            {"Id": 4, "Reason": "Other"}
        ]
        
        for reason_data in reject_reasons_data:
            await conn.execute(
                RejectReason.__table__.insert().on_conflict_do_nothing(),
                reason_data
            )
        
        # Insert sample regional council
        await conn.execute(
            RegionalCouncil.__table__.insert().on_conflict_do_nothing(),
            {"Id": "RC001", "Code": 1, "Name": "Sample Regional Council"}
        )
        
        # Insert sample local council
        await conn.execute(
            LocalCouncil.__table__.insert().on_conflict_do_nothing(),
            {"Id": "LC001", "Code": 1, "Name": "Sample Local Council", "RegionalCouncilId": "RC001"}
        )
        
        # Insert sample JamatKhana
        await conn.execute(
            JamatKhana.__table__.insert().on_conflict_do_nothing(),
            {"Id": "JK001", "Code": "JK001", "Name": "Sample JamatKhana", "LocalCouncilId": "LC001"}
        )
        
        # Insert sample admin user (password: password123)
        await conn.execute(
            User.__table__.insert().on_conflict_do_nothing(),
            {
                "Id": "ADMIN001",
                "Email": "admin@example.com",
                "FullName": "System Administrator",
                "PhoneNumber": "+1234567890",
                "PasswordHash": "$2b$12$6uO2t7GKgSVhj2NtFfNCbuTlJLVlKBHv7AaplQObwjX/QnoNBZ/7u",
                "RoleId": 3,
                "StatusId": 1,
                "JamatKhanaIds": ["JK001"],
                "CreatedAt": datetime.utcnow(),
                "UpdatedAt": datetime.utcnow(),
                "IsActive": True
            }
        )
        
        # Insert sample enumerator user (password: password123)
        await conn.execute(
            User.__table__.insert().on_conflict_do_nothing(),
            {
                "Id": "ENUM001",
                "Email": "enumerator@example.com",
                "FullName": "John Doe - Enumerator",
                "PhoneNumber": "+1234567891",
                "PasswordHash": "$2b$12$6uO2t7GKgSVhj2NtFfNCbuTlJLVlKBHv7AaplQObwjX/QnoNBZ/7u",
                "RoleId": 1,
                "StatusId": 1,
                "JamatKhanaIds": ["JK001"],
                "CreatedAt": datetime.utcnow(),
                "UpdatedAt": datetime.utcnow(),
                "IsActive": True
            }
        )
        
        # Insert sample checker user (password: password123)
        await conn.execute(
            User.__table__.insert().on_conflict_do_nothing(),
            {
                "Id": "CHECK001",
                "Email": "checker@example.com",
                "FullName": "Jane Smith - Checker",
                "PhoneNumber": "+1234567892",
                "PasswordHash": "$2b$12$6uO2t7GKgSVhj2NtFfNCbuTlJLVlKBHv7AaplQObwjX/QnoNBZ/7u",
                "RoleId": 2,
                "StatusId": 1,
                "JamatKhanaIds": ["JK001"],
                "CreatedAt": datetime.utcnow(),
                "UpdatedAt": datetime.utcnow(),
                "IsActive": True
            }
        )
        
        print("✅ Initial data inserted successfully")
        print("📧 Default users created:")
        print("   Admin: admin@example.com / password123")
        print("   Enumerator: enumerator@example.com / password123")
        print("   Checker: checker@example.com / password123")

if __name__ == "__main__":
    print("🚀 Starting database initialization...")
    asyncio.run(init_database())
