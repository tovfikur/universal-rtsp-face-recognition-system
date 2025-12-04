"""
Diagnostic script to test person detection on a single frame from RTSP stream.
"""

import cv2
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from detector import PersonDetector
from video_sources import EnhancedVideoStream, parse_source
from enhanced_recognition import enhance_frame_for_detection

RTSP_URL = "rtsp://admin:123456789m@192.168.50.210:554/cam/realmonitor?channel=1&subtype=0"

def test_detection():
    """Test detection on a frame"""

    print("="*60)
    print("DIAGNOSTIC: Person Detection Test")
    print("="*60)

    # Initialize detector
    print("\n[1] Initializing PersonDetector...")
    detector = PersonDetector(
        model_path="yolov8n.pt",
        confidence=0.35,  # Lowered from 0.65 to detect people reliably
        device="auto",
        batch_size=8,
        min_person_area=1500,  # Lowered from 3000 to detect smaller/distant people
        max_aspect_ratio=4.0,
    )
    print(f"[1] OK - Detector initialized (device: {detector.device})")

    # Connect to RTSP stream
    print(f"\n[2] Connecting to RTSP: {RTSP_URL}")
    source = parse_source(RTSP_URL)
    video_stream = EnhancedVideoStream(
        source=source,
        reconnect_delay=5.0,
        max_reconnect_attempts=3,
        buffer_size=1,
        max_width=1280,
        max_height=720
    )
    print("[2] OK - Stream connected")

    # Get a frame
    print("\n[3] Getting frame from stream...")
    import time
    time.sleep(2)  # Wait for stream to stabilize
    frame = video_stream.get_frame()

    if frame is None:
        print("[3] ERROR - No frame available!")
        return

    print(f"[3] OK - Got frame: {frame.shape}")

    # Save original frame
    output_dir = Path("test_screenshots")
    output_dir.mkdir(exist_ok=True)
    cv2.imwrite(str(output_dir / "diag_01_original.jpg"), frame)
    print(f"[3] Saved: test_screenshots/diag_01_original.jpg")

    # Enhance frame
    print("\n[4] Enhancing frame...")
    enhanced_frame = enhance_frame_for_detection(frame)
    print(f"[4] OK - Enhanced frame: {enhanced_frame.shape}")
    cv2.imwrite(str(output_dir / "diag_02_enhanced.jpg"), enhanced_frame)
    print(f"[4] Saved: test_screenshots/diag_02_enhanced.jpg")

    # Detect persons
    print("\n[5] Running person detection...")
    detections = detector.detect_immediate(enhanced_frame)
    print(f"[5] OK - Detected {len(detections)} persons")

    if len(detections) == 0:
        print("[5] WARNING - No persons detected!")
        print("[5] Trying with original (non-enhanced) frame...")
        detections = detector.detect_immediate(frame)
        print(f"[5] OK - Detected {len(detections)} persons in original frame")

    # Draw detections
    print("\n[6] Drawing detections...")
    output_frame = enhanced_frame.copy()

    for i, detection in enumerate(detections):
        bbox = detection['bbox']
        confidence = detection['confidence']
        x1, y1, x2, y2 = [int(v) for v in bbox]

        print(f"[6] Person {i+1}: bbox=({x1},{y1},{x2},{y2}), conf={confidence:.2f}")

        # Draw ellipse (same as backend)
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)
        radius_x = int((x2 - x1) / 2)
        radius_y = int((y2 - y1) / 2)

        cv2.ellipse(output_frame, (center_x, center_y), (radius_x, radius_y),
                   0, 0, 360, (0, 255, 0), 3)

        # Draw label
        label = f"Person {i+1} ({confidence*100:.0f}%)"
        cv2.putText(output_frame, label, (x1, max(20, y1 - 10)),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imwrite(str(output_dir / "diag_03_with_detections.jpg"), output_frame)
    print(f"[6] Saved: test_screenshots/diag_03_with_detections.jpg")

    # Cleanup
    video_stream.stop()
    detector.stop()

    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)
    print(f"\nResults:")
    print(f"- Frame size: {frame.shape}")
    print(f"- Persons detected: {len(detections)}")
    print(f"- Output saved to: {output_dir}")
    print("\nPlease check the output images to verify detection is working.")

if __name__ == "__main__":
    try:
        test_detection()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
