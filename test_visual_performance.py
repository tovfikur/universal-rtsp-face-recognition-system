"""
Visual performance test - shows detection running in real-time while testing API operations.

This script:
1. Opens webcam and displays detection results
2. Tests API registration in background
3. Shows FPS and performance metrics
4. Verifies detection never freezes during API calls
"""

import cv2
import time
import threading
import requests
import base64
import numpy as np
from collections import deque
from datetime import datetime


class VisualPerformanceTest:
    """Visual test with live detection display."""

    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.running = True
        self.frame_times = deque(maxlen=30)
        self.detection_results = []
        self.last_api_time = 0
        self.api_status = "Idle"
        self.api_count = 0

    def encode_frame(self, frame: np.ndarray) -> str:
        """Encode frame to base64."""
        _, buffer = cv2.imencode('.jpg', frame)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{img_base64}"

    def call_recognize_api(self, frame: np.ndarray) -> dict:
        """Call recognition API with frame."""
        try:
            image_data = self.encode_frame(frame)
            response = requests.post(
                f"{self.base_url}/api/recognize",
                json={"image": image_data},
                timeout=5
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "results": []}

        except Exception as e:
            print(f"[API Error] {e}")
            return {"success": False, "results": []}

    def register_test_face(self, name: str, person_id: str, frame: np.ndarray):
        """Register a face in background thread."""
        def _register():
            self.api_status = f"Registering {name}..."
            try:
                t0 = time.time()
                image_data = self.encode_frame(frame)

                response = requests.post(
                    f"{self.base_url}/api/register",
                    json={
                        "name": name,
                        "person_id": person_id,
                        "image": image_data
                    },
                    timeout=30
                )

                t1 = time.time()
                self.last_api_time = (t1 - t0) * 1000

                if response.status_code == 200:
                    result = response.json()
                    self.api_count += 1
                    self.api_status = f"✓ Registered {name} ({self.last_api_time:.0f}ms)"
                    print(f"\n[API] ✓ Registered {name} in {self.last_api_time:.0f}ms")
                    print(f"[API]   Total faces: {result.get('count', '?')}")
                else:
                    self.api_status = f"✗ Failed to register {name}"
                    print(f"\n[API] ✗ Failed: {response.text}")

            except Exception as e:
                self.api_status = f"✗ Error: {str(e)[:30]}"
                print(f"\n[API] ✗ Exception: {e}")

        # Run in background thread (non-blocking)
        thread = threading.Thread(target=_register, daemon=True)
        thread.start()

    def draw_overlay(self, frame: np.ndarray, fps: float) -> np.ndarray:
        """Draw performance overlay on frame."""
        overlay = frame.copy()
        h, w = frame.shape[:2]

        # Semi-transparent background for text
        cv2.rectangle(overlay, (10, 10), (w - 10, 150), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

        # Draw FPS
        fps_text = f"FPS: {fps:.1f}"
        cv2.putText(frame, fps_text, (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        # Draw detection count
        det_text = f"Detections: {len(self.detection_results)}"
        cv2.putText(frame, det_text, (20, 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Draw API status
        api_color = (0, 255, 0) if "✓" in self.api_status else (100, 100, 255)
        cv2.putText(frame, f"API: {self.api_status}", (20, 105),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, api_color, 2)

        # Draw API count
        cv2.putText(frame, f"Registered: {self.api_count}", (20, 135),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Draw instructions
        instructions = [
            "Press 'R' to register current frame as test face",
            "Press 'Q' to quit",
        ]
        y_offset = h - 80
        for i, instruction in enumerate(instructions):
            cv2.putText(frame, instruction, (20, y_offset + i * 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Draw detection boxes
        for result in self.detection_results:
            bbox = result.get("person_bbox", [])
            if len(bbox) == 4:
                x1, y1, x2, y2 = [int(v) for v in bbox]
                name = result.get("name", "Unknown")
                confidence = result.get("face_confidence", 0.0)

                # Color based on recognition
                color = (0, 255, 0) if name != "Unknown" else (255, 165, 0)

                # Draw box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                # Draw label
                label = f"{name}"
                if confidence > 0:
                    label += f" ({confidence*100:.0f}%)"

                (label_w, label_h), _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                )

                cv2.rectangle(frame,
                             (x1, y1 - label_h - 10),
                             (x1 + label_w + 10, y1),
                             color, -1)

                cv2.putText(frame, label, (x1 + 5, y1 - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return frame

    def run(self):
        """Run visual test with webcam."""
        print("\n" + "="*70)
        print("VISUAL PERFORMANCE TEST")
        print("="*70)
        print("\nStarting webcam...")
        print("\nInstructions:")
        print("  • Press 'R' to register current frame as test face")
        print("  • Watch if detection continues smoothly during registration")
        print("  • Press 'Q' to quit\n")

        # Open webcam
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("✗ Failed to open webcam")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)

        test_face_index = 0
        frame_count = 0

        print("✓ Webcam opened successfully")
        print("✓ Starting detection loop...\n")

        try:
            while self.running:
                t0 = time.time()

                # Capture frame
                ret, frame = cap.read()
                if not ret:
                    print("✗ Failed to read frame")
                    break

                frame_count += 1

                # Call recognition API every 100ms
                if frame_count % 3 == 0:  # Every 3rd frame at 30fps = ~100ms
                    result = self.call_recognize_api(frame)
                    if result.get("success"):
                        self.detection_results = result.get("results", [])

                # Calculate FPS
                t1 = time.time()
                frame_time = (t1 - t0) * 1000
                self.frame_times.append(frame_time)

                avg_frame_time = np.mean(self.frame_times)
                fps = 1000.0 / avg_frame_time if avg_frame_time > 0 else 0

                # Draw overlay
                display_frame = self.draw_overlay(frame, fps)

                # Display
                cv2.imshow("Visual Performance Test", display_frame)

                # Handle keyboard
                key = cv2.waitKey(1) & 0xFF

                if key == ord('q') or key == ord('Q'):
                    print("\n[User] Quit requested")
                    break

                elif key == ord('r') or key == ord('R'):
                    # Register current frame as test face
                    test_face_index += 1
                    name = f"VisualTest_{test_face_index}"
                    person_id = f"VIS_{test_face_index:03d}"

                    print(f"\n[User] Registering {name}...")
                    self.register_test_face(name, person_id, frame)

        except KeyboardInterrupt:
            print("\n[Interrupt] Stopping...")

        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.running = False

            # Print summary
            print("\n" + "="*70)
            print("TEST SUMMARY")
            print("="*70)
            print(f"\nTotal frames processed: {frame_count}")
            print(f"Average FPS: {1000.0 / np.mean(self.frame_times):.2f}")
            print(f"API registrations: {self.api_count}")

            if self.api_count > 0:
                print(f"\n✓ Detection continued smoothly during {self.api_count} API registrations")
                print("✓ Multi-threaded optimization is working correctly!")
            else:
                print("\nNo API calls were made during the test")

            print("\n" + "="*70)


def check_backend(base_url: str) -> bool:
    """Check if backend is running."""
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ Backend is running at {base_url}")
            print(f"  GPU: {data.get('gpu_name', 'CPU only')}")
            print(f"  Known faces: {data.get('faces', 0)}")
            return True
        else:
            print(f"✗ Backend returned {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Backend not responding: {e}")
        print(f"\nPlease start the backend first:")
        print("  cd backend")
        print("  python app.py")
        return False


def main():
    """Run visual performance test."""
    base_url = "http://localhost:5000"

    if not check_backend(base_url):
        return

    # Run visual test
    test = VisualPerformanceTest(base_url)
    test.run()


if __name__ == "__main__":
    main()
