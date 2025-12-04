"""
Diagnostic script to check snapshot functionality
Run this while the backend is running
"""
import requests
import time
import os

BASE_URL = "http://localhost:5000"

def check_health():
    """Check if backend is running"""
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.ok:
            data = response.json()
            print("[OK] Backend is running")
            print(f"     GPU: {data.get('gpu_name', 'N/A')}")
            print(f"     Faces: {data.get('faces', 0)}")
            print(f"     Current source: {data.get('current_source', 'None')}")
            return True
        else:
            print(f"[X] Backend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("[X] Backend is not running at http://localhost:5000")
        return False
    except Exception as e:
        print(f"[X] Error: {e}")
        return False

def check_background_status():
    """Check background processing status"""
    try:
        response = requests.get(f"{BASE_URL}/api/background/status", timeout=5)
        if response.ok:
            data = response.json()
            print("\nBackground Processing Status:")
            print(f"  - Stream active: {data.get('stream_active', False)}")
            print(f"  - Background running: {data.get('background_running', False)}")
            print(f"  - Current source: {data.get('current_source', 'None')}")
            print(f"  - Thread alive: {data.get('thread_alive', False)}")
            return data.get('background_running', False)
        else:
            print(f"[X] Status check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[X] Error checking status: {e}")
        return False

def check_snapshot_api():
    """Check if snapshot endpoint is working"""
    print("\nChecking Snapshot API:")
    try:
        response = requests.get(f"{BASE_URL}/api/snapshot?t={int(time.time()*1000)}", timeout=5)

        if response.status_code == 404:
            print("  [X] No snapshot available (404 - file not found)")
            print("      This means the snapshot analysis thread hasn't created a snapshot yet")
            return False
        elif response.ok:
            content_type = response.headers.get('content-type', '')
            if 'image' in content_type:
                print(f"  [OK] Snapshot available! ({len(response.content)} bytes)")

                # Save snapshot for inspection
                snapshot_path = "test_snapshot.jpg"
                with open(snapshot_path, 'wb') as f:
                    f.write(response.content)
                print(f"  [OK] Saved to {snapshot_path}")
                return True
            else:
                print(f"  [X] Unexpected content type: {content_type}")
                return False
        else:
            print(f"  [X] Failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"  [X] Error: {e}")
        return False

def check_snapshot_history():
    """Check snapshot history"""
    print("\nChecking Snapshot History:")
    try:
        response = requests.get(f"{BASE_URL}/api/snapshot/history", timeout=5)
        if response.ok:
            data = response.json()
            if data.get('success'):
                history = data.get('history', [])
                print(f"  [OK] Found {len(history)} snapshots in history")
                for i, item in enumerate(history[:4]):
                    print(f"       {i+1}. {item.get('filename')} - {item.get('timestamp')}")
                return len(history) > 0
            else:
                print("  [X] History API returned success=False")
                return False
        else:
            print(f"  [X] Failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"  [X] Error: {e}")
        return False

def check_snapshot_file():
    """Check if snapshot file exists on disk"""
    print("\nChecking Snapshot File on Disk:")
    snapshot_path = "backend/data/analysis_snapshot.jpg"
    if os.path.exists(snapshot_path):
        size = os.path.getsize(snapshot_path)
        mtime = os.path.getmtime(snapshot_path)
        age = time.time() - mtime
        print(f"  [OK] File exists: {snapshot_path}")
        print(f"       Size: {size} bytes")
        print(f"       Modified: {age:.1f} seconds ago")

        if age > 10:
            print(f"  [!] Warning: File is {age:.1f}s old - snapshot thread may not be running")
            return False
        else:
            print(f"  [OK] File is recent ({age:.1f}s ago)")
            return True
    else:
        print(f"  [X] File not found: {snapshot_path}")
        print("      The snapshot analysis thread hasn't created any snapshots yet")
        return False

def start_background_processing():
    """Start background processing"""
    print("\nStarting Background Processing:")
    try:
        response = requests.post(f"{BASE_URL}/api/background/start", timeout=5)
        if response.ok:
            data = response.json()
            if data.get('success'):
                print("  [OK] Background processing started successfully")
                return True
            else:
                print(f"  [X] Failed: {data.get('message', 'Unknown error')}")
                return False
        else:
            print(f"  [X] Failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"  [X] Error: {e}")
        return False

def main():
    print("=" * 60)
    print("SNAPSHOT DIAGNOSTIC TOOL")
    print("=" * 60)

    # Step 1: Check if backend is running
    print("\n[1] Checking Backend Health...")
    if not check_health():
        print("\n[X] Backend is not running. Please start the backend first:")
        print("   python backend/app.py")
        return

    # Step 2: Check background status
    print("\n[2] Checking Background Processing...")
    bg_running = check_background_status()

    # Step 3: Check snapshot file
    print("\n[3] Checking Snapshot File...")
    file_exists = check_snapshot_file()

    # Step 4: Check snapshot API
    print("\n[4] Checking Snapshot API...")
    api_works = check_snapshot_api()

    # Step 5: Check snapshot history
    print("\n[5] Checking Snapshot History...")
    history_exists = check_snapshot_history()

    # Summary
    print("\n" + "=" * 60)
    print("DIAGNOSIS SUMMARY")
    print("=" * 60)

    issues = []

    if not bg_running:
        issues.append("Background processing is NOT running")
        print("[!] Background processing is NOT running")
        print("    -> Click the 'RTSP' button in the frontend to start it")
        print("    -> Or run: curl -X POST http://localhost:5000/api/background/start")

    if not file_exists:
        issues.append("Snapshot file doesn't exist or is too old")
        print("[!] Snapshot file doesn't exist or is stale")
        print("    -> The snapshot analysis thread may not be running")

    if not api_works:
        issues.append("Snapshot API is not returning images")
        print("[!] Snapshot API is not working")
        print("    -> Check backend logs for errors in snapshot_analysis_loop()")

    if not history_exists:
        issues.append("No snapshot history available")
        print("[!] No snapshot history")

    if not issues:
        print("\n[OK] Everything looks good!")
        print("     Snapshots should be visible in the frontend")
    else:
        print(f"\n[X] Found {len(issues)} issue(s)")

        if not bg_running:
            print("\nRECOMMENDED FIX:")
            print("   1. Make sure a video source is active")
            print("   2. Click the 'RTSP' button to start background detection")
            print("   3. Wait 2-3 seconds for snapshots to be generated")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
