"""
Test network accessibility from another device
Run this on ANOTHER computer/phone on the same network
"""
import requests
import sys

def test_connection(ip_address, port=5000):
    """Test if the server is accessible"""
    url = f"http://{ip_address}:{port}"

    print(f"\n{'='*60}")
    print(f"NETWORK ACCESSIBILITY TEST")
    print(f"{'='*60}\n")
    print(f"Testing connection to: {url}")
    print(f"From device: {requests.get('https://api.ipify.org').text}")
    print()

    # Test 1: Health check
    print("[1] Testing /api/health endpoint...")
    try:
        response = requests.get(f"{url}/api/health", timeout=5)
        if response.ok:
            print(f"    [OK] Status: {response.status_code}")
            print(f"    [OK] Server is accessible!")
            data = response.json()
            print(f"    Response: {data.get('status', 'Unknown')}")
            return True
        else:
            print(f"    [FAIL] Status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"    [FAIL] Connection refused")
        print(f"    Possible causes:")
        print(f"      - Backend is not running")
        print(f"      - Firewall is blocking port {port}")
        print(f"      - Wrong IP address")
        return False
    except requests.exceptions.Timeout:
        print(f"    [FAIL] Connection timeout")
        print(f"    Server might be too slow or unreachable")
        return False
    except Exception as e:
        print(f"    [FAIL] Error: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("\nUsage: python test_network_access.py <IP_ADDRESS>")
        print("\nExample:")
        print("  python test_network_access.py 192.168.50.152")
        return 1

    ip_address = sys.argv[1]

    if test_connection(ip_address):
        print(f"\n{'='*60}")
        print("[SUCCESS] Server is accessible from this device!")
        print(f"{'='*60}")
        print(f"\nYou can access the application at:")
        print(f"  http://{ip_address}:5000")
        print()
        return 0
    else:
        print(f"\n{'='*60}")
        print("[FAILED] Server is NOT accessible from this device")
        print(f"{'='*60}")
        print("\nTroubleshooting steps:")
        print("1. Verify backend is running on the server")
        print("2. Check Windows Firewall allows port 5000")
        print("3. Verify IP address is correct")
        print("4. Ensure both devices are on the same network")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
