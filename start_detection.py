"""
Quick script to start background detection and snapshot analysis.
Run this after starting the backend if detection isn't working.
"""

import requests
import time

def start_background_processing(base_url="http://localhost:5000"):
    """Start background processing via API."""
    print("Starting background detection and snapshot analysis...")

    try:
        # Check backend health
        print(f"\n1. Checking backend at {base_url}...")
        response = requests.get(f"{base_url}/api/health", timeout=5)

        if response.status_code != 200:
            print(f"✗ Backend not responding properly (status: {response.status_code})")
            return False

        data = response.json()
        print(f"✓ Backend is running")
        print(f"  - GPU: {data.get('gpu_name', 'CPU')}")
        print(f"  - Known faces: {data.get('faces', 0)}")
        print(f"  - Current source: {data.get('current_source', 'None')}")

        # Start background processing
        print(f"\n2. Starting background processing...")
        response = requests.post(f"{base_url}/api/background/start", timeout=10)

        if response.status_code == 200:
            result = response.json()
            print(f"✓ Background processing started!")
            print(f"  - Status: {result.get('message', 'Started')}")
            return True
        else:
            print(f"✗ Failed to start: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to backend at {base_url}")
        print(f"\nPlease make sure the backend is running:")
        print(f"  cd backend")
        print(f"  python app.py")
        return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    print("="*70)
    print("START BACKGROUND DETECTION")
    print("="*70)

    success = start_background_processing()

    print("\n" + "="*70)
    if success:
        print("✓ Detection is now running!")
        print("\nYou should now see:")
        print("  - Detections appearing in the frontend")
        print("  - Snapshot image updating every 1.5 seconds")
        print("  - Background processing in backend logs")
    else:
        print("✗ Failed to start detection")
        print("\nTroubleshooting:")
        print("  1. Make sure backend is running (python backend/app.py)")
        print("  2. Check backend logs for errors")
        print("  3. Try opening frontend and clicking RTSP button")
    print("="*70)
