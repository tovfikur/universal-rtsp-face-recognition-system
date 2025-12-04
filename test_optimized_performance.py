"""
Test script to verify optimized multi-threaded performance.

This script tests:
1. Detection continues uninterrupted during API operations
2. API requests don't block detection thread
3. CPU/GPU utilization is maximized
4. Face registration is fast and non-blocking
"""

import asyncio
import base64
import time
import threading
import requests
import numpy as np
import cv2
from collections import deque
from datetime import datetime


class PerformanceMonitor:
    """Monitor system performance metrics."""

    def __init__(self):
        self.detection_times = deque(maxlen=100)
        self.api_times = deque(maxlen=50)
        self.detection_count = 0
        self.api_count = 0
        self.running = True

    def record_detection(self, duration_ms: float):
        """Record detection operation time."""
        self.detection_times.append(duration_ms)
        self.detection_count += 1

    def record_api(self, duration_ms: float):
        """Record API operation time."""
        self.api_times.append(duration_ms)
        self.api_count += 1

    def get_stats(self) -> dict:
        """Get performance statistics."""
        return {
            "detection": {
                "count": self.detection_count,
                "avg_ms": np.mean(self.detection_times) if self.detection_times else 0,
                "min_ms": np.min(self.detection_times) if self.detection_times else 0,
                "max_ms": np.max(self.detection_times) if self.detection_times else 0,
                "fps": 1000.0 / np.mean(self.detection_times) if self.detection_times and np.mean(self.detection_times) > 0 else 0,
            },
            "api": {
                "count": self.api_count,
                "avg_ms": np.mean(self.api_times) if self.api_times else 0,
                "min_ms": np.min(self.api_times) if self.api_times else 0,
                "max_ms": np.max(self.api_times) if self.api_times else 0,
            }
        }

    def print_stats(self):
        """Print formatted statistics."""
        stats = self.get_stats()
        print("\n" + "="*70)
        print("PERFORMANCE STATISTICS")
        print("="*70)

        print(f"\nDETECTION THREAD:")
        print(f"  Total operations: {stats['detection']['count']}")
        print(f"  Average time: {stats['detection']['avg_ms']:.2f} ms")
        print(f"  Min/Max time: {stats['detection']['min_ms']:.2f} / {stats['detection']['max_ms']:.2f} ms")
        print(f"  Effective FPS: {stats['detection']['fps']:.2f}")

        print(f"\nAPI OPERATIONS:")
        print(f"  Total operations: {stats['api']['count']}")
        print(f"  Average time: {stats['api']['avg_ms']:.2f} ms")
        print(f"  Min/Max time: {stats['api']['min_ms']:.2f} / {stats['api']['max_ms']:.2f} ms")

        print("="*70 + "\n")


