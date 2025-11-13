"""
Direct RTSP Stream Test
Tests if RTSP camera can be accessed and frames can be read.
"""

import cv2
import time
import numpy as np

# Your RTSP URL
RTSP_URL = "rtsp://admin:123456789m@192.168.50.210:554/cam/realmonitor?channel=4&subtype=0"

print("=" * 70)
print("RTSP Stream Direct Test")
print("=" * 70)
print(f"Testing URL: {RTSP_URL}")
print()

# Test 1: Basic connection
print("[TEST 1] Basic Connection Test")
print("-" * 70)
print("Attempting to open RTSP stream with FFmpeg backend...")

cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)

if not cap.isOpened():
    print("❌ FAILED: Cannot open RTSP stream")
    exit(1)

print("✅ SUCCESS: Stream opened")

# Get stream properties
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

print(f"Stream properties: {width}x{height} @ {fps}fps")
print()

# Test 2: Read frames
print("[TEST 2] Frame Reading Test")
print("-" * 70)
print("Attempting to read 10 frames...")
print()

frame_times = []
successful_reads = 0
failed_reads = 0

for i in range(10):
    start_time = time.time()

    ret, frame = cap.read()

    read_time = time.time() - start_time
    frame_times.append(read_time)

    if ret and frame is not None:
        successful_reads += 1
        h, w = frame.shape[:2]
        print(f"Frame {i+1}: ✅ SUCCESS - {w}x{h} - Read time: {read_time:.3f}s")

        # Test downscaling
        if w > 1280 or h > 720:
            scale = min(1280 / w, 720 / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            print(f"         Downscaled to: {new_w}x{new_h}")
    else:
        failed_reads += 1
        print(f"Frame {i+1}: ❌ FAILED - Read time: {read_time:.3f}s")

    # Small delay between reads
    time.sleep(0.1)

print()
print("-" * 70)
print(f"Results: {successful_reads} successful, {failed_reads} failed")

if frame_times:
    avg_time = sum(frame_times) / len(frame_times)
    min_time = min(frame_times)
    max_time = max(frame_times)
    print(f"Read times: avg={avg_time:.3f}s, min={min_time:.3f}s, max={max_time:.3f}s")

# Test 3: Continuous reading with display
if successful_reads > 0:
    print()
    print("[TEST 3] Live Preview Test")
    print("-" * 70)
    print("Opening live preview window...")
    print("Press 'q' to quit, 's' to save screenshot")
    print()

    frame_count = 0
    start_time = time.time()

    while True:
        ret, frame = cap.read()

        if not ret or frame is None:
            print("❌ Frame read failed, retrying...")
            time.sleep(0.1)
            continue

        frame_count += 1
        h, w = frame.shape[:2]

        # Downscale if needed
        if w > 1280 or h > 720:
            scale = min(1280 / w, 720 / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            display_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            display_frame = frame.copy()

        # Calculate FPS
        elapsed = time.time() - start_time
        current_fps = frame_count / elapsed if elapsed > 0 else 0

        # Add info overlay
        cv2.putText(display_frame, f"Original: {w}x{h}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display_frame, f"Display: {display_frame.shape[1]}x{display_frame.shape[0]}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display_frame, f"FPS: {current_fps:.1f}", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display_frame, f"Frame: {frame_count}", (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Show frame
        cv2.imshow("RTSP Stream Test", display_frame)

        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("User quit")
            break
        elif key == ord('s'):
            filename = f"rtsp_screenshot_{int(time.time())}.jpg"
            cv2.imwrite(filename, frame)
            print(f"Screenshot saved: {filename}")

        # Auto-quit after 100 frames for testing
        if frame_count >= 100:
            print(f"Captured 100 frames successfully!")
            break

    cv2.destroyAllWindows()

# Cleanup
cap.release()

print()
print("=" * 70)
print("Test Complete")
print("=" * 70)

if successful_reads == 10:
    print("✅ ALL TESTS PASSED")
    print("Your RTSP stream is working perfectly!")
else:
    print(f"⚠️ PARTIAL SUCCESS: {successful_reads}/10 frames read")
    print("Stream is working but may have reliability issues")
