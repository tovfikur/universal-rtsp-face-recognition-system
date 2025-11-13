"""
Verification script for the Attendance Management System
Run this before starting the server to ensure everything is configured correctly.
"""

import sys
from pathlib import Path

def verify_imports():
    """Verify all required modules can be imported"""
    print("=" * 60)
    print("STEP 1: Verifying Python Dependencies")
    print("=" * 60)

    required_modules = [
        ('quart', 'Quart'),
        ('quart_cors', 'Quart-CORS'),
        ('hypercorn', 'Hypercorn'),
        ('numpy', 'NumPy'),
        ('cv2', 'OpenCV'),
        ('ultralytics', 'Ultralytics'),
        ('face_recognition', 'Face Recognition'),
    ]

    missing = []
    for module, name in required_modules:
        try:
            __import__(module)
            print(f"✓ {name}")
        except ImportError:
            print(f"✗ {name} - NOT INSTALLED")
            missing.append(name)

    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False

    print("\n✓ All dependencies installed\n")
    return True


def verify_project_files():
    """Verify all required project files exist"""
    print("=" * 60)
    print("STEP 2: Verifying Project Files")
    print("=" * 60)

    backend_dir = Path(__file__).parent

    required_files = [
        'app.py',
        'attendance_system.py',
        'api_routes.py',
        'database.py',
        'detector.py',
        'recognizer.py',
        'tracker.py',
        'stream_state.py',
        'detection_history.py',
        'video_sources.py',
    ]

    missing = []
    for file in required_files:
        file_path = backend_dir / file
        if file_path.exists():
            print(f"✓ {file}")
        else:
            print(f"✗ {file} - NOT FOUND")
            missing.append(file)

    if missing:
        print(f"\n⚠️  Missing files: {', '.join(missing)}")
        return False

    print("\n✓ All project files present\n")
    return True


def verify_directories():
    """Verify required directories exist"""
    print("=" * 60)
    print("STEP 3: Verifying Data Directories")
    print("=" * 60)

    backend_dir = Path(__file__).parent

    required_dirs = [
        'data',
        'faces',
    ]

    for dir_name in required_dirs:
        dir_path = backend_dir / dir_name
        if dir_path.exists():
            print(f"✓ {dir_name}/ exists")
        else:
            print(f"⚠️  {dir_name}/ not found - will be created automatically")
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ Created {dir_name}/")

    print("\n✓ Data directories ready\n")
    return True


def verify_attendance_system():
    """Verify the attendance system can be initialized"""
    print("=" * 60)
    print("STEP 4: Verifying Attendance System")
    print("=" * 60)

    try:
        from attendance_system import AttendanceSystem
        print("✓ AttendanceSystem module imported")

        backend_dir = Path(__file__).parent
        test_db = backend_dir / "data" / "test_attendance.db"

        # Test initialization
        system = AttendanceSystem(db_path=test_db)
        print("✓ AttendanceSystem initialized successfully")

        # Test database structure
        import sqlite3
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = ['persons', 'attendance', 'detection_events',
                          'system_config', 'api_keys', 'system_logs']

        for table in expected_tables:
            if table in tables:
                print(f"✓ Table '{table}' created")
            else:
                print(f"✗ Table '{table}' missing")
                conn.close()
                return False

        conn.close()

        # Clean up test database
        test_db.unlink()

        print("\n✓ Attendance system verified\n")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def verify_api_routes():
    """Verify API routes can be imported"""
    print("=" * 60)
    print("STEP 5: Verifying API Routes")
    print("=" * 60)

    try:
        from api_routes import api_bp, init_api_routes
        print("✓ API routes module imported")
        print(f"✓ API Blueprint prefix: {api_bp.url_prefix}")

        # Count routes
        route_count = len(api_bp.deferred_functions)
        print(f"✓ {route_count} route handlers registered")

        print("\n✓ API routes verified\n")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def print_next_steps():
    """Print instructions for next steps"""
    print("=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print()
    print("1. Start the server:")
    print("   cd backend")
    print("   hypercorn app:app --bind 0.0.0.0:5000")
    print()
    print("2. Generate an API key (in Python console):")
    print("   from attendance_system import AttendanceSystem")
    print("   from pathlib import Path")
    print("   system = AttendanceSystem(Path('data/attendance.db'))")
    print("   result = system.create_api_key(")
    print("       name='Admin Master Key',")
    print("       permissions=['*'],")
    print("       expires_days=None")
    print("   )")
    print("   print(f\"API Key: {result['api_key']}\")")
    print()
    print("3. Test the API:")
    print("   curl http://localhost:5000/api/v1/health")
    print()
    print("4. View documentation:")
    print("   - API Reference: API_DOCUMENTATION.md")
    print("   - Setup Guide: SETUP_GUIDE.md")
    print()


def main():
    """Run all verification checks"""
    print("\n" + "=" * 60)
    print("ATTENDANCE MANAGEMENT SYSTEM - SETUP VERIFICATION")
    print("=" * 60 + "\n")

    all_passed = True

    # Run verification steps
    all_passed &= verify_imports()
    all_passed &= verify_project_files()
    all_passed &= verify_directories()
    all_passed &= verify_attendance_system()
    all_passed &= verify_api_routes()

    # Print summary
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    if all_passed:
        print("✓ ALL CHECKS PASSED")
        print("\nYour system is ready to use!")
        print_next_steps()
        return 0
    else:
        print("✗ SOME CHECKS FAILED")
        print("\nPlease resolve the issues above before starting the server.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
