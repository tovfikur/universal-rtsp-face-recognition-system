"""
API Testing Script for Attendance Management System

This script tests all major API endpoints to ensure the system is working correctly.
Make sure the server is running before executing this script.

Usage:
    python test_api.py <API_KEY>

Example:
    python test_api.py sk_1234567890abcdef
"""

import sys
import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:5000/api/v1"
HEADERS = {}


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_result(endpoint, method, status_code, response_data):
    """Print formatted result"""
    status_icon = "✓" if 200 <= status_code < 300 else "✗"
    print(f"{status_icon} {method:6} {endpoint:40} [{status_code}]")

    if isinstance(response_data, dict):
        if response_data.get('success'):
            msg = response_data.get('message', '')
            if msg:
                print(f"   → {msg}")
        else:
            error = response_data.get('error', 'Unknown error')
            print(f"   ✗ {error}")
    print()


def test_health_check():
    """Test health check endpoint (no auth required)"""
    print_section("1. HEALTH CHECK (No Authentication)")

    try:
        response = requests.get(f"{BASE_URL}/health")
        print_result("/health", "GET", response.status_code, response.json())

        if response.status_code == 200:
            data = response.json()
            print(f"   Status: {data.get('status')}")
            print(f"   Version: {data.get('version')}")
            print(f"   Timestamp: {data.get('timestamp')}")
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    return False


def test_system_status():
    """Test system status endpoint"""
    print_section("2. SYSTEM STATUS (Requires Authentication)")

    try:
        response = requests.get(f"{BASE_URL}/status", headers=HEADERS)
        print_result("/status", "GET", response.status_code, response.json())

        if response.status_code == 200:
            data = response.json()
            status = data.get('data', {})
            print(f"   Background Recognition: {status.get('background_recognition_running')}")
            print(f"   Snapshot Analysis: {status.get('snapshot_analysis_running')}")
            print(f"   Active Stream: {status.get('active_video_stream')}")
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    return False


