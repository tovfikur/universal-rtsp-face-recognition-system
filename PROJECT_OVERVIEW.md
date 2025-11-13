# Smart Recognition System - Complete Project Overview

## Table of Contents
1. [Project Summary](#project-summary)
2. [System Architecture](#system-architecture)
3. [Core Features](#core-features)
4. [Technology Stack](#technology-stack)
5. [Directory Structure](#directory-structure)
6. [Component Details](#component-details)
7. [Data Flow](#data-flow)
8. [API Documentation](#api-documentation)
9. [Database Schema](#database-schema)
10. [Configuration](#configuration)
11. [Performance Optimizations](#performance-optimizations)
12. [Background Processing](#background-processing)
13. [Deployment](#deployment)

---

## Project Summary

**Smart Recognition System** is an AI-powered real-time face recognition and person tracking system designed for security and monitoring applications. The system supports multiple video sources (webcams, RTSP/IP cameras, HTTP streams), performs real-time person detection and face recognition, and maintains a persistent history of all detections.

### Key Capabilities
- ✅ Real-time person detection using YOLOv8
- ✅ Face recognition with deep learning models
- ✅ Multi-person tracking with persistent IDs
- ✅ Support for multiple video sources (Webcam, RTSP, HTTP, RTMP)
- ✅ Background processing (continues when browser closed)
- ✅ Detection history with full CRUD operations
- ✅ Auto-reconnection and state restoration
- ✅ GPU acceleration (CUDA support)
- ✅ Responsive web interface with live overlay

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Browser)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Live Video   │  │   Canvas     │  │  Timeline    │         │
│  │   Preview    │  │   Overlay    │  │   Events     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│           │                 │                  │                │
└───────────┼─────────────────┼──────────────────┼────────────────┘
            │                 │                  │
         HTTP/WS           WebSocket          REST API
            │                 │                  │
┌───────────▼─────────────────▼──────────────────▼────────────────┐
│                    BACKEND (Python/Quart)                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │            Main Recognition Pipeline (Frontend)            │ │
│  │  [Video Stream] → [Detect] → [Track] → [Recognize]       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↕                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │       Background Processing Thread (Independent)           │ │
│  │  [Video Stream] → [Detect] → [Track] → [Recognize]       │ │
│  │                      ↓                                     │ │
│  │              [Store to Database]                          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   YOLOv8     │  │ Face         │  │  Person      │         │
│  │   Detector   │  │ Recognition  │  │  Tracker     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└──────────────────────────────────────────────────────────────────┘
            │                 │                  │
            ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Face DB      │  │ Detection    │  │  Stream      │         │
│  │ (Pickle)     │  │ History      │  │  State       │         │
│  │              │  │ (SQLite)     │  │  (JSON)      │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### Processing Pipeline

```
Video Source
    │
    ├─→ [Frame Capture]
    │       │
    │       ├─→ For Webcam: Capture at 50% resolution
    │       └─→ For RTSP: Use full resolution
    │
    ▼
[Frame Enhancement]
    │
    ├─→ Adjust brightness/contrast
    ├─→ Increase sharpness
    └─→ Denoise
    │
    ▼
[Person Detection] (YOLOv8)
    │
    ├─→ Detect all persons in frame
    ├─→ Filter by confidence (>0.65)
    └─→ Return bounding boxes
    │
    ▼
[Person Tracking] (SimpleTracker)
    │
    ├─→ Match detections to existing tracks (IoU)
    ├─→ Assign persistent track IDs
    ├─→ Handle occlusions (max_age=3 frames)
    └─→ Clean up old tracks
    │
    ▼
[Face Recognition]
    │
    ├─→ Extract person region from frame
    ├─→ Detect face in region
    ├─→ Extract face encoding (128-dim vector)
    ├─→ Compare with known faces (tolerance=0.45)
    └─→ Return: Name, Person ID, Confidence
    │
    ▼
[Output]
    │
    ├─→ Frontend: Display overlay with names
    ├─→ Backend: Store detection in database
    └─→ Events: Add to recent events timeline
```

---

## Core Features

### 1. Real-Time Person Detection
- **Technology**: YOLOv8 Nano (optimized for speed)
- **Confidence Threshold**: 0.65
- **GPU Acceleration**: CUDA support
- **Batch Processing**: Up to 8 frames per batch
- **Filters**: Min area (3000px), Max aspect ratio (4.0)

### 2. Face Recognition
- **Model**: CNN-based (GPU) or HOG (CPU fallback)
- **Encoding**: 128-dimensional face vectors
- **Tolerance**: 0.45 (configurable)
- **Features**:
  - Distance and angle robustness
  - Quality assessment
  - Multiple face handling
  - Person ID association

### 3. Multi-Person Tracking
- **Algorithm**: IoU-based tracker with Kalman filtering
- **Track Persistence**: 3 frames (configurable)
- **Features**:
  - Persistent track IDs
  - Color-coded overlays (Green=Known, Red=Unknown)
  - Occlusion handling
  - Face memory (3 seconds)

### 4. Video Source Support
- **Webcam**: USB cameras (device index 0, 1, 2, ...)
- **RTSP**: IP cameras and NVR systems
- **HTTP/MJPEG**: HTTP video streams
- **RTMP**: RTMP streaming sources
- **Video Files**: MP4, AVI, etc.

### 5. Background Processing
- **Independent Thread**: Runs separately from frontend
- **Continuous Operation**: Works when browser closed
- **Auto-Restore**: Resumes on server restart
- **Detection Storage**: All detections saved to database
- **State Persistence**: Stream state saved to JSON

### 6. Detection History
- **Storage**: SQLite database
- **Full CRUD**: Create, Read, Update, Delete operations
- **Filtering**: By person, date range, status
- **Statistics**: Daily counts, top persons, status breakdown
- **Pagination**: Efficient data retrieval

### 7. User Interface
- **Live Preview**: Real-time video with overlay
- **Canvas Overlay**: Ellipse bounding boxes with labels
- **Timeline**: Recent detection events
- **Statistics**: FPS, detected count, source info
- **Responsive**: Bootstrap 5 design
- **Auto-Reconnect**: Seamless reconnection after browser close

---

## Technology Stack

### Backend
- **Framework**: Quart (async Python web framework)
- **Server**: Hypercorn (ASGI server)
- **AI/ML**:
  - YOLOv8 (Ultralytics) - Person detection
  - face_recognition (dlib) - Face recognition
  - OpenCV (cv2) - Video processing
  - PyTorch - GPU acceleration
- **Database**: SQLite (detection history)
- **Storage**: Pickle (face encodings)
- **Video**: Enhanced video streaming with reconnection

### Frontend
- **HTML5/CSS3**: Modern web standards
- **JavaScript**: Vanilla JS (no frameworks)
- **Bootstrap 5**: UI framework
- **Font Awesome 6**: Icons
- **Canvas API**: Real-time overlay drawing
- **Fetch API**: Async HTTP requests

### System Requirements
- **OS**: Windows/Linux/macOS
- **Python**: 3.8+
- **GPU**: NVIDIA GPU with CUDA 11.0+ (optional but recommended)
- **RAM**: 4GB minimum, 8GB+ recommended
- **Storage**: 1GB+ for dependencies and models

---

## Directory Structure

```
face_person_recognition/
│
├── backend/                          # Backend server code
│   ├── app.py                       # Main application entry point
│   ├── database.py                  # Face database management
│   ├── detector.py                  # YOLOv8 person detector
│   ├── recognizer.py                # Face recognition engine
│   ├── tracker.py                   # Multi-person tracker
│   ├── enhanced_recognition.py      # Advanced face recognition
│   ├── video_sources.py             # Video stream management
│   ├── detection_history.py         # Detection history database
│   ├── stream_state.py              # Stream state persistence
│   ├── requirements.txt             # Python dependencies
│   │
│   ├── data/                        # Data storage
│   │   ├── faces.pkl               # Face encodings database
│   │   ├── detection_history.db    # SQLite detection history
│   │   └── stream_state.json       # Active stream state
│   │
│   └── faces/                       # Registered face images
│       └── [person_name]_[id].jpg
│
├── frontend/                         # Frontend web interface
│   ├── index.html                   # Main page (live monitoring)
│   ├── faces.html                   # Registered faces page
│   ├── script.js                    # Main JavaScript logic
│   ├── style.css                    # Custom styles
│   │
│   └── assets/                      # Static assets (if any)
│
├── yolov8n.pt                       # YOLOv8 Nano model weights
├── yolov8m.pt                       # YOLOv8 Medium model (optional)
├── .env                             # Environment configuration
└── README.md                        # Project documentation
```

---

## Component Details

### Backend Components

#### 1. **app.py** - Main Application
- HTTP server setup (Quart + Hypercorn)
- API endpoint definitions
- Request/response handling
- Background thread management
- Auto-restore logic

**Key Endpoints**:
- `/api/recognize` - Process frame and return detections
- `/api/register` - Register new face
- `/api/sources/change` - Change video source
- `/api/detections` - CRUD operations for detection history
- `/api/background/status` - Background processing status
- `/api/stream` - MJPEG video stream

#### 2. **detector.py** - Person Detector
```python
class PersonDetector:
    - YOLOv8 model loading and inference
    - GPU optimization with batching
    - Person filtering (confidence, size, aspect ratio)
    - Bounding box extraction
```

**Features**:
- Batch processing (8 frames)
- GPU warmup for consistent performance
- Confidence threshold: 0.65
- Min person area: 3000 pixels
- Max aspect ratio: 4.0

#### 3. **recognizer.py** - Face Recognition Engine
```python
class FaceRecognitionEngine:
    - Face detection in person regions
    - Face encoding extraction (128-dim)
    - Face matching against database
    - Track-based face caching
```

**Features**:
- CNN model for GPU, HOG for CPU
- Upsample times: 1 (balance speed/accuracy)
- Tracking TTL: 2 seconds
- Max simultaneous trackers: 30
- Batch processing: 8 faces

#### 4. **tracker.py** - Person Tracker
```python
class SimpleTracker:
    - IoU-based track matching
    - Kalman filter prediction
    - Track lifecycle management
    - Face-to-person linking
```

**Features**:
- IoU threshold: 0.3
- Max age: 3 frames (track persistence)
- Min hits: 1 (immediate tracking)
- Face memory: 3 seconds
- Color-coded tracks

#### 5. **video_sources.py** - Video Stream Management
```python
class EnhancedVideoStream:
    - Multi-source support (webcam, RTSP, HTTP, etc.)
    - Threaded frame reading
    - Auto-reconnection on failure
    - Health monitoring
```

**Features**:
- Async frame capture
- Reconnection with exponential backoff
- Stream health checks
- Buffer management

#### 6. **detection_history.py** - Detection Database
```python
class DetectionHistory:
    - SQLite-based storage
    - Full CRUD operations
    - Filtering and pagination
    - Statistics generation
```

**Schema**:
```sql
CREATE TABLE detections (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    person_name TEXT,
    person_id TEXT,
    confidence REAL,
    status TEXT,
    track_id INTEGER,
    bbox_x1, bbox_y1, bbox_x2, bbox_y2 REAL,
    source TEXT,
    snapshot_path TEXT,
    metadata TEXT,
    created_at TEXT
);
```

#### 7. **stream_state.py** - State Persistence
```python
class StreamStateManager:
    - Save/load active stream state
    - JSON-based storage
    - Thread-safe operations
```

**State Format**:
```json
{
  "active": true,
  "source": "rtsp://192.168.1.100:554/stream",
  "source_type": "rtsp"
}
```

### Frontend Components

#### 1. **script.js** - Main Logic

**Key Functions**:
```javascript
// Video capture
captureFrame() - Capture webcam frame at 50% resolution

// Overlay rendering
drawOverlays(results) - Draw ellipse overlays on canvas
drawSimpleBox() - Draw person bounding ellipse
drawSimpleLabel() - Draw person name/ID label

// Recognition loop
pollRecognition() - Poll backend every 16ms (60 FPS)
startRecognitionLoop() - Start recognition polling
stopRecognitionLoop() - Stop recognition polling

// Video source management
changeVideoSource() - Switch between video sources
toggleCamera() - Start/stop webcam

// Auto-reconnect
autoReconnectToStream() - Reconnect to active stream on page load

// State management
state = {
  stream, recognitionRunning, lastResults,
  remoteSource, isProcessing, bboxScaleX, bboxScaleY,
  lastOverlayUpdateTime, overlayMaxAge
}
```

**Overlay Features**:
- Ellipse bounding boxes (not rectangles)
- Dynamic scaling for webcam (50% → 100%)
- No scaling for RTSP (1:1)
- Edge clipping prevention
- Centered labels
- Color-coded by status

#### 2. **index.html** - Main Page
- Live video preview
- Canvas overlay
- Control buttons (Start, Stop, Add Person, RTSP, Clear)
- Status footer (FPS, detected count, source)
- Recognition timeline
- Settings panel

#### 3. **faces.html** - Registered Faces
- Gallery of registered faces
- Face cards with name, ID, date
- Refresh functionality
- Clear database option

#### 4. **style.css** - Custom Styles
- Dark theme UI
- Glassmorphism effects
- Responsive layout
- Animation transitions
- Status indicators

---

## Data Flow

### 1. Live Preview Flow (Browser Open)

```
[User Opens Browser]
        ↓
[Page Load]
        ↓
[Auto-Reconnect Check]
   ├─→ Active Stream? → Reconnect
   └─→ No Stream? → Show Start Button
        ↓
[User Starts Stream]
        ↓
Frontend Poll Loop (60 FPS):
   [Capture Frame @ 50%] (webcam only)
        ↓
   [Send to /api/recognize]
        ↓
   Backend Processing:
      [Get Frame]
      [Enhance]
      [Detect Persons]
      [Track Persons]
      [Recognize Faces]
        ↓
   [Return Results JSON]
        ↓
   [Draw Overlay on Canvas]
   [Scale coordinates 2x for webcam]
   [Update UI counters]
        ↓
   [Repeat every 16ms]
```

### 2. Background Processing Flow (Browser Closed)

```
[User Closes Browser]
        ↓
[Frontend Stops Polling]
        ↓
[Backend Continues Running]
        ↓
Background Thread Loop:
   [Get Frame from Stream]
        ↓
   [Enhance Frame]
        ↓
   [Detect Persons (YOLOv8)]
        ↓
   [Track Persons]
        ↓
   [Recognize Faces]
        ↓
   [Store Detections to Database]
   (only for "Known" persons)
        ↓
   [Sleep 500ms]
        ↓
   [Repeat Forever]
```

### 3. State Restoration Flow

```
[Backend Starts]
        ↓
[Load stream_state.json]
        ↓
Stream Active?
   ├─→ Yes:
   │    [Recreate Video Stream]
   │    [Start Background Thread]
   │    [Resume Processing]
   └─→ No:
        [Wait for User]
```

---

## API Documentation

### Video Source Endpoints

#### `POST /api/sources/change`
Change active video source and start background processing.

**Request:**
```json
{
  "source": "rtsp://admin:pass@192.168.1.100:554/stream",
  "reset": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Switched to source: rtsp://...",
  "source": "rtsp://...",
  "reset": true,
  "background_processing": true
}
```

#### `POST /api/sources/validate`
Validate if a video source is accessible.

**Request:**
```json
{
  "source": "rtsp://192.168.1.100:554/stream"
}
```

**Response:**
```json
{
  "success": true,
  "valid": true,
  "message": "Source is valid and accessible",
  "source": "rtsp://..."
}
```

### Recognition Endpoints

#### `POST /api/recognize`
Process frame and return detection results.

**Request:**
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
  // For webcam, or empty string "" for RTSP
}
```

**Response:**
```json
{
  "success": true,
  "timestamp": "2025-11-11T17:30:00.000Z",
  "results": [
    {
      "track_id": 1,
      "person_bbox": [100.0, 50.0, 300.0, 400.0],
      "person_confidence": 0.88,
      "face_bbox": [150.0, 100.0, 250.0, 200.0],
      "name": "John Doe",
      "person_id": "EMP001",
      "face_confidence": 0.95,
      "status": "Known",
      "frames_tracked": 45,
      "color": [0, 255, 0]
    }
  ],
  "active_tracks": 3
}
```

#### `POST /api/register`
Register a new person.

**Request:**
```json
{
  "name": "John Doe",
  "person_id": "EMP001",
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Face registered successfully",
  "face": {
    "name": "John Doe",
    "person_id": "EMP001",
    "image_url": "/faces/john_doe_EMP001.jpg",
    "created_at": "2025-11-11T17:30:00.000Z"
  }
}
```

### Detection History Endpoints

#### `GET /api/detections`
Get detection records with filtering.

**Query Parameters:**
- `limit` - Max records (default: 100)
- `offset` - Skip N records (default: 0)
- `person_name` - Filter by name
- `start_date` - Filter start date (ISO format)
- `end_date` - Filter end date (ISO format)

**Response:**
```json
{
  "success": true,
  "detections": [
    {
      "id": 1,
      "timestamp": "2025-11-11T17:30:00",
      "person_name": "John Doe",
      "person_id": "EMP001",
      "confidence": 0.95,
      "status": "Known",
      "track_id": 1,
      "bbox": [100.0, 50.0, 300.0, 400.0],
      "source": "rtsp://...",
      "metadata": {
        "frames_tracked": 45,
        "background_mode": true
      }
    }
  ],
  "count": 1
}
```

#### `GET /api/detections/<id>`
Get single detection by ID.

#### `PUT /api/detections/<id>`
Update detection record.

#### `DELETE /api/detections/<id>`
Delete detection record.

#### `DELETE /api/detections`
Delete all detection records.

#### `GET /api/detections/statistics`
Get detection statistics.

**Response:**
```json
{
  "success": true,
  "statistics": {
    "total_detections": 1234,
    "status_breakdown": {
      "Known": 1000,
      "Unknown": 234
    },
    "top_detected_persons": [
      {"name": "John Doe", "count": 500},
      {"name": "Jane Smith", "count": 300}
    ],
    "daily_detections": [
      {"date": "2025-11-11", "count": 150},
      {"date": "2025-11-10", "count": 200}
    ]
  }
}
```

### Background Processing Endpoints

#### `GET /api/background/status`
Check background processing status.

**Response:**
```json
{
  "success": true,
  "background_running": true,
  "stream_active": true,
  "current_source": "rtsp://...",
  "source_type": "rtsp",
  "thread_alive": true
}
```

#### `POST /api/background/start`
Manually start background processing.

#### `POST /api/background/stop`
Stop background processing.

### Utility Endpoints

#### `GET /api/faces`
Get all registered faces.

#### `DELETE /api/clear`
Clear all registered faces.

#### `GET /api/events`
Get recent detection events (timeline).

#### `GET /api/stream`
MJPEG video stream endpoint.

---

## Database Schema

### Face Database (Pickle)

**File**: `backend/data/faces.pkl`

**Structure**:
```python
{
  "encodings": [
    [0.1, -0.2, 0.3, ...],  # 128-dim vector
    [0.2, 0.1, -0.1, ...]
  ],
  "metadata": [
    {
      "name": "John Doe",
      "person_id": "EMP001",
      "image_path": "john_doe_EMP001.jpg",
      "created_at": "2025-11-11T17:30:00"
    }
  ]
}
```

### Detection History (SQLite)

**File**: `backend/data/detection_history.db`

**Table**: `detections`

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| timestamp | TEXT | Detection timestamp (ISO format) |
| person_name | TEXT | Detected person's name |
| person_id | TEXT | Person ID/badge number |
| confidence | REAL | Recognition confidence (0-1) |
| status | TEXT | "Known" or "Unknown" |
| track_id | INTEGER | Tracker ID |
| bbox_x1, bbox_y1, bbox_x2, bbox_y2 | REAL | Bounding box coordinates |
| source | TEXT | Video source |
| snapshot_path | TEXT | Path to snapshot image (optional) |
| metadata | TEXT | JSON metadata |
| created_at | TEXT | Record creation time |

**Indexes**:
- `idx_timestamp` - On timestamp (DESC)
- `idx_person_name` - On person_name
- `idx_created_at` - On created_at (DESC)

### Stream State (JSON)

**File**: `backend/data/stream_state.json`

```json
{
  "active": true,
  "source": "rtsp://admin:pass@192.168.1.100:554/stream",
  "source_type": "rtsp"
}
```

---

## Configuration

### Environment Variables (.env)

```bash
# Flask/Quart settings
FLASK_DEBUG=0                    # Debug mode (0=off, 1=on)

# Face recognition settings
FACE_TOLERANCE=0.45              # Lower = stricter matching

# Video settings
DEFAULT_CAMERA_SOURCE=0          # Default webcam index
FRAME_BUFFER_SIZE=3              # Frame buffer size

# Device settings
YOLO_DEVICE=cuda:0               # cuda:0 for GPU, cpu for CPU
```

### Frontend Configuration (script.js)

```javascript
const state = {
  frameInterval: 500,           // Frame send interval (ms)
  minFrameInterval: 300,        // Min time between frames
  requestTimeout: 5000,         // Request timeout
  maxTimeout: 10000,            // Max timeout
  adaptiveQuality: 0.6,         // JPEG quality (0-1)
  lowResMode: false,            // Low resolution mode
  overlayMaxAge: 1000,          // Clear overlay after 1s
};
```

### Backend Configuration (app.py)

```python
# Detector settings
detector = PersonDetector(
    model_path="yolov8n.pt",    # Nano model for speed
    confidence=0.65,             # Min confidence
    device=YOLO_DEVICE,
    batch_size=8,                # Batch size
    min_person_area=3000,        # Min area (pixels)
    max_aspect_ratio=4.0         # Max height/width ratio
)

# Recognizer settings
recognizer = FaceRecognitionEngine(
    model="cnn" if GPU else "hog",
    upsample_times=1,
    tracking_ttl=2.0,            # Track for 2 seconds
    max_trackers=30,
    batch_size=8
)

# Tracker settings
person_tracker = SimpleTracker(
    iou_threshold=0.3,           # IoU matching threshold
    max_age=3,                   # Max frames without detection
    min_hits=1,                  # Frames before track confirmed
    face_memory_time=3.0         # Face cache duration
)
```

---

## Performance Optimizations

### 1. Resolution Scaling
- **Webcam**: Send frames at 50% resolution
- **RTSP**: Process at full resolution
- **Canvas**: Display at full resolution with coordinate scaling

### 2. GPU Acceleration
- YOLOv8 detection on GPU
- Face recognition with CNN model (GPU)
- Batch processing for efficiency
- CUDA optimizations enabled

### 3. Frame Processing
- Throttled frame sending (300ms minimum)
- Sequential processing (no queuing)
- Latest frame only (abort old requests)
- Adaptive quality adjustment

### 4. Overlay Rendering
- Double buffering (offscreen canvas)
- Atomic canvas updates (no flicker)
- Persistent overlay (no redraw until new data)
- Optimized ellipse drawing

### 5. Tracking Optimization
- IoU-based matching (fast)
- Kalman prediction for missing frames
- Face caching (avoid re-recognition)
- Track cleanup (old tracks removed)

### 6. Database Optimization
- SQLite indexes on key columns
- Batch inserts for detections
- Pagination for large datasets
- Statistics pre-computation

### 7. Network Optimization
- MJPEG streaming (efficient)
- Compressed JPEG (quality=0.6)
- Connection pooling
- Request timeout management

---

## Background Processing

### Architecture

```
Backend Process
    │
    ├─→ Main Thread (Quart Server)
    │    └─→ Handles HTTP requests
    │
    └─→ Background Thread (Daemon)
         └─→ Independent processing loop
              │
              ├─→ Get frame from video stream
              ├─→ Detect persons
              ├─→ Track persons
              ├─→ Recognize faces
              └─→ Store to database
```

### Features

1. **Independent Operation**
   - Runs in separate thread
   - Not affected by frontend state
   - Continues when browser closed
   - Daemon thread (auto-cleanup)

2. **State Persistence**
   - Stream state saved to JSON
   - Auto-restore on server restart
   - No manual intervention needed

3. **Detection Storage**
   - Only stores "Known" persons
   - Includes full metadata
   - Marked as "background_mode": true

4. **Auto-Reconnection**
   - Frontend checks `/api/background/status` on load
   - Reconnects to active stream automatically
   - Seamless user experience

### Workflow

**Starting Stream:**
```
User → Start RTSP → Backend
                        ↓
                  [Create Video Stream]
                        ↓
                  [Start Background Thread]
                        ↓
                  [Save State to JSON]
                        ↓
                  [Return Success]
```

**Closing Browser:**
```
User → Close Browser → Frontend Stops
                            ↓
                       Backend Continues
                            ↓
                    [Background Thread Runs]
                            ↓
                    [Detections Stored]
```

**Reopening Browser:**
```
Browser → Load Page → Auto-Reconnect Check
                            ↓
                    [GET /api/background/status]
                            ↓
                    Stream Active?
                      ↓ Yes
                [Reconnect to Stream]
                      ↓
                [Show Live Preview]
                      ↓
                [Resume Recognition Loop]
```

**Server Restart:**
```
Backend Start → Load stream_state.json
                      ↓
                Stream Was Active?
                  ↓ Yes
            [Recreate Video Stream]
                  ↓
            [Start Background Thread]
                  ↓
            [Resume Processing]
```

---

## Deployment

### Installation

1. **Clone Repository**
   ```bash
   cd /path/to/project
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

3. **Install Dependencies**
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Download YOLOv8 Model**
   ```bash
   # Model will auto-download on first run
   # Or manually download from Ultralytics
   ```

5. **Configure Environment**
   ```bash
   # Edit .env file
   FLASK_DEBUG=0
   FACE_TOLERANCE=0.45
   DEFAULT_CAMERA_SOURCE=0
   YOLO_DEVICE=cuda:0  # or cpu
   ```

### Running the System

**Development Mode:**
```bash
python backend/app.py
```

**Production Mode:**
```bash
# Using hypercorn directly
hypercorn backend.app:app --bind 0.0.0.0:5000

# Or with gunicorn
gunicorn -w 1 -k uvicorn.workers.UvicornWorker backend.app:app --bind 0.0.0.0:5000
```

**Access Interface:**
```
http://localhost:5000          # Main interface
http://localhost:5000/faces.html  # Registered faces
```

### Docker Deployment (Optional)

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "backend/app.py"]
```

```bash
docker build -t smart-recognition .
docker run -p 5000:5000 --gpus all smart-recognition
```

### System Service (Linux)

```bash
# /etc/systemd/system/smart-recognition.service
[Unit]
Description=Smart Recognition System
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/project
Environment="PATH=/path/to/project/.venv/bin"
ExecStart=/path/to/project/.venv/bin/python backend/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable smart-recognition
sudo systemctl start smart-recognition
```

---

## Troubleshooting

### Common Issues

1. **GPU Not Detected**
   - Install CUDA toolkit and cuDNN
   - Verify: `python -c "import torch; print(torch.cuda.is_available())"`
   - Set `YOLO_DEVICE=cpu` in .env as fallback

2. **RTSP Connection Failed**
   - Check camera credentials
   - Verify network connectivity
   - Test with VLC: `vlc rtsp://...`
   - Check firewall settings

3. **Face Recognition Low Accuracy**
   - Adjust `FACE_TOLERANCE` (lower = stricter)
   - Ensure good lighting
   - Register multiple face angles
   - Check face image quality

4. **High CPU/GPU Usage**
   - Reduce frame rate (increase `minFrameInterval`)
   - Use lower resolution
   - Reduce `batch_size`
   - Switch to YOLOv8n (nano) model

5. **Overlay Misalignment**
   - Check coordinate scaling (fixed in latest version)
   - Verify canvas dimensions match video
   - Check `bboxScaleX/Y` values

---

## Future Enhancements

### Planned Features
- [ ] Multi-camera support (simultaneous streams)
- [ ] Email/SMS alerts for specific persons
- [ ] Facial attribute detection (age, gender, emotion)
- [ ] Advanced search (by time, location, appearance)
- [ ] Video recording with detections
- [ ] Dashboard with analytics
- [ ] Mobile app (iOS/Android)
- [ ] Cloud deployment (AWS/Azure/GCP)
- [ ] LDAP/Active Directory integration
- [ ] Access control integration
- [ ] Visitor management system

### Performance Improvements
- [ ] Redis caching for face encodings
- [ ] PostgreSQL for scalable detection storage
- [ ] Horizontal scaling (multiple workers)
- [ ] Load balancing for multiple cameras
- [ ] Video compression for storage
- [ ] Distributed processing (Celery/RQ)

### Security Enhancements
- [ ] User authentication (login system)
- [ ] Role-based access control (RBAC)
- [ ] Encrypted face data storage
- [ ] Audit logging
- [ ] HTTPS/SSL support
- [ ] API key authentication
- [ ] Rate limiting

---

## License

This project is proprietary and confidential.

## Support

For support, please contact: [Your Contact Information]

## Version History

- **v1.0.0** (2025-11-11)
  - Initial release
  - Real-time detection and recognition
  - Multi-source support
  - Background processing
  - Detection history
  - Auto-reconnection

---

## Acknowledgments

- **Ultralytics YOLOv8** - Person detection
- **dlib/face_recognition** - Face recognition
- **OpenCV** - Video processing
- **Quart** - Async web framework
- **Bootstrap** - UI framework

---

**Generated**: 2025-11-11
**Project**: Smart Recognition System
**Architecture Version**: 1.0
