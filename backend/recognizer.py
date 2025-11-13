"""
Face recognition helpers built on top of the face_recognition package with async support.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Dict, List, Optional, Set
import queue
import time

import cv2
import face_recognition
import numpy as np
from dataclasses import dataclass

@dataclass
class TrackedPerson:
    """Person tracking information."""
    track_id: int
    person_bbox: List[float]  # [x1, y1, x2, y2]
    face_bbox: Optional[List[float]] = None
    name: str = "Unknown"
    confidence: float = 0.0
    last_seen: float = 0.0
    is_recognized: bool = False


class FaceRecognitionEngine:
    """Encapsulates face location, encoding, and confidence helpers with tracking."""

    def __init__(
        self, 
        model: str = "hog",  # Use HOG for CPU, CNN for GPU 
        upsample_times: int = 2,  # Increased for better detection
        tracking_ttl: float = 2.0,  # How long to keep tracking a person
        max_trackers: int = 20,  # Reduced for better performance
        batch_size: int = 8,   # Increased for better throughput
        debug: bool = True     # Enable debug logging
    ) -> None:
        """Initialize face recognition engine."""
        self.model = model
        self.upsample_times = upsample_times
        self.tracking_ttl = tracking_ttl
        self.max_trackers = max_trackers
        self.batch_size = batch_size
        self.debug = debug

        # Initialize known face encodings
        self.known_face_encodings = []
        self.known_face_names = []
        
        print(f"[DEBUG] Initializing FaceRecognitionEngine:")
        print(f"[DEBUG] - Model: {model}")
        print(f"[DEBUG] - Upsample times: {upsample_times}")
        print(f"[DEBUG] - Tracking TTL: {tracking_ttl}")
        print(f"[DEBUG] - Max trackers: {max_trackers}")
        print(f"[DEBUG] - Batch size: {batch_size}")
        
        # Tracking state
        self.next_track_id = 1
        self.tracked_persons: Dict[int, TrackedPerson] = {}
        self.trackers = cv2.legacy.MultiTracker_create()
        
        # Async processing queues
        self.face_queue = queue.Queue(maxsize=batch_size * 2)
        self.result_queue = queue.Queue()
        
        # Start worker threads
        self.running = True
        self.face_thread = threading.Thread(target=self._face_processor, daemon=True)
        self.face_thread.start()

    async def process_frame(
        self, 
        frame: np.ndarray,
        person_detections: List[Dict[str, float]]
    ) -> List[TrackedPerson]:
        """Process a frame with person detections asynchronously."""
        if frame is None or not person_detections:
            if self.debug:
                print("[DEBUG] Empty frame or no detections")
            return []
            
        if self.debug:
            print(f"[DEBUG] Processing frame with {len(person_detections)} detections")
            print(f"[DEBUG] Frame shape: {frame.shape}")
            for i, det in enumerate(person_detections):
                print(f"[DEBUG] Detection {i}: bbox={det['bbox']}, conf={det['confidence']:.2f}")
            
        # Update existing trackers
        success, boxes = self.trackers.update(frame)
        current_time = time.time()
        
        # Remove old tracks
        self.tracked_persons = {
            tid: track for tid, track in self.tracked_persons.items()
            if current_time - track.last_seen <= self.tracking_ttl
        }
        
        # Update tracked persons with new positions
        if success:
            for tid, box in zip(self.tracked_persons.keys(), boxes):
                if tid in self.tracked_persons:
                    x, y, w, h = box
                    self.tracked_persons[tid].person_bbox = [x, y, x+w, y+h]
                    self.tracked_persons[tid].last_seen = current_time

        # Process new detections
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        processed: Set[int] = set()
        
        for person in person_detections:
            bbox = person["bbox"]
            conf = person["confidence"]
            
            # Check if detection matches existing track
            matched = False
            for track in self.tracked_persons.values():
                if self._box_iou(bbox, track.person_bbox) > 0.5:
                    track.person_bbox = bbox
                    track.last_seen = current_time
                    processed.add(track.track_id)
                    matched = True
                    break
            
            if not matched and len(self.tracked_persons) < self.max_trackers:
                # Create new tracker
                x1, y1, x2, y2 = bbox
                tracker = cv2.legacy.TrackerCSRT_create()
                ok = tracker.init(frame, (x1, y1, x2-x1, y2-y1))
                if ok:
                    track_id = self.next_track_id
                    self.next_track_id += 1
                    self.tracked_persons[track_id] = TrackedPerson(
                        track_id=track_id,
                        person_bbox=bbox,
                        last_seen=current_time
                    )
                    self.trackers.add(tracker, frame, (x1, y1, x2-x1, y2-y1))
        
                        # Queue face detection with adaptive rate limiting
                current_faces = 0
                for track in self.tracked_persons.values():
                    # Shorter delay for unrecognized faces to improve responsiveness
                    delay = 0.2 if not track.is_recognized else 0.5
                    
                    # Skip if recently processed
                    if hasattr(track, 'last_face_check') and \
                       current_time - track.last_face_check < delay:
                        continue
                        
                    try:
                        x1, y1, x2, y2 = [int(v) for v in track.person_bbox]
                        region = frame[y1:y2, x1:x2]
                        if region.size > 0:
                            self.face_queue.put((track.track_id, region), timeout=0.01)
                            track.last_face_check = current_time
                            current_faces += 1
                            if current_faces >= 3:  # Limit faces per frame
                                break
                    except queue.Full:
                        break

        # Get face recognition results
        try:
            while True:
                track_id, face_data = self.result_queue.get_nowait()
                if track_id in self.tracked_persons:
                    track = self.tracked_persons[track_id]
                    track.face_bbox = face_data["bbox"]
                    track.name = face_data["name"]
                    track.confidence = face_data["confidence"]
                    track.is_recognized = track.name != "Unknown"
        except queue.Empty:
            pass

        return list(self.tracked_persons.values())

    def _face_processor(self):
        """Background thread for face detection and recognition."""
        face_cache = {}  # Simple LRU cache for face encodings
        MAX_CACHE_SIZE = 100
        
        while self.running:
            batch_regions = []
            batch_ids = []
            
            # Collect frames for batch processing
            deadline = time.time() + 0.1  # Increased collection window
            while len(batch_regions) < self.batch_size and time.time() < deadline:
                try:
                    track_id, region = self.face_queue.get(timeout=0.01)
                    # Skip if we recently processed this track
                    if track_id in face_cache and \
                       time.time() - face_cache[track_id]["time"] < 1.0:
                        continue
                    batch_regions.append(region)
                    batch_ids.append(track_id)
                except queue.Empty:
                    break
                    
            if not batch_regions:
                time.sleep(0.01)
                continue
                
            # Process faces in batch
            try:
                if batch_regions:
                    if self.debug:
                        print(f"[DEBUG] Processing batch of {len(batch_regions)} face regions")
                        
                    # Process all regions in one batch for better performance
                    all_faces = self.extract_batch(batch_regions)
                    for track_id, faces in zip(batch_ids, all_faces):
                        if faces:
                            face = faces[0]  # Use first face found
                            if self.debug:
                                print(f"[DEBUG] Track {track_id}: Found face with bbox {face['bbox']}")
                            
                            # Compare with known faces
                            if self.known_face_encodings:
                                if self.debug:
                                    print(f"[DEBUG] Comparing face with {len(self.known_face_encodings)} known faces")
                                
                                # Get matches with known faces
                                matches = face_recognition.compare_faces(self.known_face_encodings, face['encoding'], tolerance=0.6)
                                face_distances = face_recognition.face_distance(self.known_face_encodings, face['encoding'])
                                
                                if self.debug:
                                    print(f"[DEBUG] Face distances: {face_distances}")
                                
                                if True in matches:
                                    best_match_idx = face_distances.argmin()
                                    face['name'] = self.known_face_names[best_match_idx]
                                    face['confidence'] = 1.0 - min(face_distances[best_match_idx], 0.6)
                                    
                                    if self.debug:
                                        print(f"[DEBUG] Match found: {face['name']} with confidence {face['confidence']:.3f}")
                            else:
                                if self.debug:
                                    print("[DEBUG] No known faces to compare against")
                            
                            face_cache[track_id] = {
                                "face": face,
                                "time": time.time()
                            }
                            self.result_queue.put((track_id, face))
                            
                            if self.debug:
                                print(f"[DEBUG] Track {track_id}: Face data queued for recognition")
                        else:
                            if self.debug:
                                print(f"[DEBUG] Track {track_id}: No faces found in region")
                        
                        # Limit cache size
                        if len(face_cache) > MAX_CACHE_SIZE:
                            oldest = min(face_cache.items(), key=lambda x: x[1]["time"])
                            del face_cache[oldest[0]]
            except Exception as e:
                print(f"[ERROR] Face processing error: {str(e)}")
                    
    def extract_batch(self, frames: List[np.ndarray]) -> List[List[Dict[str, object]]]:
        """Process multiple frames in a single batch."""
        if not frames:
            if self.debug:
                print("[DEBUG] extract_batch: No frames to process")
            return []
            
        if self.debug:
            print(f"[DEBUG] extract_batch: Processing {len(frames)} frames")
            
        # Prepare batch of RGB images
        rgb_frames = []
        resized_frames = []
        for i, frame in enumerate(frames):
            if self.debug:
                print(f"[DEBUG] Frame {i} shape: {frame.shape}")
            
            # Ensure minimum size for face detection
            min_size = 64
            h, w = frame.shape[:2]
            scale = max(min_size / min(h, w), 1.0)
            
            if scale > 1.0:
                new_size = (int(w * scale), int(h * scale))
                if self.debug:
                    print(f"[DEBUG] Resizing frame {i} to {new_size}")
                frame = cv2.resize(frame, new_size, interpolation=cv2.INTER_LINEAR)
            
            rgb_frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            resized_frames.append(frame)
        
        # Process locations in batch
        all_locations = []
        for i, frame in enumerate(rgb_frames):
            if self.debug:
                print(f"[DEBUG] Processing face locations for frame {i}")
                print(f"[DEBUG] Frame {i} size: {frame.shape}")
            
            try:
                locations = face_recognition.face_locations(
                    frame,
                    number_of_times_to_upsample=self.upsample_times,
                    model=self.model
                )
                
                if self.debug:
                    print(f"[DEBUG] Frame {i}: Found {len(locations)} faces")
                    for j, loc in enumerate(locations):
                        print(f"[DEBUG] Face {j} location: {loc}")
                        # Draw debug rectangle on frame
                        if resized_frames is not None:
                            top, right, bottom, left = loc
                            cv2.rectangle(resized_frames[i], (left, top), (right, bottom), (0, 255, 0), 2)
                            
                all_locations.append(locations)
                
            except Exception as e:
                print(f"[ERROR] Face detection failed for frame {i}: {str(e)}")
                all_locations.append([])
                continue
        
        # Process encodings in batch
        results = []
        for i, (frame, locations) in enumerate(zip(rgb_frames, all_locations)):
            if not locations:
                results.append([])
                continue
            
            try:
                encodings = face_recognition.face_encodings(frame, locations)
                
                if self.debug:
                    print(f"[DEBUG] Frame {i}: Generated {len(encodings)} encodings for {len(locations)} faces")
                
                faces = []
                for (top, right, bottom, left), encoding in zip(locations, encodings):
                    faces.append({
                        "bbox": [int(left), int(top), int(right), int(bottom)],
                        "encoding": encoding,
                        "name": "Unknown",
                        "confidence": 0.0
                    })
                results.append(faces)
                
            except Exception as e:
                print(f"[ERROR] Face encoding failed for frame {i}: {str(e)}")
                results.append([])
            
        return results

    def extract(self, frame: np.ndarray) -> List[Dict[str, object]]:
        """Return face locations and encodings for the provided frame."""
        if frame is None:
            return []

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(
            rgb,
            number_of_times_to_upsample=self.upsample_times,
            model=self.model,
        )
        encodings = face_recognition.face_encodings(rgb, locations)

        faces: List[Dict[str, object]] = []
        for (top, right, bottom, left), encoding in zip(locations, encodings):
            faces.append({
                "bbox": [int(left), int(top), int(right), int(bottom)],
                "encoding": encoding,
                "name": "Unknown",
                "confidence": 0.0
            })
        return faces

    def stop(self):
        """Stop background processing."""
        self.running = False
        if self.face_thread.is_alive():
            self.face_thread.join(timeout=1.0)

    @staticmethod
    def distance_to_confidence(distance: float, max_distance: float = 0.6) -> float:
        """Convert a face distance into a human-friendly confidence score."""
        confidence = 1.0 - min(distance / max_distance, 1.0)
        return round(confidence, 3)

    @staticmethod
    def _box_iou(box1: List[float], box2: List[float]) -> float:
        """Calculate IoU between two bounding boxes."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        if x2 < x1 or y2 < y1:
            return 0.0
            
        intersection = (x2 - x1) * (y2 - y1)
        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = box1_area + box2_area - intersection
        
        return intersection / union if union > 0 else 0.0

