"""
Quick script to configure Odoo connection settings
"""

from pathlib import Path
from attendance_system import AttendanceSystem
import sys


def configure_odoo():
    """Configure Odoo connection interactively"""
    print("\n" + "=" * 60)
    print("ODOO CONFIGURATION - Face Attendance System")
    print("=" * 60 + "\n")

    # Initialize attendance system
    backend_dir = Path(__file__).parent
    db_path = backend_dir / "data" / "attendance.db"

    try:
        system = AttendanceSystem(db_path=db_path)
        print("✓ Attendance system initialized\n")
    except Exception as e:
        print(f"✗ Failed to initialize system: {e}")
        return 1

    # Check if already configured
    existing_config = system.get_odoo_config()
    if existing_config:
        print("Odoo is already configured:")
        print(f"  URL: {existing_config.get('url')}")
        print(f"  Database: {existing_config.get('db')}")
        print(f"  Username: {existing_config.get('username')}")
        print()
        reconfigure = input("Do you want to reconfigure? [y/N]: ").strip().lower()
        if reconfigure != 'y':
            print("Configuration unchanged.")
            return 0

    print("Enter Odoo connection details:\n")

    # Get configuration from user
    url = input("Odoo URL [http://localhost:8069]: ").strip()
    if not url:
        url = "http://localhost:8069"

    db = input("Database name: ").strip()
    if not db:
        print("✗ Database name is required")
        return 1

    username = input("Username [admin]: ").strip()
    if not username:
        username = "admin"

    password = input("Password: ").strip()
    if not password:
        print("✗ Password is required")
        return 1

    print("\nTesting connection...")

    # Test connection
    try:
        from odoo_connector import OdooConnector

        connector = OdooConnector(
            url=url,
            db=db,
            username=username,
            password=password
        )

        result = connector.connect()

        if not result.get('success'):
            print(f"✗ Connection failed: {result.get('error')}")
            print("\nPlease check your credentials and try again.")
            return 1

        print("✓ Connection successful!")
        print(f"  User ID: {result.get('uid')}")

        # Test if we can access employees
        print("\nTesting employee access...")
        emp_result = connector.pull_employees(limit=1)

        if emp_result.get('success'):
            print(f"✓ Can access employees (found {emp_result.get('total', 0)})")
        else:
            print(f"⚠️  Warning: Cannot access employees: {emp_result.get('error')}")
            print("  You may not have permission to access hr.employee model")

    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        return 1

    # Save configuration
    print("\nSaving configuration...")

    try:
        system.set_config('odoo_url', url, 'Odoo server URL')
        system.set_config('odoo_db', db, 'Odoo database name')
        system.set_config('odoo_username', username, 'Odoo username')
        system.set_config('odoo_password', password, 'Odoo password')

        print("✓ Configuration saved successfully\n")

        print("=" * 60)
        print("Odoo is now configured and ready to use!")
        print("=" * 60)
        print("\nYou can now use the Odoo sync APIs:")
        print("  - Pull employees: POST /api/v1/sync/odoo/pull")
        print("  - Push attendance: POST /api/v1/sync/odoo/push")
        print("  - Check status: GET /api/v1/sync/status")
        print()

        return 0

    except Exception as e:
        print(f"✗ Failed to save configuration: {e}")
        return 1


def test_connection():
    """Test existing Odoo configuration"""
    print("\n" + "=" * 60)
    print("TESTING ODOO CONNECTION")
    print("=" * 60 + "\n")

    backend_dir = Path(__file__).parent
    db_path = backend_dir / "data" / "attendance.db"

    try:
        system = AttendanceSystem(db_path=db_path)
        config = system.get_odoo_config()

        if not config:
            print("✗ Odoo is not configured")
            print("Run: python configure_odoo.py")
            return 1

        print("Testing connection with:")
        print(f"  URL: {config['url']}")
        print(f"  Database: {config['db']}")
        print(f"  Username: {config['username']}")
        print()

        from odoo_connector import OdooConnector

        connector = OdooConnector(**config)
        result = connector.test_connection()

        if result.get('success'):
            print("✓ Connection successful!")
            print(f"  Server version: {result.get('server_version')}")
            print(f"  Protocol version: {result.get('protocol_version')}")
            return 0
        else:
            print(f"✗ Connection failed: {result.get('error')}")
            return 1

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return 1


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        return test_connection()
    else:
        return configure_odoo()


if __name__ == "__main__":
    sys.exit(main())