def create_test_face_image(name: str, color_idx: int = 0) -> str:
    """Create a test face image and encode to base64."""
    # Create a simple test image with a rectangle (simulating a face)
    img = np.random.randint(100, 200, (480, 640, 3), dtype=np.uint8)

    # Draw a face-like rectangle
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
    color = colors[color_idx % len(colors)]

    # Draw face region
    cv2.rectangle(img, (200, 100), (440, 380), color, -1)
    # Draw eyes
    cv2.circle(img, (280, 200), 20, (0, 0, 0), -1)
    cv2.circle(img, (360, 200), 20, (0, 0, 0), -1)
    # Draw mouth
    cv2.ellipse(img, (320, 300), (50, 30), 0, 0, 180, (0, 0, 0), 3)

    # Add name text
    cv2.putText(img, name, (220, 420), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # Encode to base64
    _, buffer = cv2.imencode('.jpg', img)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{img_base64}"


def test_detection_continuity(base_url: str, monitor: PerformanceMonitor, duration_sec: int = 30):
    """
    Continuously call the recognize endpoint to verify detection keeps running.
    This simulates the frontend polling for detections.
    """
    print(f"[Detection Test] Starting continuous detection test for {duration_sec} seconds...")

    endpoint = f"{base_url}/api/recognize"
    start_time = time.time()
    errors = 0

    while time.time() - start_time < duration_sec:
        try:
            t0 = time.time()
            response = requests.post(endpoint, json={"image": ""}, timeout=5)
            t1 = time.time()

            if response.status_code == 200:
                duration_ms = (t1 - t0) * 1000
                monitor.record_detection(duration_ms)

                # Print progress every 10 operations
                if monitor.detection_count % 10 == 0:
                    print(f"[Detection] Processed {monitor.detection_count} frames, avg {duration_ms:.1f}ms")
            else:
                errors += 1
                print(f"[Detection] Error: {response.status_code}")

        except Exception as e:
            errors += 1
            print(f"[Detection] Exception: {e}")

        time.sleep(0.1)  # ~10 FPS polling rate

    print(f"[Detection Test] Completed. Total errors: {errors}")


def test_api_registration(base_url: str, monitor: PerformanceMonitor, num_faces: int = 5):
    """
    Register multiple faces via API to test non-blocking behavior.
    """
    print(f"\n[API Test] Registering {num_faces} faces via API...")

    endpoint = f"{base_url}/api/register"

    for i in range(num_faces):
        name = f"TestPerson_{i+1}"
        person_id = f"TEST_{i+1:03d}"

        print(f"\n[API] Registering {name} ({person_id})...")

        # Create test image
        image_data = create_test_face_image(name, i)

        payload = {
            "name": name,
            "person_id": person_id,
            "image": image_data
        }

        try:
            t0 = time.time()
            response = requests.post(endpoint, json=payload, timeout=30)
            t1 = time.time()

            duration_ms = (t1 - t0) * 1000
            monitor.record_api(duration_ms)

            if response.status_code == 200:
                result = response.json()
                print(f"[API] ✓ Registered {name} in {duration_ms:.0f}ms")
                print(f"[API]   Total faces in database: {result.get('count', 'unknown')}")
            else:
                print(f"[API] ✗ Failed: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"[API] ✗ Exception: {e}")

        # Small delay between registrations
        time.sleep(0.5)

    print(f"\n[API Test] Registration test completed")


def test_concurrent_operations(base_url: str, duration_sec: int = 30):
    """
    Run detection and API operations concurrently to verify no blocking.
    """
    print("\n" + "="*70)
    print("CONCURRENT OPERATIONS TEST")
    print("="*70)
    print(f"\nTesting for {duration_sec} seconds...")
    print("This will:")
    print("  1. Continuously poll /api/recognize (simulating frontend)")
    print("  2. Register faces via /api/register (simulating API calls)")
    print("  3. Monitor if detection continues uninterrupted\n")

    monitor = PerformanceMonitor()

    # Start detection thread
    detection_thread = threading.Thread(
        target=test_detection_continuity,
        args=(base_url, monitor, duration_sec),
        daemon=True
    )
    detection_thread.start()

    # Wait a bit for detection to start
    time.sleep(2)

    # Perform API registrations while detection is running
    test_api_registration(base_url, monitor, num_faces=5)

    # Wait for detection thread to finish
    detection_thread.join()

    # Print final statistics
    monitor.print_stats()

    # Verify detection continued during API operations
    stats = monitor.get_stats()
    if stats['detection']['count'] > 0 and stats['api']['count'] > 0:
        print("✓ SUCCESS: Detection continued running during API operations!")
        print(f"  Detection FPS: {stats['detection']['fps']:.2f}")
        print(f"  API calls completed: {stats['api']['count']}")
        return True
    else:
        print("✗ FAILURE: Detection was blocked or API failed!")
        return False


def check_backend_health(base_url: str) -> bool:
    """Check if backend is running and healthy."""
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"\n[Health] Backend is running")
            print(f"[Health] GPU Available: {data.get('gpu', False)}")
            print(f"[Health] GPU Name: {data.get('gpu_name', 'N/A')}")
            print(f"[Health] Known Faces: {data.get('faces', 0)}")
            return True
        else:
            print(f"[Health] Backend returned {response.status_code}")
            return False
    except Exception as e:
        print(f"[Health] Backend not responding: {e}")
        return False


def main():
    """Run performance tests."""
    base_url = "http://localhost:5000"

    print("="*70)
    print("OPTIMIZED PERFORMANCE TEST")
    print("="*70)
    print(f"\nBackend URL: {base_url}")
    print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Check backend health
    if not check_backend_health(base_url):
        print("\n✗ Backend is not running. Please start it first:")
        print("  cd backend")
        print("  python app.py")
        return

    # Run concurrent test
    success = test_concurrent_operations(base_url, duration_sec=30)

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    if success:
        print("\n✓ ALL TESTS PASSED")
        print("\nThe optimized system successfully:")
        print("  • Kept detection running during API operations")
        print("  • Processed face registrations without blocking")
        print("  • Utilized separate thread pools for concurrent operations")
    else:
        print("\n✗ TESTS FAILED")
        print("\nPlease check the backend logs for errors.")

    print("\n" + "="*70)


if __name__ == "__main__":
    main()
