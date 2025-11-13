"""Smart Recognition System - High Performance Async Flask backend."""

from __future__ import annotations

import asyncio
import base64
import os
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from collections import deque
import concurrent.futures

import cv2
import face_recognition
import numpy as np
from quart import Quart, Response, jsonify, request, send_from_directory
from quart_cors import cors
import torch

# Initialize thread pool for parallel face processing
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

from database import FaceDatabase
from detector import PersonDetector
from recognizer import FaceRecognitionEngine
from tracker import SimpleTracker, TrackedPerson, link_face_to_person
from enhanced_recognition import EnhancedFaceRecognizer, enhance_frame_for_detection
from video_sources import EnhancedVideoStream, parse_source, validate_source, SourceType
from detection_history import DetectionHistory
from stream_state import StreamStateManager
from attendance_system import AttendanceSystem
from api_routes import api_bp, init_api_routes

# Enable GPU optimizations
if torch.cuda.is_available():
    torch.backends.cudnn.benchmark = True
    torch.cuda.set_device(0)

# --------------------------------------------------------------------------- #
# Paths & configuration
# --------------------------------------------------------------------------- #
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

DEFAULT_CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "0")
FACE_MODEL = os.getenv("FACE_MODEL", "hog")
FACE_TOLERANCE = float(os.getenv("FACE_TOLERANCE", "0.45"))
YOLO_DEVICE = os.getenv("YOLO_DEVICE", "auto")

# Performance settings
MAX_WORKERS = 4  # Parallel face processing threads
FRAME_BUFFER_SIZE = 10  # Frames to keep in buffer

# --------------------------------------------------------------------------- #
# Quart app setup for async support
# --------------------------------------------------------------------------- #
app = Quart(
    __name__,
    static_folder=str(FRONTEND_DIR),
    template_folder=str(FRONTEND_DIR),
)
app = cors(app, allow_origin="*")

# Initialize with optimized detector (nano model)
detector = PersonDetector(
    model_path="yolov8n.pt",  # Use nano model for faster processing
    confidence=0.65,  # High confidence - only detect actual persons
    device=YOLO_DEVICE,
    batch_size=8,  # Increased batch size for better throughput
    min_person_area=3000,  # Minimum 3000 pixels (e.g., 50x60)
    max_aspect_ratio=4.0,  # Maximum height/width ratio
)

# Initialize database first
database = FaceDatabase(
    data_dir=BACKEND_DIR / "data",
    faces_dir=BACKEND_DIR / "faces",
    tolerance=FACE_TOLERANCE,
)

# Initialize face recognition with GPU if available
recognizer = FaceRecognitionEngine(
    model="cnn" if torch.cuda.is_available() else "hog",
    upsample_times=1,
    tracking_ttl=2.0,  # Track people for 2 seconds
    max_trackers=30,
    batch_size=8,
)

# Initialize person tracker for persistent IDs
person_tracker = SimpleTracker(
    iou_threshold=0.3,
    max_age=3,  # Remove tracks after 3 missed frames (~1 second)
    min_hits=1,
    face_memory_time=3.0
)

# Initialize enhanced face recognizer for distance/angle robustness
enhanced_recognizer = EnhancedFaceRecognizer(
    base_tolerance=0.65,      # Higher tolerance for angle variations
    min_face_size=30,         # Detect small distant faces
    max_upsample=2,           # More upsampling for distant faces
    quality_threshold=0.25    # Lower threshold to accept more angles
)

# Initialize detection history database
detection_history = DetectionHistory(
    db_path=BACKEND_DIR / "data" / "detection_history.db"
)

# Initialize stream state manager
stream_state = StreamStateManager(
    state_file=BACKEND_DIR / "data" / "stream_state.json"
)

# Initialize attendance management system
attendance_system = AttendanceSystem(
    db_path=BACKEND_DIR / "data" / "attendance.db"
)

# Register API routes blueprint
app.register_blueprint(api_bp)
init_api_routes(attendance_system)

print("[AttendanceSystem] API routes registered at /api/v1")

# Background processing state
background_thread = None
background_running = False

# Independent snapshot analysis state
snapshot_thread = None
snapshot_running = False
latest_snapshot_path = None
snapshot_history = []  # Keep last 4 snapshots for thumbnail display
MAX_SNAPSHOT_HISTORY = 4

# Pre-load known faces from database
if database.count > 0:
    print(f"[INFO] Loading {database.count} known faces into recognition engine...")

    # Load encodings directly from database (much faster than re-extracting from images)
    with database._lock:
        recognizer.known_face_encodings = database._encodings.copy()
        recognizer.known_face_names = [meta["name"] for meta in database._metadata]

    print(f"[INFO] Loaded {len(recognizer.known_face_encodings)} known face encodings")
    print(f"[INFO] Known face names: {recognizer.known_face_names}")

    # Print known face details
    print("[DEBUG] Known face status:")
    print(f"[DEBUG] - Number of known face encodings: {len(recognizer.known_face_encodings)}")
    print(f"[DEBUG] - Number of known face names: {len(recognizer.known_face_names)}")
    print(f"[DEBUG] - Known face names: {recognizer.known_face_names}")
    print(f"[DEBUG] - First face encoding shape: {recognizer.known_face_encodings[0].shape if recognizer.known_face_encodings else 'None'}")
