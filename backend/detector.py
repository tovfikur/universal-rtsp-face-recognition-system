"""
YOLOv8 based person detector with maximum GPU utilization.
"""

from __future__ import annotations

from typing import Dict, List, Optional
import threading
import queue
import time

import numpy as np
from ultralytics import YOLO
import torch


def _autodetect_device(preferred: Optional[str] = None) -> str:
    """Pick the best available execution device (cuda > mps > cpu)."""
    if preferred and preferred.lower() != "auto":
        return preferred

    try:
        import torch
    except Exception:  # pragma: no cover - torch import optional
        return "cpu"

    if torch.cuda.is_available():
        return "cuda:0"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():  # type: ignore[attr-defined]
        return "mps"
    return "cpu"


class PersonDetector:
    """High-performance YOLOv8n detector with GPU optimization and tracking."""

    def __init__(
        self,
        model_path: str = "yolov8n.pt",  # Use nano model for faster inference
        confidence: float = 0.65,  # Much higher threshold - only very confident person detections
        device: Optional[str] = None,
        batch_size: int = 4,  # Smaller batches for lower latency
        min_person_area: int = 3000,  # Minimum pixel area for valid person (prevent small false detections)
        max_aspect_ratio: float = 4.0,  # Maximum height/width ratio (prevent weird shaped objects)
    ) -> None:
        self.confidence = confidence
        self.min_person_area = min_person_area
        self.max_aspect_ratio = max_aspect_ratio
        self.device = _autodetect_device(device)
        self.batch_size = batch_size
        print(f"[PersonDetector] Using device: {self.device}")
        print(f"[PersonDetector] Confidence threshold: {self.confidence}")
        print(f"[PersonDetector] Min person area: {self.min_person_area} pixels")
        print(f"[PersonDetector] Max aspect ratio: {self.max_aspect_ratio}")

        # Initialize YOLO with optimized settings
        self.model = YOLO(model_path)

        # Force model to GPU and enable optimization
        if "cuda" in self.device:
            # Set PyTorch to use cudnn benchmarking for best performance
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.enabled = True

            # Move model to GPU
            self.model.to(self.device)

            # Enable TensorFloat-32 for faster matrix operations on Ampere GPUs
            torch.set_float32_matmul_precision('high')

            print("[PersonDetector] Warming up GPU with optimized inference...")
            # Warm up with realistic single frame (faster startup)
            dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
            with torch.amp.autocast('cuda'):
                for _ in range(2):  # Quick warmup
                    try:
                        self.model.predict(
                            dummy_frame,
                            classes=[0],
                            conf=self.confidence,
                            verbose=False,
                            device=self.device,
                            half=True,
                            imgsz=640
                        )
                    except Exception as e:
                        print(f"[Warmup warning] {e}")

            print("[PersonDetector] GPU warmup complete - ready for inference")
            
        # Setup batch processing queue
        self.frame_queue = queue.Queue(maxsize=self.batch_size * 2)
        self.result_queue = queue.Queue()
        self.processing_thread = threading.Thread(target=self._batch_processor, daemon=True)
        self.running = True
        self.processing_thread.start()

    def _detect_batch(self, batch: List[np.ndarray]) -> List[List[Dict[str, float]]]:
        """Process a batch of frames on GPU."""
        # Validate input dimensions
        valid_frames = []
        for frame in batch:
            if frame is None or frame.size == 0 or min(frame.shape[:2]) < 10:
                valid_frames.append(np.zeros((640, 640, 3), dtype=np.uint8))
            else:
                valid_frames.append(frame)
                
        with torch.amp.autocast('cuda'):  # Use automatic mixed precision
            results = self.model.predict(
                source=valid_frames,
                classes=[0],  # person class
                conf=self.confidence,
                verbose=False,
                device=self.device,
                max_det=50,  # More detections
                imgsz=640,
                half=True if "cuda" in self.device else False,
                batch=len(valid_frames),  # Explicit batch size
                stream=True,  # Stream results
            )
        
        batch_detections = []
        for result in results:
            detections = []
            if result.boxes is not None:
                xyxy = result.boxes.xyxy.cpu().numpy()
                confs = result.boxes.conf.cpu().numpy()

                print(f"[DEBUG] YOLO returned {len(xyxy)} raw detections")

                for i, (bbox, conf) in enumerate(zip(xyxy, confs)):
                    x1, y1, x2, y2 = [float(v) for v in bbox]

                    # Calculate bounding box dimensions
                    width = x2 - x1
                    height = y2 - y1
                    area = width * height

                    print(f"[DEBUG] Detection {i}: bbox=({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}), conf={conf:.2f}, area={area:.0f}")

                    # Filter 1: Minimum area (prevent tiny false detections)
                    if area < self.min_person_area:
                        print(f"[DEBUG]   -> FILTERED: area {area:.0f} < {self.min_person_area}")
                        continue

                    # Filter 2: Aspect ratio (persons are typically taller than wide)
                    aspect_ratio = height / width if width > 0 else 0
                    if aspect_ratio > self.max_aspect_ratio or aspect_ratio < 0.3:
                        # Too tall/thin (like poles) or too wide/flat (like tables)
                        print(f"[DEBUG]   -> FILTERED: aspect_ratio {aspect_ratio:.2f} not in [0.3, {self.max_aspect_ratio}]")
                        continue

                    # Filter 3: Reasonable dimensions (prevent extremely large detections)
                    if width < 20 or height < 40:
                        # Too small to be a person
                        print(f"[DEBUG]   -> FILTERED: dimensions {width:.0f}x{height:.0f} too small")
                        continue

                    if width > 800 or height > 1200:
                        # Unreasonably large (probably false detection)
                        print(f"[DEBUG]   -> FILTERED: dimensions {width:.0f}x{height:.0f} too large")
                        continue

                    # Valid person detection
                    print(f"[DEBUG]   -> ACCEPTED")
                    detections.append({
                        "bbox": [x1, y1, x2, y2],
                        "confidence": float(conf),
                    })
            else:
                print("[DEBUG] YOLO returned NO boxes")
            batch_detections.append(detections)

        return batch_detections

    def _batch_processor(self):
        """Background thread for batch processing."""
        while self.running:
            batch_frames = []
            batch_ids = []
            
            # Collect frames for batch
            deadline = time.time() + 0.05  # 50ms window
            while len(batch_frames) < self.batch_size and time.time() < deadline:
                try:
                    frame_id, frame = self.frame_queue.get(timeout=0.01)
                    batch_frames.append(frame)
                    batch_ids.append(frame_id)
                except queue.Empty:
                    break
            
            if batch_frames:
                # Pad batch if needed
                while len(batch_frames) < self.batch_size:
                    batch_frames.append(batch_frames[-1])
                    batch_ids.append(-1)
                
                # Process batch
                batch = np.array(batch_frames)
                results = self._detect_batch(batch)
                
                # Return results
                for i, (frame_id, detections) in enumerate(zip(batch_ids, results)):
                    if frame_id != -1:  # Skip padding
                        self.result_queue.put((frame_id, detections))

    def detect(self, frame: np.ndarray, frame_id: Optional[int] = None) -> List[Dict[str, float]]:
        """
        Queue frame for detection and return results.
        """
        if frame is None:
            return []
        
        # Use timestamp as frame_id if not provided
        if frame_id is None:
            frame_id = int(time.time() * 1000000)
        
        # Queue frame
        try:
            self.frame_queue.put((frame_id, frame), timeout=0.05)
        except queue.Full:
            return []  # Skip if queue is full
        
        # Try to get result
        try:
            result_id, detections = self.result_queue.get(timeout=0.1)
            return detections
        except queue.Empty:
            return []

    def detect_immediate(self, frame: np.ndarray, debug: bool = False) -> List[Dict[str, float]]:
        """
        OPTIMIZED: Direct detection without batching for lowest latency.
        Uses single-frame inference for immediate results.
        """
        if frame is None:
            if debug:
                print("[DEBUG] Detector: Empty frame received")
            return []

        if debug:
            print(f"[DEBUG] Detector: Processing frame with shape {frame.shape}")

        # Direct single-frame inference (no batching overhead)
        try:
            with torch.amp.autocast('cuda') if "cuda" in self.device else torch.no_grad():
                result = self.model.predict(
                    source=frame,
                    classes=[0],  # person class only
                    conf=self.confidence,
                    verbose=False,
                    device=self.device,
                    max_det=50,
                    imgsz=640,
                    half=True if "cuda" in self.device else False,
                    stream=False,  # Single frame, no streaming
                )[0]  # Get first result

            detections = []
            if result.boxes is not None:
                xyxy = result.boxes.xyxy.cpu().numpy()
                confs = result.boxes.conf.cpu().numpy()

                if debug:
                    print(f"[DEBUG] YOLO returned {len(xyxy)} raw detections")

                for i, (bbox, conf) in enumerate(zip(xyxy, confs)):
                    x1, y1, x2, y2 = [float(v) for v in bbox]

                    # Calculate bounding box dimensions
                    width = x2 - x1
                    height = y2 - y1
                    area = width * height

                    if debug:
                        print(f"[DEBUG] Detection {i}: bbox=({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}), conf={conf:.2f}, area={area:.0f}")

                    # Filter 1: Minimum area (prevent tiny false detections)
                    if area < self.min_person_area:
                        if debug:
                            print(f"[DEBUG]   -> FILTERED: area {area:.0f} < {self.min_person_area}")
                        continue

                    # Filter 2: Aspect ratio (persons are typically taller than wide)
                    aspect_ratio = height / width if width > 0 else 0
                    if aspect_ratio > self.max_aspect_ratio or aspect_ratio < 0.3:
                        if debug:
                            print(f"[DEBUG]   -> FILTERED: aspect_ratio {aspect_ratio:.2f} not in [0.3, {self.max_aspect_ratio}]")
                        continue

                    # Filter 3: Reasonable dimensions
                    if width < 20 or height < 40:
                        if debug:
                            print(f"[DEBUG]   -> FILTERED: dimensions {width:.0f}x{height:.0f} too small")
                        continue

                    if width > 800 or height > 1200:
                        if debug:
                            print(f"[DEBUG]   -> FILTERED: dimensions {width:.0f}x{height:.0f} too large")
                        continue

                    # Valid person detection
                    if debug:
                        print(f"[DEBUG]   -> ACCEPTED")

                    detections.append({
                        "bbox": [x1, y1, x2, y2],
                        "confidence": float(conf),
                    })
            else:
                if debug:
                    print("[DEBUG] YOLO returned NO boxes")

            if debug:
                print(f"[DEBUG] Detector: Found {len(detections)} valid people")

            return detections

        except Exception as e:
            print(f"[ERROR] Detection failed: {e}")
            import traceback
            traceback.print_exc()
            return []

    def stop(self):
        """Stop the batch processing thread."""
        self.running = False
        if self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)