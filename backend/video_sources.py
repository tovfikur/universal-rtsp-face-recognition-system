"""
Enhanced video source manager supporting multiple input types:
- Webcam (USB cameras)
- RTSP streams
- HTTP/HTTPS streams
- RTMP streams
- Local video files
"""

import cv2
import numpy as np
import threading
import time
import os
from typing import Optional, Union, Dict, Any
from dataclasses import dataclass
from enum import Enum


class SourceType(Enum):
    """Video source types."""
    WEBCAM = "webcam"
    RTSP = "rtsp"
    HTTP = "http"
    RTMP = "rtmp"
    FILE = "file"
    UNKNOWN = "unknown"


@dataclass
class SourceInfo:
    """Information about a video source."""
    source_type: SourceType
    source: Union[int, str]
    width: int = 0
    height: int = 0
    fps: float = 0.0
    is_live: bool = True
    description: str = ""


class EnhancedVideoStream:
    """
    Enhanced video stream with support for multiple source types.
    Handles connection errors, reconnection, and stream health monitoring.
    """

    def __init__(
        self,
        source: Union[int, str],
        reconnect_delay: float = 5.0,
        max_reconnect_attempts: int = 0,  # 0 = infinite
        buffer_size: int = 1,
        max_width: int = 1280,  # Maximum frame width
        max_height: int = 720   # Maximum frame height
    ):
        self.source = source
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self.buffer_size = buffer_size
        self.max_width = max_width
        self.max_height = max_height

        # Detect source type
        self.source_info = self._detect_source_type(source)

        # Stream state
        self.capture: Optional[cv2.VideoCapture] = None
        self.frame: Optional[np.ndarray] = None
        self.lock = threading.Lock()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.reconnect_count = 0
        self.last_frame_time = 0.0
        self.is_connected = False
        self.downscale_applied = False  # Track if downscaling was applied

        # Start streaming
        self._connect()

    def _detect_source_type(self, source: Union[int, str]) -> SourceInfo:
        """Detect the type of video source."""
        if isinstance(source, int):
            return SourceInfo(
                source_type=SourceType.WEBCAM,
                source=source,
                is_live=True,
                description=f"Webcam {source}"
            )

        source_str = str(source).lower()

        if source_str.startswith("rtsp://"):
            return SourceInfo(
                source_type=SourceType.RTSP,
                source=source,
                is_live=True,
                description=f"RTSP Stream"
            )
        elif source_str.startswith(("http://", "https://")):
            return SourceInfo(
                source_type=SourceType.HTTP,
                source=source,
                is_live=True,
                description=f"HTTP Stream"
            )
        elif source_str.startswith("rtmp://"):
            return SourceInfo(
                source_type=SourceType.RTMP,
                source=source,
                is_live=True,
                description=f"RTMP Stream"
            )
        elif source_str.endswith(('.mp4', '.avi', '.mkv', '.mov', '.flv')):
            return SourceInfo(
                source_type=SourceType.FILE,
                source=source,
                is_live=False,
                description=f"Video File"
            )
        else:
            return SourceInfo(
                source_type=SourceType.UNKNOWN,
                source=source,
                is_live=True,
                description=f"Unknown Source"
            )

    def _connect(self) -> bool:
        """Connect to video source."""
        try:
            print(f"[VideoStream] Connecting to {self.source_info.description}: {self.source}")

            # For RTSP, use FFmpeg backend with optimizations
            if self.source_info.source_type == SourceType.RTSP:
                print("[VideoStream] Using FFmpeg backend for RTSP")

                # Build RTSP URL with FFmpeg options embedded
                rtsp_options = (
                    "rtsp_transport;tcp|"  # Force TCP transport
                    "rtsp_flags;prefer_tcp|"  # Prefer TCP over UDP
                    "buffer_size;1024000|"  # 1MB buffer
                    "max_delay;500000|"  # 500ms max delay
                    "stimeout;5000000"  # 5 second socket timeout
                )

                # Set FFmpeg options via environment variable method
                os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = rtsp_options

                # Force FFmpeg backend
                self.capture = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
            else:
                # Use default backend for other sources
                self.capture = cv2.VideoCapture(self.source)

            if not self.capture.isOpened():
                raise RuntimeError(f"Failed to open source: {self.source}")

            # Configure capture based on source type
            if self.source_info.source_type == SourceType.RTSP:
                # RTSP optimizations for low latency
                self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffer

                # Aggressive timeout settings
                self.capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)  # 3 second open timeout
                self.capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)  # 3 second read timeout

                print("[VideoStream] RTSP settings applied: TCP mode, 3s timeouts, buffer=1")

            elif self.source_info.source_type == SourceType.WEBCAM:
                # Webcam optimizations
                self.capture.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)
                self.capture.set(cv2.CAP_PROP_FPS, 30)
                self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            # Get stream info
            self.source_info.width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.source_info.height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.source_info.fps = self.capture.get(cv2.CAP_PROP_FPS) or 30.0

            print(f"[VideoStream] Connected: {self.source_info.width}x{self.source_info.height} @ {self.source_info.fps}fps")

            # Skip test frame read for RTSP (can cause hangs on high-res streams)
            # The reader thread will handle frame reading with proper timeouts
            if self.source_info.source_type != SourceType.RTSP:
                print("[VideoStream] Testing frame read...")
                test_success, test_frame = self.capture.read()

                if not test_success or test_frame is None:
                    print("[VideoStream] WARNING: Could not read test frame, but continuing...")
                else:
                    print(f"[VideoStream] Successfully read test frame: {test_frame.shape}")
            else:
                print("[VideoStream] Skipping test frame read for RTSP (will read in background thread)")

            # Start reader thread
            self.running = True
            self.is_connected = True
            self.thread = threading.Thread(target=self._reader, daemon=True)
            self.thread.start()

            print("[VideoStream] Reader thread started")
            return True

        except Exception as e:
            print(f"[VideoStream] Connection failed: {e}")
            self.is_connected = False
            if self.capture:
                self.capture.release()
                self.capture = None
            return False

    def _reader(self) -> None:
        """Background thread to read frames."""
        consecutive_failures = 0
        max_failures = 30  # Reconnect after 30 consecutive failures
        is_rtsp = self.source_info.source_type == SourceType.RTSP
        frame_count = 0

        print(f"[VideoStream] Reader thread running (RTSP: {is_rtsp})")

        # For RTSP: Log first frame attempt
        first_frame_logged = False

        while self.running:
            if not self.capture or not self.capture.isOpened():
                print("[VideoStream] Capture not available, attempting reconnect...")
                self._reconnect()
                time.sleep(1)
                continue

            try:
                # For RTSP: Log first frame attempt
                if is_rtsp and not first_frame_logged:
                    print("[VideoStream] Attempting to read first RTSP frame...")
                    first_frame_logged = True

                # Read frame with timeout protection using threading
                if is_rtsp:
                    # Use timeout for RTSP frame read
                    result = [None, None]

                    def read_frame():
                        try:
                            result[0], result[1] = self.capture.read()
                        except Exception as e:
                            print(f"[VideoStream] Exception during frame read: {e}")
                            result[0], result[1] = False, None

                    read_thread = threading.Thread(target=read_frame, daemon=True)
                    read_thread.start()
                    read_thread.join(timeout=3.0)  # 3 second timeout

                    if read_thread.is_alive():
                        print("[VideoStream] Frame read timeout, skipping...")
                        consecutive_failures += 1
                        time.sleep(0.5)
                        continue

                    success, frame = result[0], result[1]
                else:
                    # No timeout for webcam
                    success, frame = self.capture.read()

                frame_count += 1

                if not success or frame is None:
                    consecutive_failures += 1
                    if consecutive_failures == 1:
                        print(f"[VideoStream] Frame read failed, will retry...")
                    elif consecutive_failures % 10 == 0:
                        print(f"[VideoStream] Still failing (attempt {consecutive_failures}/{max_failures})")

                    if consecutive_failures >= max_failures:
                        print("[VideoStream] Too many failures, reconnecting...")
                        self._reconnect()
                        consecutive_failures = 0

                    time.sleep(0.2)  # Longer delay on failure
                    continue

                # Successfully read frame
                if consecutive_failures > 0:
                    print(f"[VideoStream] Frame read recovered after {consecutive_failures} failures")
                consecutive_failures = 0

                # Log first successful frame for RTSP
                if is_rtsp and frame_count == 1:
                    print(f"[VideoStream] Successfully read first RTSP frame!")

                # Auto-downscale frame if it exceeds maximum resolution
                if frame is not None:
                    h, w = frame.shape[:2]

                    # Check if downscaling is needed
                    if w > self.max_width or h > self.max_height:
                        # Calculate scaling factor to maintain aspect ratio
                        scale = min(self.max_width / w, self.max_height / h)
                        new_w = int(w * scale)
                        new_h = int(h * scale)

                        # Downscale frame using high-quality interpolation
                        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

                        # Log once when downscaling is first applied
                        if not self.downscale_applied:
                            print(f"[VideoStream] Auto-downscaling: {w}x{h} → {new_w}x{new_h} (max: {self.max_width}x{self.max_height})")
                            self.downscale_applied = True

                with self.lock:
                    self.frame = frame
                    self.last_frame_time = time.time()

                # Adaptive delay based on source type
                if is_rtsp:
                    time.sleep(0.01)  # 10ms delay for RTSP
                else:
                    time.sleep(0.01)  # Standard delay

            except Exception as e:
                print(f"[VideoStream] Error reading frame: {e}")
                consecutive_failures += 1
                time.sleep(0.2)

    def _reconnect(self) -> None:
        """Attempt to reconnect to source."""
        if not self.is_connected:
            return

        self.is_connected = False
        self.reconnect_count += 1

        # Check reconnect limit
        if self.max_reconnect_attempts > 0 and self.reconnect_count > self.max_reconnect_attempts:
            print(f"[VideoStream] Max reconnect attempts ({self.max_reconnect_attempts}) reached")
            self.stop()
            return

        print(f"[VideoStream] Reconnecting... (attempt {self.reconnect_count})")

        # Release old capture
        if self.capture:
            self.capture.release()
            self.capture = None

        # Wait before reconnecting
        time.sleep(self.reconnect_delay)

        # Attempt reconnection
        self._connect()

    def get_frame(self) -> Optional[np.ndarray]:
        """Get the latest frame."""
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def get_info(self) -> SourceInfo:
        """Get source information."""
        return self.source_info

    def is_alive(self) -> bool:
        """Check if stream is alive and receiving frames."""
        if not self.is_connected:
            return False

        # Check if we've received a frame recently (within last 5 seconds)
        if self.last_frame_time == 0:
            return True  # Just started

        return (time.time() - self.last_frame_time) < 5.0

    def get_status(self) -> Dict[str, Any]:
        """Get detailed stream status."""
        return {
            "connected": self.is_connected,
            "alive": self.is_alive(),
            "source_type": self.source_info.source_type.value,
            "width": self.source_info.width,
            "height": self.source_info.height,
            "fps": self.source_info.fps,
            "reconnect_count": self.reconnect_count,
            "last_frame_time": self.last_frame_time,
            "description": self.source_info.description
        }

    def stop(self) -> None:
        """Stop the video stream."""
        print(f"[VideoStream] Stopping stream from {self.source}")
        self.running = False
        self.is_connected = False

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

        if self.capture:
            self.capture.release()
            self.capture = None


# Convenience functions
def parse_source(source_str: str) -> Union[int, str]:
    """
    Parse source string to appropriate type.

    Examples:
        "0" -> 0 (webcam)
        "1" -> 1 (webcam)
        "rtsp://192.168.1.100:554/stream" -> "rtsp://..." (RTSP)
        "http://example.com/stream.mjpg" -> "http://..." (HTTP)
    """
    # Try to parse as integer (webcam index)
    try:
        return int(source_str)
    except ValueError:
        pass

    # Return as string (URL or file path)
    return source_str


def validate_source(source: Union[int, str]) -> tuple[bool, str]:
    """
    Validate if a source is accessible.

    Returns:
        (is_valid, error_message)
    """
    try:
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            cap.release()
            return False, f"Cannot open source: {source}"

        # Try to read one frame
        success, frame = cap.read()
        cap.release()

        if not success or frame is None:
            return False, f"Cannot read from source: {source}"

        return True, "Source is valid"

    except Exception as e:
        return False, f"Error validating source: {str(e)}"
