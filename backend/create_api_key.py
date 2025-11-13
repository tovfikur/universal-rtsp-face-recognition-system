"""
Quick script to create an API key for the Attendance Management System
Run this to generate your initial admin API key.
"""

from pathlib import Path
from attendance_system import AttendanceSystem
import sys

def create_admin_key():
    """Create an admin API key with full permissions"""
    print("\n" + "=" * 60)
    print("API KEY GENERATION - Attendance Management System")
    print("=" * 60 + "\n")

    # Initialize attendance system
    backend_dir = Path(__file__).parent
    db_path = backend_dir / "data" / "attendance.db"

    print(f"Database: {db_path}")

    try:
        system = AttendanceSystem(db_path=db_path)
        print("✓ Attendance system initialized\n")
    except Exception as e:
        print(f"✗ Failed to initialize system: {e}")
        return 1

    # Get key details from user
    print("Enter API key details (or press Enter for defaults):\n")

    key_name = input("Key name [Admin Master Key]: ").strip()
    if not key_name:
        key_name = "Admin Master Key"

    permissions_input = input("Permissions (comma-separated) [*]: ").strip()
    if not permissions_input:
        permissions = ["*"]
    else:
        permissions = [p.strip() for p in permissions_input.split(",")]

    expires_input = input("Expires in days (blank for never) [never]: ").strip()
    if not expires_input:
        expires_days = None
    else:
        try:
            expires_days = int(expires_input)
        except ValueError:
            print("✗ Invalid number, using never expires")
            expires_days = None

    # Create the key
    print("\nCreating API key...")

    try:
        result = system.create_api_key(
            name=key_name,
            permissions=permissions,
            expires_days=expires_days
        )

        if result.get('success'):
            print("\n" + "=" * 60)
            print("✓ API KEY CREATED SUCCESSFULLY")
            print("=" * 60 + "\n")
            print(f"API Key: {result['api_key']}")
            print(f"Name: {key_name}")
            print(f"Permissions: {', '.join(permissions)}")
            if expires_days:
                print(f"Expires: {result.get('expires_at', 'Unknown')}")
            else:
                print("Expires: Never")
            print("\n" + "⚠️  IMPORTANT: Save this key securely!")
            print("This key will not be shown again.\n")
            print("=" * 60 + "\n")

            # Show usage example
            print("Usage Example:")
            print("-" * 60)
            print("curl -H \"X-API-Key: " + result['api_key'] + "\" \\")
            print("  http://localhost:5000/api/v1/status")
            print()

            return 0
        else:
            print(f"✗ Failed to create key: {result.get('error', 'Unknown error')}")
            return 1

    except Exception as e:
        print(f"✗ Error creating key: {e}")
        return 1


def list_existing_keys():
    """List all existing API keys"""
    backend_dir = Path(__file__).parent
    db_path = backend_dir / "data" / "attendance.db"

    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name, permissions, status, created_at, expires_at
            FROM api_keys
            WHERE status = 'active'
            ORDER BY created_at DESC
        """)

        keys = cursor.fetchall()
        conn.close()

        if keys:
            print("\n" + "=" * 60)
            print("EXISTING ACTIVE API KEYS")
            print("=" * 60 + "\n")

            for i, (name, perms, status, created, expires) in enumerate(keys, 1):
                print(f"{i}. {name}")
                print(f"   Permissions: {perms}")
                print(f"   Created: {created}")
                print(f"   Expires: {expires if expires else 'Never'}")
                print()

        else:
            print("\nNo active API keys found.")

    except Exception as e:
        # Database might not exist yet
        pass


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_existing_keys()
        return 0

    print("\nWelcome to the API Key Generator!")
    print("This will create an API key for accessing the system.\n")

    # Show existing keys first
    list_existing_keys()

    # Confirm before creating new key
    confirm = input("\nCreate a new API key? [Y/n]: ").strip().lower()
    if confirm and confirm != 'y':
        print("Cancelled.")
        return 0

    return create_admin_key()


if __name__ == "__main__":
    sys.exit(main())