def test_person_management():
    """Test person management endpoints"""
    print_section("3. PERSON MANAGEMENT")

    test_person_id = "TEST001"
    test_person_name = "Test User"

    # Create person
    print("Creating test person...")
    try:
        payload = {
            "person_id": test_person_id,
            "name": test_person_name,
            "email": "test@example.com",
            "department": "Testing",
            "position": "Test Subject"
        }
        response = requests.post(f"{BASE_URL}/persons", json=payload, headers=HEADERS)
        print_result("/persons", "POST", response.status_code, response.json())

        if response.status_code not in [200, 201]:
            # Person might already exist, that's okay
            if "already exists" not in response.json().get('error', '').lower():
                return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    # Get person
    print("Retrieving person...")
    try:
        response = requests.get(f"{BASE_URL}/persons/{test_person_id}", headers=HEADERS)
        print_result(f"/persons/{test_person_id}", "GET", response.status_code, response.json())

        if response.status_code == 200:
            person = response.json().get('data', {})
            print(f"   Name: {person.get('name')}")
            print(f"   Department: {person.get('department')}")
            print(f"   Status: {person.get('status')}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # List persons
    print("Listing all persons...")
    try:
        response = requests.get(f"{BASE_URL}/persons?limit=10", headers=HEADERS)
        print_result("/persons", "GET", response.status_code, response.json())

        if response.status_code == 200:
            data = response.json().get('data', {})
            persons = data.get('persons', [])
            print(f"   Total persons: {data.get('total', 0)}")
            print(f"   Returned: {len(persons)}")
    except Exception as e:
        print(f"✗ Error: {e}")

    return True


def test_attendance_management():
    """Test attendance management endpoints"""
    print_section("4. ATTENDANCE MANAGEMENT")

    test_person_id = "TEST001"
    test_person_name = "Test User"

    # Mark attendance
    print("Marking attendance...")
    try:
        payload = {
            "person_id": test_person_id,
            "person_name": test_person_name,
            "marked_by": "api_test",
            "notes": "API test attendance"
        }
        response = requests.post(f"{BASE_URL}/attendance/mark", json=payload, headers=HEADERS)
        print_result("/attendance/mark", "POST", response.status_code, response.json())

        attendance_id = None
        if response.status_code in [200, 201]:
            attendance_id = response.json().get('attendance_id')
            print(f"   Attendance ID: {attendance_id}")

    except Exception as e:
        print(f"✗ Error: {e}")

    # Get today's attendance
    print("Getting today's attendance...")
    try:
        response = requests.get(f"{BASE_URL}/attendance/today", headers=HEADERS)
        print_result("/attendance/today", "GET", response.status_code, response.json())

        if response.status_code == 200:
            data = response.json().get('data', {})
            records = data.get('records', [])
            print(f"   Total records today: {data.get('total', 0)}")
            if records:
                print(f"   Latest: {records[0].get('person_name')} at {records[0].get('check_in')}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Get person attendance
    print(f"Getting attendance history for {test_person_id}...")
    try:
        response = requests.get(f"{BASE_URL}/attendance/person/{test_person_id}", headers=HEADERS)
        print_result(f"/attendance/person/{test_person_id}", "GET", response.status_code, response.json())

        if response.status_code == 200:
            data = response.json().get('data', {})
            records = data.get('records', [])
            print(f"   Total records: {data.get('total', 0)}")
    except Exception as e:
        print(f"✗ Error: {e}")

    return True


def test_reporting():
    """Test reporting endpoints"""
    print_section("5. REPORTING & ANALYTICS")

    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    # Get attendance report
    print("Getting weekly attendance report...")
    try:
        params = {
            "start_date": week_ago,
            "end_date": today
        }
        response = requests.get(f"{BASE_URL}/reports/attendance", params=params, headers=HEADERS)
        print_result("/reports/attendance", "GET", response.status_code, response.json())

        if response.status_code == 200:
            data = response.json().get('data', {})
            print(f"   Total records: {data.get('total_records', 0)}")
            print(f"   Unique persons: {data.get('unique_persons', 0)}")
            print(f"   Date range: {data.get('start_date')} to {data.get('end_date')}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Get daily summary
    print(f"Getting daily summary for {today}...")
    try:
        response = requests.get(f"{BASE_URL}/reports/daily-summary/{today}", headers=HEADERS)
        print_result(f"/reports/daily-summary/{today}", "GET", response.status_code, response.json())

        if response.status_code == 200:
            data = response.json().get('data', {})
            print(f"   Date: {data.get('date')}")
            print(f"   Present: {data.get('present_count', 0)}")
            print(f"   Total persons: {data.get('total_persons', 0)}")
    except Exception as e:
        print(f"✗ Error: {e}")

    return True


def test_configuration():
    """Test configuration endpoints"""
    print_section("6. SYSTEM CONFIGURATION")

    # Get all config
    print("Getting system configuration...")
    try:
        response = requests.get(f"{BASE_URL}/config", headers=HEADERS)
        print_result("/config", "GET", response.status_code, response.json())

        if response.status_code == 200:
            config = response.json().get('data', {}).get('config', {})
            print(f"   Configuration items: {len(config)}")
            for key, value in list(config.items())[:3]:
                print(f"   - {key}: {value}")
    except Exception as e:
        print(f"✗ Error: {e}")

    return True


def test_logs():
    """Test logging endpoints"""
    print_section("7. SYSTEM LOGS")

    print("Getting recent system logs...")
    try:
        params = {"limit": 10}
        response = requests.get(f"{BASE_URL}/logs", params=params, headers=HEADERS)
        print_result("/logs", "GET", response.status_code, response.json())

        if response.status_code == 200:
            data = response.json().get('data', {})
            logs = data.get('logs', [])
            print(f"   Total logs: {data.get('total', 0)}")
            if logs:
                latest = logs[0]
                print(f"   Latest: [{latest.get('level')}] {latest.get('message')}")
    except Exception as e:
        print(f"✗ Error: {e}")

    return True


def main():
    """Main test runner"""
    global HEADERS

    print("\n" + "=" * 70)
    print("  ATTENDANCE MANAGEMENT SYSTEM - API TEST SUITE")
    print("=" * 70)

    # Check if API key provided
    if len(sys.argv) < 2:
        print("\n✗ Error: API key required")
        print(f"\nUsage: python {sys.argv[0]} <API_KEY>")
        print("\nExample:")
        print(f"  python {sys.argv[0]} sk_1234567890abcdef")
        print("\nTo generate an API key, run:")
        print("  cd backend")
        print("  python create_api_key.py")
        return 1

    api_key = sys.argv[1]
    HEADERS = {"X-API-Key": api_key}

    print(f"\nAPI Key: {api_key[:20]}...")
    print(f"Base URL: {BASE_URL}\n")

    # Run tests
    results = []

    # Test 1: Health check (no auth)
    results.append(("Health Check", test_health_check()))

    # Test 2: System status (with auth)
    results.append(("System Status", test_system_status()))

    # Test 3: Person management
    results.append(("Person Management", test_person_management()))

    # Test 4: Attendance management
    results.append(("Attendance Management", test_attendance_management()))

    # Test 5: Reporting
    results.append(("Reporting", test_reporting()))

    # Test 6: Configuration
    results.append(("Configuration", test_configuration()))

    # Test 7: Logs
    results.append(("System Logs", test_logs()))

    # Print summary
    print_section("TEST SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {test_name}")

    print(f"\nResult: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed! Your API is working correctly.\n")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the output above for details.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
