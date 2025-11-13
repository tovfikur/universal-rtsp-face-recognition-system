"""
Person tracking with ByteTrack algorithm for persistent ID assignment.
Integrates with YOLO person detection and face recognition.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import time
from collections import defaultdict


@dataclass
class TrackedPerson:
    """Represents a tracked person with persistent ID and recognition status."""
    track_id: int
    person_bbox: List[float]  # [x1, y1, x2, y2]
    confidence: float  # Person detection confidence

    # Face recognition data
    face_bbox: Optional[List[float]] = None  # [x1, y1, x2, y2]
    name: str = "—"
    person_id: str = ""  # Person ID / Badge Number
    face_confidence: float = 0.0
    status: str = "Tracking"  # "Known", "Unknown", "Tracking"

    # Tracking metadata
    last_seen: float = field(default_factory=time.time)
    frames_tracked: int = 0
    frames_lost: int = 0
    face_last_seen: float = 0.0

    def update_detection(self, bbox: List[float], conf: float):
        """Update person detection."""
        self.person_bbox = bbox
        self.confidence = conf
        self.last_seen = time.time()
        self.frames_tracked += 1
        self.frames_lost = 0

    def update_face(self, face_bbox: List[float], name: str, face_conf: float, person_id: str = ""):
        """Update face recognition data."""
        self.face_bbox = face_bbox
        self.name = name
        self.person_id = person_id
        self.face_confidence = face_conf
        self.face_last_seen = time.time()

        # Update status
        if name == "Unknown":
            self.status = "Unknown"
        elif name != "—":
            self.status = "Known"

    def mark_lost(self):
        """Mark person as lost (not detected in current frame)."""
        self.frames_lost += 1

    def get_color(self) -> Tuple[int, int, int]:
        """Get bounding box color based on status."""
        if self.status == "Known":
            return (0, 255, 0)  # Green
        elif self.status == "Unknown":
            return (255, 0, 0)  # Red
        else:  # Tracking
            return (255, 255, 0)  # Yellow


class SimpleTracker:
    """
    Simplified ByteTrack-style tracker using IoU matching.
    Maintains persistent IDs across frames.
    """

    def __init__(
        self,
        iou_threshold: float = 0.3,
        max_age: int = 3,  # Max frames to keep lost tracks (reduced from 30)
        min_hits: int = 1,   # Min detections before confirmed
        face_memory_time: float = 3.0  # Remember face for 3 seconds
    ):
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.min_hits = min_hits
        self.face_memory_time = face_memory_time

        self.next_id = 1
        self.tracked_persons: Dict[int, TrackedPerson] = {}

        print(f"[Tracker] Initialized with max_age={max_age} frames")
        print(f"[Tracker] Persons will be removed after {max_age} missed detections")

    def update(self, detections: List[Dict]) -> List[TrackedPerson]:
        """
        Update tracker with new detections.

        Args:
            detections: List of person detections with bbox and confidence

        Returns:
            List of tracked persons with persistent IDs
        """
        # Mark all existing tracks as lost initially
        for track in self.tracked_persons.values():
            track.mark_lost()

        # Convert detections to bboxes for matching
        det_boxes = []
        for det in detections:
            bbox = det["bbox"]
            conf = det["confidence"]
            det_boxes.append((bbox, conf))

        # Match detections to existing tracks
        matched_tracks = set()
        unmatched_dets = []

        for i, (bbox, conf) in enumerate(det_boxes):
            best_iou = 0
            best_track_id = None

            # Find best matching track
            for track_id, track in self.tracked_persons.items():
                if track_id in matched_tracks:
                    continue

                iou = self._calculate_iou(bbox, track.person_bbox)
                if iou > self.iou_threshold and iou > best_iou:
                    best_iou = iou
                    best_track_id = track_id

            if best_track_id is not None:
                # Update existing track
                self.tracked_persons[best_track_id].update_detection(bbox, conf)
                matched_tracks.add(best_track_id)
            else:
                # New unmatched detection
                unmatched_dets.append((bbox, conf))

        # Create new tracks for unmatched detections
        for bbox, conf in unmatched_dets:
            track_id = self.next_id
            self.next_id += 1

            self.tracked_persons[track_id] = TrackedPerson(
                track_id=track_id,
                person_bbox=bbox,
                confidence=conf
            )

        # Remove tracks that have been lost too long
        self._cleanup_old_tracks()

        # Clean up face data if face hasn't been seen recently
        self._cleanup_face_memory()

        return list(self.tracked_persons.values())

    def update_face_recognition(
        self,
        track_id: int,
        face_bbox: List[float],
        name: str,
        confidence: float,
        person_id: str = ""
    ):
        """Update face recognition data for a specific track."""
        if track_id in self.tracked_persons:
            self.tracked_persons[track_id].update_face(face_bbox, name, confidence, person_id)

    def _calculate_iou(self, box1: List[float], box2: List[float]) -> float:
        """Calculate Intersection over Union between two boxes."""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2

        # Calculate intersection
        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)

        if inter_x_max < inter_x_min or inter_y_max < inter_y_min:
            return 0.0

        inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)

        # Calculate union
        box1_area = (x1_max - x1_min) * (y1_max - y1_min)
        box2_area = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = box1_area + box2_area - inter_area

        if union_area == 0:
            return 0.0

        return inter_area / union_area

    def _cleanup_old_tracks(self):
        """Remove tracks that haven't been seen for too long."""
        current_time = time.time()
        to_remove = []

        for track_id, track in self.tracked_persons.items():
            # Remove if lost for too many frames
            if track.frames_lost > self.max_age:
                to_remove.append(track_id)
            # Also remove if never confirmed and old
            elif track.frames_tracked < self.min_hits and \
                 (current_time - track.last_seen) > 2.0:
                to_remove.append(track_id)

        for track_id in to_remove:
            del self.tracked_persons[track_id]

    def _cleanup_face_memory(self):
        """Clear face data if face hasn't been seen recently."""
        current_time = time.time()

        for track in self.tracked_persons.values():
            if track.face_last_seen > 0 and \
               (current_time - track.face_last_seen) > self.face_memory_time:
                # Reset to tracking mode if face data is old
                if track.face_bbox is not None:
                    track.face_bbox = None
                    track.name = "—"
                    track.face_confidence = 0.0
                    track.status = "Tracking"

    def get_track_by_id(self, track_id: int) -> Optional[TrackedPerson]:
        """Get a specific track by ID."""
        return self.tracked_persons.get(track_id)

    def get_all_tracks(self) -> List[TrackedPerson]:
        """Get all active tracks."""
        return list(self.tracked_persons.values())

    def reset(self):
        """Reset tracker state."""
        self.tracked_persons.clear()
        self.next_id = 1


def link_face_to_person(
    person_bbox: List[float],
    face_bbox: List[float]
) -> bool:
    """
    Check if a face bounding box is inside a person bounding box.

    Args:
        person_bbox: [x1, y1, x2, y2] person box
        face_bbox: [x1, y1, x2, y2] face box

    Returns:
        True if face is inside person box
    """
    px1, py1, px2, py2 = person_bbox
    fx1, fy1, fx2, fy2 = face_bbox

    # Check if face center is inside person box
    face_center_x = (fx1 + fx2) / 2
    face_center_y = (fy1 + fy2) / 2

    if px1 <= face_center_x <= px2 and py1 <= face_center_y <= py2:
        return True

    # Also check for significant overlap
    overlap_x = min(px2, fx2) - max(px1, fx1)
    overlap_y = min(py2, fy2) - max(py1, fy1)

    if overlap_x > 0 and overlap_y > 0:
        overlap_area = overlap_x * overlap_y
        face_area = (fx2 - fx1) * (fy2 - fy1)

        # If more than 50% of face overlaps with person
        if face_area > 0 and (overlap_area / face_area) > 0.5:
            return True

    return False