else:
    print("[INFO] No known faces in database")

recent_events: deque = deque(maxlen=100)
EVENT_LIMIT = 50

stream_lock = threading.Lock()
video_stream_cache: Optional[EnhancedVideoStream] = None
current_source: str = DEFAULT_CAMERA_SOURCE

# Frame buffer for smoother processing
frame_buffer = deque(maxlen=FRAME_BUFFER_SIZE)
buffer_lock = threading.Lock()


# =============================================================================
# Background Processing Thread (runs independently of frontend)
# =============================================================================

def background_processing_loop():
    """
    Background thread that continuously processes frames and stores detections.
    Runs independently - frontend only displays results, doesn't drive processing.
    """
    global background_running, video_stream_cache, current_source

    print("[Background] Starting background processing thread...")
    background_running = True
    last_process_time = 0
    process_interval = 0.5  # Process every 500ms

    while background_running:
        try:
            # Check if we have an active stream
            if not video_stream_cache:
                time.sleep(1)
                continue

            # Throttle processing
            now = time.time()
            if now - last_process_time < process_interval:
                time.sleep(0.1)
                continue

            last_process_time = now

            # Get frame from stream
            frame = video_stream_cache.get_frame()
            if frame is None:
                time.sleep(0.1)
                continue

            # Enhance frame
            enhanced_frame = enhance_frame_for_detection(frame)

            # Detect persons using immediate detection
            persons = detector.detect_immediate(enhanced_frame)
            if not persons or len(persons) == 0:
                continue

            # Update tracker
            tracked_persons = person_tracker.update(persons)

            # Process faces for each tracked person
            for track in tracked_persons:
                # Skip if already recognized recently
                if track.status == "Known" and track.name != "Unknown":
                    continue

                x1, y1, x2, y2 = [int(v) for v in track.person_bbox]
                person_region = enhanced_frame[max(0, y1):min(enhanced_frame.shape[0], y2),
                                               max(0, x1):min(enhanced_frame.shape[1], x2)]

                if person_region.size == 0:
                    continue

                # Recognize face using enhanced recognizer (only if database has faces)
                if len(database._encodings) > 0:
                    match_result = enhanced_recognizer.detect_and_recognize(
                        person_region,
                        database._encodings,
                        [meta["name"] for meta in database._metadata],
                        model="cnn" if torch.cuda.is_available() else "hog"
                    )

                    if match_result:
                        track.face_bbox = match_result.get("face_bbox")
                        track.face_confidence = match_result.get("confidence", 0.0)
                        track.name = match_result.get("name", "Unknown")
                        # Get person_id from database metadata
                        if track.name != "Unknown":
                            for meta in database._metadata:
                                if meta["name"] == track.name:
                                    track.person_id = meta.get("person_id", "")
                                    break
                        track.status = "Known" if track.name != "Unknown" else "Unknown"

            # Store detections in database
            for track in tracked_persons:
                if track.status == "Known" and track.name != "Unknown":
                    try:
                        detection_history.add_detection(
                            person_name=track.name,
                            person_id=track.person_id,
                            confidence=track.face_confidence,
                            status=track.status,
                            track_id=track.track_id,
                            bbox=[float(x) for x in track.person_bbox],
                            source=current_source,
                            metadata={
                                "frames_tracked": track.frames_tracked,
                                "background_mode": True
                            }
                        )
                    except Exception as e:
                        print(f"[Background] Error storing detection: {e}")

        except Exception as e:
            print(f"[Background] Processing error: {e}")
            time.sleep(1)

    print("[Background] Background processing thread stopped")


def start_background_processing():
    """Start the background processing thread."""
    global background_thread, background_running

    if background_thread and background_thread.is_alive():
        print("[Background] Already running")
        return

    background_thread = threading.Thread(target=background_processing_loop, daemon=True)
    background_thread.start()
    print("[Background] Background thread started")


def stop_background_processing():
    """Stop the background processing thread."""
    global background_running

    background_running = False
    if background_thread:
        print("[Background] Stopping background thread...")
        # Wait a bit for thread to finish
        time.sleep(0.5)


# =============================================================================
# Independent Snapshot Analysis (1 frame per 1.5 seconds)
# =============================================================================

