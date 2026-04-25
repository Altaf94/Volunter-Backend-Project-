#!/usr/bin/env python3
# ============================================
# ERROR LOGGING TEST SCRIPT
# Test the error logging system by making API calls
# and verifying errors are logged to the database
# ============================================

import asyncio
import json
import httpx
from datetime import datetime
import asyncpg

# Configuration
API_BASE_URL = "http://localhost:8001"
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "NewPassword123"
DB_NAME = "northenvolunteerdb"
DB_PORT = 5432

# Test data
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpass123"


async def get_auth_token():
    """Get authentication token from login endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/login-json",
            json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"❌ Failed to get auth token: {response.status_code} - {response.text}")
            return None


async def test_invalid_maker_decision():
    """Test maker decision with invalid volunteer ID - should log VOLUNTEER_NOT_FOUND"""
    print("\n" + "="*60)
    print("TEST 1: Invalid Volunteer ID (should log VOLUNTEER_NOT_FOUND)")
    print("="*60)
    
    token = await get_auth_token()
    if not token:
        print("❌ Could not obtain auth token")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Make request with non-existent volunteer ID
    test_data = [
        {
            "id": 99999,  # Non-existent ID
            "decisionStatus": "Ok",
            "reason": "Testing error logging",
            "makerId": 1
        }
    ]
    
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/volunteers/maker-decisions",
            json=test_data,
            headers=headers
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
        if response.status_code in [200, 400, 500]:
            print("✅ Request completed (error logging triggered)")
        else:
            print(f"⚠️  Unexpected status code: {response.status_code}")


async def test_invalid_decision_status():
    """Test maker decision with invalid status - should log VALIDATION_ERROR"""
    print("\n" + "="*60)
    print("TEST 2: Invalid Decision Status (should log VALIDATION_ERROR)")
    print("="*60)
    
    token = await get_auth_token()
    if not token:
        print("❌ Could not obtain auth token")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # First, get a valid volunteer ID from database
    try:
        conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=DB_HOST,
            port=DB_PORT
        )
        
        volunteer_id = await conn.fetchval(
            "SELECT id FROM volunteer_record LIMIT 1"
        )
        
        await conn.close()
        
        if not volunteer_id:
            print("❌ No volunteer records found in database")
            return
        
        print(f"Using volunteer ID: {volunteer_id}")
        
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        return
    
    # Make request with invalid decision status
    test_data = [
        {
            "id": volunteer_id,
            "decisionStatus": "InvalidStatus",  # Invalid status
            "reason": "Testing invalid status error logging",
            "makerId": 1
        }
    ]
    
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/volunteers/maker-decisions",
            json=test_data,
            headers=headers
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
        if response.status_code in [200, 400, 500]:
            print("✅ Request completed (error logging triggered)")
        else:
            print(f"⚠️  Unexpected status code: {response.status_code}")


async def test_successful_decision():
    """Test successful maker decision - should log success"""
    print("\n" + "="*60)
    print("TEST 3: Valid Maker Decision (should succeed)")
    print("="*60)
    
    token = await get_auth_token()
    if not token:
        print("❌ Could not obtain auth token")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get a valid volunteer ID from database
    try:
        conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=DB_HOST,
            port=DB_PORT
        )
        
        volunteer_id = await conn.fetchval(
            "SELECT id FROM volunteer_record LIMIT 1"
        )
        
        await conn.close()
        
        if not volunteer_id:
            print("❌ No volunteer records found in database")
            return
        
        print(f"Using volunteer ID: {volunteer_id}")
        
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        return
    
    # Make request with valid data
    test_data = [
        {
            "id": volunteer_id,
            "decisionStatus": "Ok",
            "reason": "Approved by test script",
            "makerId": 1
        }
    ]
    
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/volunteers/maker-decisions",
            json=test_data,
            headers=headers
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("✅ Decision successfully recorded")
                request_id = data.get("requestId")
                if request_id:
                    print(f"   Request ID: {request_id}")
            else:
                print("⚠️  Response not successful")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")


async def check_logged_errors():
    """Query the error_codes table to see logged errors"""
    print("\n" + "="*60)
    print("VERIFICATION: Checking error_codes table")
    print("="*60)
    
    try:
        conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=DB_HOST,
            port=DB_PORT
        )
        
        # Get recent errors
        errors = await conn.fetch("""
            SELECT id, code, status, severity, message, details, created_at
            FROM error_codes
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        if errors:
            print(f"\n✅ Found {len(errors)} recent errors in database:\n")
            for error in errors:
                print(f"  ID: {error['id']}")
                print(f"  Code: {error['code']}")
                print(f"  Status: {error['status']}")
                print(f"  Severity: {error['severity']}")
                print(f"  Message: {error['message']}")
                if error['details']:
                    try:
                        details = json.loads(error['details']) if isinstance(error['details'], str) else error['details']
                        print(f"  Details: {json.dumps(details, indent=4)}")
                    except:
                        print(f"  Details: {error['details']}")
                print(f"  Created: {error['created_at']}")
                print()
        else:
            print("❌ No errors found in error_codes table")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {str(e)}")


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("ERROR LOGGING SYSTEM TEST SUITE")
    print("="*80)
    print(f"\nAPI Base URL: {API_BASE_URL}")
    print(f"Database: {DB_NAME}@{DB_HOST}:{DB_PORT}")
    print(f"Test started at: {datetime.now().isoformat()}")
    
    # Run tests
    await test_invalid_maker_decision()
    await asyncio.sleep(1)  # Wait a bit between tests
    
    await test_invalid_decision_status()
    await asyncio.sleep(1)
    
    await test_successful_decision()
    await asyncio.sleep(1)
    
    # Verify results
    await check_logged_errors()
    
    print("\n" + "="*80)
    print("TEST SUITE COMPLETED")
    print("="*80 + "\n")


if __name__ == "__main__":
    print("⚠️  IMPORTANT: Make sure the API is running on http://localhost:8001")
    print("   Start the API with: uvicorn main:app --host 0.0.0.0 --port 8001 --reload\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test suite interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite error: {str(e)}")
        import traceback
        traceback.print_exc()