def snapshot_analysis_loop():
    """
    Independent snapshot analysis thread.
    Analyzes high-quality frames every 1.5 seconds and saves snapshot with overlays.
    Completely independent from video streaming.
    """
    global snapshot_running, video_stream_cache, current_source, latest_snapshot_path

    print("[Snapshot] Starting independent snapshot analysis thread...")
    snapshot_running = True
    analysis_interval = 1.5  # Process every 1.5 seconds

    while snapshot_running:
        try:
            # Check if we have an active stream
            if not video_stream_cache:
                time.sleep(1)
                continue

            # Get high-quality frame
            frame = video_stream_cache.get_frame()
            if frame is None:
                time.sleep(0.5)
                continue

            # Enhance frame for better detection
            enhanced_frame = enhance_frame_for_detection(frame)

            # Detect persons
            persons = detector.detect_immediate(enhanced_frame)

            # Draw overlays if persons detected
            if persons and len(persons) > 0:
                overlay_frame = enhanced_frame.copy()
                tracked_persons = person_tracker.update(persons)

                # Draw overlays for each person
                for track in tracked_persons:
                    x1, y1, x2, y2 = [int(v) for v in track.person_bbox]

                    # Recognize face if database has faces
                    if len(database._encodings) > 0:
                        person_region = enhanced_frame[max(0, y1):min(enhanced_frame.shape[0], y2),
                                                       max(0, x1):min(enhanced_frame.shape[1], x2)]

                        if person_region.size > 0:
                            match_result = enhanced_recognizer.detect_and_recognize(
                                person_region,
                                database._encodings,
                                [meta["name"] for meta in database._metadata],
                                model="cnn" if torch.cuda.is_available() else "hog"
                            )

                            if match_result:
                                track.name = match_result.get("name", "Unknown")
                                track.face_confidence = match_result.get("confidence", 0.0)
                                track.status = "Known" if track.name != "Unknown" else "Unknown"

                                # AUTO-MARK ATTENDANCE for recognized persons
                                if track.status == "Known" and track.name != "Unknown":
                                    # Get person_id from database metadata
                                    person_id = None
                                    for i, meta in enumerate(database._metadata):
                                        if meta["name"] == track.name:
                                            person_id = meta.get("person_id", f"ID_{track.name.replace(' ', '_')}")
                                            break

                                    if person_id:
                                        # Mark attendance automatically
                                        attendance_result = attendance_system.mark_attendance(
                                            person_id=person_id,
                                            person_name=track.name,
                                            confidence=track.face_confidence,
                                            source=current_source or "snapshot_analysis",
                                            marked_by="auto",
                                            metadata={
                                                "track_id": track.track_id,
                                                "detection_method": "snapshot_analysis"
                                            }
                                        )

                                        if attendance_result.get('success'):
                                            print(f"[Attendance] Auto-marked for {track.name} ({person_id})")

                                    # Log detection event
                                    attendance_system.log_detection(
                                        person_id=person_id,
                                        person_name=track.name,
                                        confidence=track.face_confidence,
                                        source=current_source or "snapshot_analysis",
                                        metadata={"track_id": track.track_id}
                                    )

                    # Choose color based on status
                    color = (0, 255, 0) if track.status == "Known" else (255, 165, 0)

                    # Draw ellipse
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    radius_x = int((x2 - x1) / 2)
                    radius_y = int((y2 - y1) / 2)

                    cv2.ellipse(overlay_frame, (center_x, center_y), (radius_x, radius_y),
                               0, 0, 360, color, 3)

                    # Draw label
                    label = track.name if hasattr(track, 'name') and track.name else "Unknown"
                    if hasattr(track, 'face_confidence') and track.face_confidence > 0:
                        label += f" ({track.face_confidence*100:.0f}%)"

                    (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    label_x = center_x - label_w // 2
                    label_y = max(20, y1 - 10)

                    cv2.rectangle(overlay_frame,
                                 (label_x - 5, label_y - label_h - 5),
                                 (label_x + label_w + 5, label_y + 5),
                                 color, -1)
                    cv2.putText(overlay_frame, label, (label_x, label_y),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            else:
                overlay_frame = enhanced_frame

            # Save main snapshot
            snapshot_path = BACKEND_DIR / "data" / "analysis_snapshot.jpg"
            cv2.imwrite(str(snapshot_path), overlay_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            latest_snapshot_path = str(snapshot_path)

            # Save to history with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            history_filename = f"snapshot_history_{timestamp}.jpg"
            history_path = BACKEND_DIR / "data" / history_filename

            # Resize to thumbnail (1/4 size for 2x2 grid)
            thumbnail = cv2.resize(overlay_frame, (overlay_frame.shape[1]//4, overlay_frame.shape[0]//4))
            cv2.imwrite(str(history_path), thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 85])

            # Add to history list (keep only last 4)
            snapshot_history.append({
                "filename": history_filename,
                "timestamp": timestamp,
                "path": str(history_path)
            })

            # Remove old snapshots if exceeds limit
            while len(snapshot_history) > MAX_SNAPSHOT_HISTORY:
                old_snapshot = snapshot_history.pop(0)
                # Delete old file
                try:
                    Path(old_snapshot["path"]).unlink(missing_ok=True)
                except Exception as e:
                    print(f"[Snapshot] Error deleting old snapshot: {e}")

            # Wait for next analysis
            time.sleep(analysis_interval)

        except Exception as e:
            print(f"[Snapshot] Error: {e}")
            time.sleep(1)

    print("[Snapshot] Snapshot analysis thread stopped")


def start_snapshot_analysis():
    """Start the independent snapshot analysis thread."""
    global snapshot_thread, snapshot_running

    if snapshot_thread and snapshot_thread.is_alive():
        print("[Snapshot] Already running")
        return

    snapshot_thread = threading.Thread(target=snapshot_analysis_loop, daemon=True)
    snapshot_thread.start()
    print("[Snapshot] Snapshot analysis thread started")


def stop_snapshot_analysis():
    """Stop the snapshot analysis thread."""
    global snapshot_running

    snapshot_running = False
    if snapshot_thread:
        print("[Snapshot] Stopping snapshot analysis thread...")
        time.sleep(0.5)


# --------------------------------------------------------------------------- #
# Utility helpers
# --------------------------------------------------------------------------- #
def camera_source(value: str) -> Union[int, str]:
    return int(value) if value.isdigit() else value


def decode_image(payload: str) -> Optional[np.ndarray]:
    if not payload:
        return None
    if "," in payload:
        payload = payload.split(",", 1)[1]
    try:
        image_bytes = base64.b64decode(payload)
    except base64.binascii.Error:
        return None
    array = np.frombuffer(image_bytes, np.uint8)
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


def slugify(text: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in text).strip("_")


def register_event(name: str, confidence: float) -> None:
    entry = {
        "id": uuid.uuid4().hex,
        "name": name,
        "confidence": confidence,
        "timestamp": datetime.utcnow().isoformat(),
    }
    recent_events.append(entry)


def process_face_region(args: Tuple) -> Optional[Dict]:
    """Process a single face region in parallel."""
    region, person, x1, y1, x2, y2 = args
    
    faces = recognizer.extract(region)
    results = []
    
    for face in faces:
        fx1, fy1, fx2, fy2 = face["bbox"]
        global_bbox = [x1 + fx1, y1 + fy1, x1 + fx2, y1 + fy2]
        encoding = face["encoding"]
        
        match = database.match(encoding)
        if match:
            name = match["name"]
            confidence = recognizer.distance_to_confidence(match["distance"])
        else:
            name = "Unknown"
            confidence = 0.0
        
        results.append({
            "person_bbox": [x1, y1, x2, y2],
            "face_bbox": global_bbox,
            "person_confidence": round(person["confidence"], 3),
            "name": name,
            "match_confidence": confidence,
        })
        
        if name != "Unknown" and confidence > 0.7:
            register_event(name, confidence)
    
    return results


def process_frame_gpu(frame: np.ndarray) -> Tuple[List[Dict[str, object]], np.ndarray]:
    """Process frame with maximum GPU utilization."""
    # Run person detection on GPU
    detections = detector.detect_immediate(frame)
    overlay = frame.copy()
    
    # Prepare regions for parallel processing
    face_tasks = []
    for person in detections:
        x1, y1, x2, y2 = [int(v) for v in person["bbox"]]
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (71, 138, 201), 2)
        region = frame[y1:y2, x1:x2]
        if region.size > 0:
            face_tasks.append((region, person, x1, y1, x2, y2))
    
    # Process faces in parallel
    all_results = []
    if face_tasks:
        # Use thread pool for CPU-bound face recognition
        futures = [executor.submit(process_face_region, task) for task in face_tasks]
        for future in concurrent.futures.as_completed(futures):
            try:
                results = future.result(timeout=0.1)
                if results:
                    all_results.extend(results)
            except Exception as e:
                print(f"Face processing error: {e}")
    
    # Draw results
    for result in all_results:
        global_bbox = result["face_bbox"]
        name = result["name"]
        confidence = result["match_confidence"]
        
        color = (18, 200, 90) if name != "Unknown" else (255, 100, 100)
        cv2.rectangle(
            overlay,
            (global_bbox[0], global_bbox[1]),
            (global_bbox[2], global_bbox[3]),
            color,
            2,
        )
        
        label = f"{name} ({confidence:.2f})"
        cv2.putText(
            overlay,
            label,
            (global_bbox[0], max(global_bbox[1] - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
        )
    
    return all_results, overlay


def save_face_image(image: np.ndarray, name: str) -> Path:
    filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{slugify(name)}.jpg"
    output_path = BACKEND_DIR / "faces" / filename
    cv2.imwrite(str(output_path), image)
    return output_path


# --------------------------------------------------------------------------- #
# Video streaming utilities
# --------------------------------------------------------------------------- #
def get_video_stream(source: Union[int, str]) -> EnhancedVideoStream:
    """Get or create video stream for given source."""
    global video_stream_cache, current_source

    # Parse source (convert "0" to 0, etc.)
    parsed_source = parse_source(str(source))

    with stream_lock:
        # Check if we need to create a new stream
        if (
            video_stream_cache is None
            or video_stream_cache.source_info.source != parsed_source
        ):
            # Stop old stream if exists
            if video_stream_cache is not None:
                print(f"[INFO] Switching video source from {current_source} to {source}")
                video_stream_cache.stop()
                time.sleep(0.5)  # Brief delay for cleanup

            # Create new stream with auto-downscaling
            video_stream_cache = EnhancedVideoStream(
                source=parsed_source,
                reconnect_delay=5.0,
                max_reconnect_attempts=0,  # Infinite reconnect attempts
                buffer_size=1,
                max_width=1280,  # Auto-downscale to max 1280x720
                max_height=720
            )
            current_source = str(source)

        return video_stream_cache


# --------------------------------------------------------------------------- #
# API endpoints
# --------------------------------------------------------------------------- #
@app.route("/api/health", methods=["GET"])
async def health() -> Response:
    gpu_available = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if gpu_available else "None"

    # Get stream status
    stream_status = None
    if video_stream_cache:
        stream_status = video_stream_cache.get_status()

    return {
        "status": "ok",
        "time": datetime.utcnow().isoformat(),
        "faces": database.count,
        "model": "YOLOv8n + dlib",  # Updated to show nano model
        "gpu": gpu_available,
        "gpu_name": gpu_name,
        "cuda_version": torch.version.cuda if gpu_available else None,
        "current_source": current_source,
        "stream_status": stream_status,
    }


@app.route("/api/sources/current", methods=["GET"])
async def get_current_source() -> Response:
    """Get current video source information."""
    global video_stream_cache, current_source

    if video_stream_cache:
        status = video_stream_cache.get_status()
        return {
            "success": True,
            "source": current_source,
            "status": status
        }
    else:
        return {
            "success": False,
            "source": current_source,
            "status": {"connected": False}
        }


@app.route("/api/sources/change", methods=["POST"])
async def change_source() -> Response:
    """Change video source and reset all processing state."""
    global video_stream_cache, current_source, person_tracker

    payload = await request.get_json(silent=True) or {}
    new_source = payload.get("source", "").strip()
    should_reset = payload.get("reset", True)  # Default to True for clean switch

    if not new_source:
        return {"success": False, "message": "Source is required"}, 400

    # Validate source before switching
    is_valid, error_msg = validate_source(parse_source(new_source))
    if not is_valid:
        return {"success": False, "message": error_msg}, 400

    try:
        print(f"[Source Change] Switching from '{current_source}' to '{new_source}'")

        # STEP 1: Stop old stream
        if video_stream_cache:
            print("[Source Change] Stopping old video stream...")
            video_stream_cache.stop()
            video_stream_cache = None

        # STEP 2: Reset all processing state if requested
        if should_reset:
            print("[Source Change] Resetting all processing state...")

            # Reset tracker - clear all active tracks
            if person_tracker:
                person_tracker.tracks = []
                print("[Source Change] Tracker cleared")

            # Reset recognizer - clear face tracking cache
            if recognizer:
                recognizer.face_tracks = {}
                recognizer.last_cleanup = time.time()
                print("[Source Change] Recognizer face tracks cleared")

            # Clear any processing queues or buffers
            # (Add more resets here if needed for other components)

        print("[Source Change] State reset complete")

        # STEP 3: Create new stream
        print(f"[Source Change] Creating new stream for: {new_source}")
        get_video_stream(new_source)

        # STEP 4: Start background processing and snapshot analysis
        stream_state.set_active(new_source, "rtsp" if "rtsp://" in new_source.lower() else "webcam")
        start_background_processing()
        start_snapshot_analysis()
        print("[Source Change] Background processing and snapshot analysis enabled")

        return {
            "success": True,
            "message": f"Switched to source: {new_source}",
            "source": new_source,
            "reset": should_reset,
            "background_processing": True
        }

    except Exception as e:
        print(f"[Source Change] Error: {e}")
        return {"success": False, "message": str(e)}, 500


@app.route("/api/sources/validate", methods=["POST"])
async def validate_source_endpoint() -> Response:
    """Validate if a video source is accessible."""
    payload = await request.get_json(silent=True) or {}
    source = payload.get("source", "").strip()

    if not source:
        return {"success": False, "message": "Source is required"}, 400

    is_valid, message = validate_source(parse_source(source))

    return {
        "success": True,
        "valid": is_valid,
        "message": message,
        "source": source
    }


@app.route("/api/register", methods=["POST"])
async def register_face() -> Response:
    payload = await request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    person_id = (payload.get("person_id") or "").strip()
    image_data = payload.get("image")

    if not name or not image_data:
        return {"success": False, "message": "Name and image are required."}, 400

    if not person_id:
        return {"success": False, "message": "Person ID is required."}, 400

    frame = decode_image(image_data)
    if frame is None:
        return {"success": False, "message": "Invalid image payload."}, 400

    # Fast face detection for registration (no upsampling)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    locations = face_recognition.face_locations(rgb, number_of_times_to_upsample=0, model="hog")

    if not locations:
        return {"success": False, "message": "No face detected."}, 422

    # Get encodings for detected faces
    encodings = face_recognition.face_encodings(rgb, locations)
    if not encodings:
        return {"success": False, "message": "Could not encode face."}, 422

    # Use the most prominent face (first detection)
    encoding = encodings[0]
    top, right, bottom, left = locations[0]

    # Extract face image
    face_image = frame[top:bottom, left:right]
    if face_image.size == 0:
        face_image = frame

    image_path = save_face_image(face_image, name)
    entry = database.add_face(name=name, encoding=encoding, image_path=image_path, person_id=person_id)

    # ⚡ CRITICAL: Update recognizer's known face lists immediately
    recognizer.known_face_encodings.append(encoding)
    recognizer.known_face_names.append(name)

    # Register person in attendance system
    attendance_system.add_person(
        person_id=person_id,
        name=name,
        face_encoding_path=str(BACKEND_DIR / "data" / f"{name}.npy"),
        face_image_path=image_path,
        metadata={"registered_via": "web_interface"}
    )

    print(f"[INFO] Registered new face: {name} (ID: {person_id})")
    print(f"[INFO] Total known faces: {len(recognizer.known_face_encodings)}")

    return {"success": True, "face": entry, "count": database.count}


@app.route("/api/recognize", methods=["POST"])
async def recognize_frame() -> Response:
    DEBUG = True  # Enable debugging for this endpoint

    payload = await request.get_json(silent=True) or {}
    image_data = payload.get("image")

    # If no image data provided (remote source like RTSP), get frame from video stream
    if not image_data or image_data == "":
        stream = get_video_stream(current_source)
        frame = stream.get_frame()

        if frame is None:
            if DEBUG:
                print("[DEBUG] No frame available from video stream")
            return {"success": False, "message": "No frame available from stream."}, 400

        if DEBUG:
            print(f"[DEBUG] Got frame from video stream: {frame.shape}")
    else:
        # Decode image from frontend (webcam)
        frame = decode_image(image_data)
        if frame is None:
            if DEBUG:
                print("[DEBUG] Failed to decode image data")
            return {"success": False, "message": "Invalid frame data."}, 400

    if DEBUG:
        print(f"[DEBUG] Processing frame with shape: {frame.shape}")

    # Step 0: Enhance frame for better detection at angles/distances
    enhanced_frame = enhance_frame_for_detection(frame)

    # Step 1: Detect persons with YOLO (use enhanced frame)
    detections = detector.detect_immediate(enhanced_frame)

    if DEBUG:
        print(f"[DEBUG] Detected {len(detections)} persons")

    # Step 2: Update tracker with person detections (assigns persistent IDs)
    tracked_persons = person_tracker.update(detections)

    if DEBUG:
        print(f"[DEBUG] Tracking {len(tracked_persons)} persons")

    # Step 3: Enhanced face recognition with distance/angle robustness
    current_time = time.time()

    for track in tracked_persons:
        # Skip if face was recently recognized (within 1 second)
        if track.face_last_seen > 0 and (current_time - track.face_last_seen) < 1.0:
            continue

        # Skip if track already confirmed as Known
        if track.status == "Known" and track.name != "Unknown":
            continue

        x1, y1, x2, y2 = [int(v) for v in track.person_bbox]

        # Extract person region from enhanced frame
        person_region = enhanced_frame[max(0, y1):min(enhanced_frame.shape[0], y2),
                                      max(0, x1):min(enhanced_frame.shape[1], x2)]

        if person_region.size == 0:
            continue

        # Use enhanced recognizer (handles distance, angles, lighting)
        result = enhanced_recognizer.detect_and_recognize(
            person_region,
            recognizer.known_face_encodings,
            recognizer.known_face_names,
            model="hog"
        )

        if result:
            if DEBUG:
                print(f"[DEBUG] Track {track.track_id}: Detected face (quality={result['quality']:.2f})")
                if result['name'] != "Unknown":
                    print(f"[DEBUG] Track {track.track_id}: Recognized as {result['name']} ({result['confidence']:.3f})")

            # Convert local face bbox to global coordinates
            face_bbox_local = result['face_bbox']
            global_face_bbox = [
                max(0, x1 + face_bbox_local[0]),
                max(0, y1 + face_bbox_local[1]),
                min(enhanced_frame.shape[1], x1 + face_bbox_local[2]),
                min(enhanced_frame.shape[0], y1 + face_bbox_local[3])
            ]

            # Update tracker with recognition data
            person_tracker.update_face_recognition(
                track.track_id,
                global_face_bbox,
                result['name'],
                result['confidence'],
                result.get('person_id', '')
            )

            # Register events for recognized persons
            if result['name'] != "Unknown" and result['confidence'] > 0.65:
                register_event(result['name'], result['confidence'])

    # Step 4: Prepare results for frontend
    results = []
    for track in tracked_persons:
        result = {
            "track_id": track.track_id,
            "person_bbox": [float(x) for x in track.person_bbox],
            "person_confidence": float(track.confidence),
            "face_bbox": [float(x) for x in track.face_bbox] if track.face_bbox else None,
            "name": track.name,
            "person_id": track.person_id,  # Include person ID
            "face_confidence": float(track.face_confidence),
            "status": track.status,
            "frames_tracked": track.frames_tracked,
            "color": track.get_color()  # RGB tuple
        }
        results.append(result)

        # Store detection in history database (only for known persons to avoid spam)
        if track.status == "Known" and track.name != "Unknown":
            try:
                detection_history.add_detection(
                    person_name=track.name,
                    person_id=track.person_id,
                    confidence=track.face_confidence,
                    status=track.status,
                    track_id=track.track_id,
                    bbox=[float(x) for x in track.person_bbox],
                    source=current_source,
                    metadata={
                        "frames_tracked": track.frames_tracked,
                        "face_bbox": [float(x) for x in track.face_bbox] if track.face_bbox else None
                    }
                )
            except Exception as e:
                print(f"[Detection Storage] Error storing detection: {e}")

    if DEBUG:
        print(f"[DEBUG] Returning {len(results)} tracked persons to frontend")

    return {
        "success": True,
        "timestamp": datetime.utcnow().isoformat(),
        "results": results,
        "active_tracks": len(person_tracker.tracked_persons)
    }


@app.route("/api/stream", methods=["GET"])
async def stream() -> Response:
    """
    RTSP/Remote stream endpoint - OPTIMIZED for performance.
    Just streams raw frames without any AI processing.
    Frontend will handle detection/recognition via /api/recognize endpoint.
    """
    source_param = request.args.get("source", DEFAULT_CAMERA_SOURCE)
    source = camera_source(source_param)

    try:
        video_stream = get_video_stream(source)
    except RuntimeError as exc:
        return await jsonify({"success": False, "message": str(exc)}), 500

    async def generate():
        """Ultra-lightweight stream - just grab and encode frames"""
        print("[Stream] Starting RTSP stream (no processing mode)")
        frame_count = 0

        try:
            while True:
                # Get frame (fast)
                frame = video_stream.get_frame()
                if frame is None:
                    await asyncio.sleep(0.033)  # ~30 FPS
                    continue

                frame_count += 1

                # Encode directly without any processing (very fast!)
                success, buffer = cv2.imencode(".jpg", frame,
                                              [cv2.IMWRITE_JPEG_QUALITY, 80])
                if not success:
                    continue

                jpg_bytes = buffer.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpg_bytes + b"\r\n"
                )

                # Minimal delay to prevent overload
                await asyncio.sleep(0.033)  # ~30 FPS

        except GeneratorExit:
            print(f"[Stream] Client disconnected after {frame_count} frames")
        except Exception as e:
            print(f"[Stream] Stream error: {e}")

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/clear", methods=["DELETE"])
async def clear_faces() -> Response:
    # Clear face database (faces.pkl)
    database.clear()

    # Clear face images
    for image_file in (BACKEND_DIR / "faces").glob("*.jpg"):
        image_file.unlink(missing_ok=True)

    # Clear persons from attendance database
    import sqlite3
    db_path = BACKEND_DIR / "data" / "attendance.db"
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM persons")
        conn.commit()
        conn.close()
        logger.info("Cleared all persons from attendance database")

    # Clear in-memory recognizer data
    recognizer.known_face_encodings.clear()
    recognizer.known_face_names.clear()

    return {"success": True, "message": "Database cleared (faces, persons, and in-memory data)."}


@app.route("/api/faces", methods=["GET"])
async def faces() -> Response:
    # Force reload from disk to fix worker process state issue
    database._load()
    return {"faces": database.list_faces()}


@app.route("/api/persons", methods=["GET"])
async def persons_list() -> Response:
    """
    List all persons from attendance system (no auth required for web console).
    This is separate from /api/v1/persons which requires authentication.
    """
    try:
        # Get all persons from attendance system
        persons = attendance_system.list_persons(status=None)

        return {
            "success": True,
            "persons": persons,
            "total": len(persons)
        }
    except Exception as e:
        logger.error(f"Error listing persons: {e}")
        return {
            "success": False,
            "error": str(e),
            "persons": []
        }, 500


@app.route("/api/snapshot", methods=["GET"])
async def get_snapshot() -> Response:
    """Serve the latest analysis snapshot image."""
    try:
        snapshot_path = BACKEND_DIR / "data" / "analysis_snapshot.jpg"

        if not snapshot_path.exists():
            return {"success": False, "message": "No snapshot available yet"}, 404

        return await send_from_directory(
            str(snapshot_path.parent),
            snapshot_path.name,
            mimetype='image/jpeg'
        )
    except Exception as e:
        print(f"[Snapshot API] Error: {e}")
        return {"success": False, "message": str(e)}, 500


@app.route("/api/snapshot/history", methods=["GET"])
async def get_snapshot_history() -> Response:
    """Get list of snapshot history thumbnails."""
    try:
        # Return the history list (most recent first)
        history_list = [
            {
                "filename": item["filename"],
                "timestamp": item["timestamp"]
            }
            for item in reversed(snapshot_history)  # Most recent first
        ]

        return {"success": True, "history": history_list}
    except Exception as e:
        print(f"[Snapshot History API] Error: {e}")
        return {"success": False, "message": str(e)}, 500


@app.route("/api/snapshot/history/<filename>", methods=["GET"])
async def get_snapshot_history_file(filename: str) -> Response:
    """Serve a specific snapshot history thumbnail."""
    try:
        # Validate filename to prevent directory traversal
        if not filename.startswith("snapshot_history_"):
            return {"success": False, "message": "Invalid filename"}, 400

        file_path = BACKEND_DIR / "data" / filename

        if not file_path.exists():
            return {"success": False, "message": "Snapshot not found"}, 404

        return await send_from_directory(
            str(file_path.parent),
            file_path.name,
            mimetype='image/jpeg'
        )
    except Exception as e:
        print(f"[Snapshot History File API] Error: {e}")
        return {"success": False, "message": str(e)}, 500


@app.route("/api/events", methods=["GET"])
async def events() -> Response:
    return {"events": list(recent_events)[-EVENT_LIMIT:]}


# --------------------------------------------------------------------------- #
# Frontend routes
# --------------------------------------------------------------------------- #
@app.route("/faces/<path:filename>")
async def face_file(filename: str):
    return await send_from_directory(str(BACKEND_DIR / "faces"), filename)


@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
async def frontend(path: str):
    target = FRONTEND_DIR / path
    if target.exists():
        return await send_from_directory(str(FRONTEND_DIR), path)
    return await send_from_directory(str(FRONTEND_DIR), "index.html")


# --------------------------------------------------------------------------- #
# Cleanup
# --------------------------------------------------------------------------- #
def cleanup():
    """Cleanup resources on exit."""
    print("Cleaning up resources...")
    detector.stop()
    executor.shutdown(wait=False)
    if video_stream_cache:
        video_stream_cache.stop()


import atexit
atexit.register(cleanup)


# --------------------------------------------------------------------------- #
# Entry point with async support
# --------------------------------------------------------------------------- #
# =============================================================================
# Detection History API Endpoints
# =============================================================================

@app.route("/api/detections", methods=["GET"])
async def get_detections() -> Response:
    """Get all detection records with optional filtering."""
    try:
        # Get query parameters
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))
        person_name = request.args.get("person_name")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        detections = detection_history.get_all_detections(
            limit=limit,
            offset=offset,
            person_name=person_name,
            start_date=start_date,
            end_date=end_date
        )

        return {
            "success": True,
            "detections": detections,
            "count": len(detections)
        }
    except Exception as e:
        print(f"[Detection API] Error getting detections: {e}")
        return {"success": False, "message": str(e)}, 500


@app.route("/api/detections/<int:detection_id>", methods=["GET"])
async def get_detection(detection_id: int) -> Response:
    """Get a single detection record by ID."""
    try:
        detection = detection_history.get_detection_by_id(detection_id)

        if detection:
            return {"success": True, "detection": detection}
        else:
            return {"success": False, "message": "Detection not found"}, 404

    except Exception as e:
        print(f"[Detection API] Error getting detection: {e}")
        return {"success": False, "message": str(e)}, 500


@app.route("/api/detections/<int:detection_id>", methods=["PUT"])
async def update_detection(detection_id: int) -> Response:
    """Update a detection record."""
    try:
        payload = await request.get_json(silent=True) or {}
        success = detection_history.update_detection(detection_id, payload)

        if success:
            return {"success": True, "message": "Detection updated successfully"}
        else:
            return {"success": False, "message": "Detection not found or update failed"}, 404

    except Exception as e:
        print(f"[Detection API] Error updating detection: {e}")
        return {"success": False, "message": str(e)}, 500


@app.route("/api/detections/<int:detection_id>", methods=["DELETE"])
async def delete_detection(detection_id: int) -> Response:
    """Delete a detection record."""
    try:
        success = detection_history.delete_detection(detection_id)

        if success:
            return {"success": True, "message": "Detection deleted successfully"}
        else:
            return {"success": False, "message": "Detection not found"}, 404

    except Exception as e:
        print(f"[Detection API] Error deleting detection: {e}")
        return {"success": False, "message": str(e)}, 500


@app.route("/api/detections", methods=["DELETE"])
async def delete_all_detections() -> Response:
    """Delete all detection records."""
    try:
        count = detection_history.delete_all_detections()
        return {
            "success": True,
            "message": f"Deleted {count} detection records",
            "count": count
        }
    except Exception as e:
        print(f"[Detection API] Error deleting all detections: {e}")
        return {"success": False, "message": str(e)}, 500


@app.route("/api/detections/statistics", methods=["GET"])
async def get_detection_statistics() -> Response:
    """Get detection statistics."""
    try:
        stats = detection_history.get_statistics()
        return {"success": True, "statistics": stats}
    except Exception as e:
        print(f"[Detection API] Error getting statistics: {e}")
        return {"success": False, "message": str(e)}, 500


# =============================================================================
# Background Processing API Endpoints
# =============================================================================

@app.route("/api/background/status", methods=["GET"])
async def get_background_status() -> Response:
    """Get background processing status."""
    try:
        stream_info = stream_state.get_state()
        return {
            "success": True,
            "background_running": background_running,
            "stream_active": stream_info.get("active", False),
            "current_source": stream_info.get("source"),
            "source_type": stream_info.get("source_type"),
            "thread_alive": background_thread.is_alive() if background_thread else False
        }
    except Exception as e:
        print(f"[Background API] Error getting status: {e}")
        return {"success": False, "message": str(e)}, 500


@app.route("/api/background/start", methods=["POST"])
async def start_background() -> Response:
    """Manually start background processing."""
    try:
        if not video_stream_cache:
            return {"success": False, "message": "No active video stream"}, 400

        start_background_processing()
        return {
            "success": True,
            "message": "Background processing started",
            "background_running": background_running
        }
    except Exception as e:
        print(f"[Background API] Error starting: {e}")
        return {"success": False, "message": str(e)}, 500


@app.route("/api/background/stop", methods=["POST"])
async def stop_background() -> Response:
    """Manually stop background processing."""
    try:
        stop_background_processing()
        stream_state.set_inactive()
        return {
            "success": True,
            "message": "Background processing stopped"
        }
    except Exception as e:
        print(f"[Background API] Error stopping: {e}")
        return {"success": False, "message": str(e)}, 500



# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"  # Disable debug for performance

    # Print GPU info
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"CUDA Version: {torch.version.cuda}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

    # Auto-restore previous stream state on startup
    if stream_state.is_active():
        previous_source = stream_state.get_source()
        print(f"\n[Auto-Restore] Found active stream from previous session: {previous_source}")
        try:
            # Recreate stream
            get_video_stream(previous_source)
            # Start background processing and snapshot analysis
            start_background_processing()
            start_snapshot_analysis()
            print("[Auto-Restore] Stream, background processing, and snapshot analysis restored successfully")
        except Exception as e:
            print(f"[Auto-Restore] Failed to restore stream: {e}")
            stream_state.set_inactive()

    # Use hypercorn for better async performance
    from hypercorn.config import Config
    from hypercorn.asyncio import serve

    config = Config()
    config.bind = ["0.0.0.0:5000"]
    config.use_reloader = debug_mode
    config.workers = 1  # Single worker for GPU access

    import asyncio
    asyncio.run(serve(app, config))