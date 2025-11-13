# Face Recognition Attendance Management System

Complete API-driven attendance management system built on top of a high-performance face recognition engine. Combines YOLOv8 person detection, dlib face recognition, and a comprehensive REST API for managing attendance records.

## 📚 Documentation Navigation

| Document | Description |
|----------|-------------|
| **[Quick Start Guide](QUICK_START.md)** | Get started in minutes |
| **[Setup Guide](SETUP_GUIDE.md)** | Detailed installation and setup instructions |
| **[API Documentation](API_DOCUMENTATION.md)** | Complete API reference with examples |
| **[API Endpoints](API_ENDPOINTS.md)** | Comprehensive list of all API endpoints |
| **[Project Overview](PROJECT_OVERVIEW.md)** | Architecture and system design |
| **[Complete Workflow](COMPLETE_WORKFLOW.md)** | End-to-end workflow documentation |
| **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)** | Technical implementation details |
| **[Integration Complete](INTEGRATION_COMPLETE.md)** | Integration capabilities |

### Feature-Specific Documentation

| Feature | Documentation |
|---------|---------------|
| **Odoo Integration** | [Integration Guide](ODOO_INTEGRATION.md) · [Module Integration](ODOO_MODULE_INTEGRATION.md) · [API Integration](ODOO_API_INTEGRATION.md) · [Quick Start](ODOO_QUICK_START.md) · [Implementation](ODOO_IMPLEMENTATION_SUMMARY.md) |
| **RTSP Streaming** | [Optimization](RTSP_OPTIMIZATION.md) · [Frontend Fix](RTSP_FRONTEND_FIX.md) · [Video Preview](RTSP_VIDEO_PREVIEW_FIX.md) · [Troubleshooting](RTSP_TROUBLESHOOTING.md) · [Fix Summary](RTSP_FIX_SUMMARY.md) |
| **Advanced Features** | [Multi-Source Input](MULTI_SOURCE_INPUT.md) · [Performance Optimization](PERFORMANCE_OPTIMIZATION.md) · [Auto Resolution Scaling](AUTO_RESOLUTION_SCALING.md) · [Distance/Angle Enhancement](DISTANCE_ANGLE_ENHANCEMENT.md) |
| **Recognition System** | [Person Detection Accuracy](PERSON_DETECTION_ACCURACY.md) · [Tracking System](TRACKING_SYSTEM.md) · [Tracker Cleanup](TRACKER_CLEANUP_FIX.md) |
| **Configuration** | [Registration Fixes](REGISTRATION_FIXES.md) · [Frontend/Backend Verification](FRONTEND_BACKEND_VERIFICATION.md) |

---

## Highlights

### Core Recognition System
- **YOLOv8 Person Detection**: Fast and accurate person detection with GPU support
- **Face Recognition**: High-accuracy face matching using dlib encodings
- **Multi-Source Support**: Webcam, RTSP streams, video files, IP cameras
- **Real-time Tracking**: Track multiple persons simultaneously with confidence scores
- **Modern Web Interface**: Bootstrap 5 dark UI with live video, canvas overlays, and face registration

### Attendance Management System (NEW)
- **Automatic Attendance Marking**: Auto-mark attendance when faces are recognized
- **Duplicate Prevention**: Configurable time window to prevent duplicate entries
- **Complete REST API**: 25+ endpoints for all operations (persons, attendance, reports, config)
- **Token Authentication**: Secure API key-based authentication with granular permissions
- **Reporting & Analytics**: Daily, weekly, and monthly attendance reports with CSV/JSON export
- **Audit Trail**: Complete detection event logging and system monitoring
- **Person Management**: Full CRUD operations for managing persons and their details

## Project Structure

```
face_person_recognition/
├── backend/
│   ├── app.py                      # Main application with recognition engine
│   ├── attendance_system.py        # Core attendance management system (NEW)
│   ├── api_routes.py               # REST API endpoints (NEW)
│   ├── detector.py                 # YOLOv8 person detection wrapper
│   ├── recognizer.py               # Face recognition engine
│   ├── database.py                 # Face database management
│   ├── tracker.py                  # Multi-person tracking
│   ├── stream_state.py             # Stream state management
│   ├── detection_history.py        # Detection history database
│   ├── video_sources.py            # Video source management
│   ├── verify_setup.py             # Setup verification script (NEW)
│   ├── create_api_key.py           # API key generator (NEW)
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── data/
│   │   ├── attendance.db           # Attendance database (auto-created)
│   │   ├── detection_history.db    # Detection history (auto-created)
│   │   └── stream_state.json       # Stream state (auto-created)
│   └── faces/                      # Saved face thumbnails
├── frontend/
│   ├── index.html                  # Main web interface
│   ├── faces.html                  # Face registration interface
│   ├── script.js                   # Frontend JavaScript
│   └── style.css                   # Styles
├── test_api.py                     # API test suite (NEW)
├── API_DOCUMENTATION.md            # Complete API reference (NEW)
├── SETUP_GUIDE.md                  # Detailed setup guide (NEW)
├── docker-compose.yml
└── README.md
```

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Verify Setup

```bash
cd backend
python verify_setup.py
```

This verifies all dependencies, files, and database structure are correct.

### 3. Start the Server

```bash
cd backend
hypercorn app:app --bind 0.0.0.0:5000
```

### 4. Generate API Key

```bash
cd backend
python create_api_key.py
```

Save the generated API key securely - it won't be shown again!

### 5. Test the System

```bash
python test_api.py <YOUR_API_KEY>
```

### 6. Access the Web Interface

- **Main Interface**: http://localhost:5000
- **Face Registration**: http://localhost:5000/faces.html
- **API Health Check**: http://localhost:5000/api/v1/health

## API Endpoints

### Core Recognition Endpoints

| Method | Path             | Description                                        |
| ------ | ---------------- | -------------------------------------------------- |
| GET    | `/api/health`    | Health info + model status                         |
| POST   | `/api/register`  | Register face (name, image base64)                 |
| POST   | `/api/recognize` | Send frame for detection + recognition             |
| GET    | `/api/stream`    | MJPEG stream with overlays (webcam/RTSP)           |
| GET    | `/api/faces`     | List stored face metadata + thumbnails             |
| DELETE | `/api/clear`     | Remove all encodings and stored images             |
| GET    | `/api/events`    | Recent recognition timeline                        |

### Attendance Management API (/api/v1)

**Person Management**
- `POST /api/v1/persons` - Create new person
- `GET /api/v1/persons/{person_id}` - Get person details
- `GET /api/v1/persons` - List all persons
- `PUT /api/v1/persons/{person_id}` - Update person
- `DELETE /api/v1/persons/{person_id}` - Delete person

**Attendance Management**
- `POST /api/v1/attendance/mark` - Mark attendance (manual or auto)
- `POST /api/v1/attendance/{id}/checkout` - Mark checkout
- `GET /api/v1/attendance/today` - Get today's attendance
- `GET /api/v1/attendance/person/{person_id}` - Get person's attendance history
- `GET /api/v1/attendance/{id}` - Get specific attendance record
- `PUT /api/v1/attendance/{id}` - Update attendance record

**Reporting & Analytics**
- `GET /api/v1/reports/attendance` - Get attendance report (date range)
- `GET /api/v1/reports/daily-summary/{date}` - Get daily summary
- `GET /api/v1/reports/export` - Export to CSV or JSON

**System Configuration**
- `GET /api/v1/config` - Get configuration
- `POST /api/v1/config` - Update configuration

**Monitoring & Logging**
- `GET /api/v1/health` - System health check (no auth)
- `GET /api/v1/status` - System status (requires auth)
- `GET /api/v1/logs` - Get system logs

**Authentication**
- `POST /api/v1/auth/keys` - Create new API key

**External Integration (Placeholder)**
- `POST /api/v1/sync/odoo/pull` - Pull from Odoo (501 Not Implemented)
- `POST /api/v1/sync/odoo/push` - Push to Odoo (501 Not Implemented)
- `GET /api/v1/sync/status` - Get sync status (501 Not Implemented)

For complete API documentation with request/response examples, see **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)**

## Usage Examples

### Register a Person

**Via API:**
```bash
curl -X POST http://localhost:5000/api/v1/persons \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "EMP001",
    "name": "John Doe",
    "email": "john@company.com",
    "department": "Engineering"
  }'
```

**Via Web Interface:**
1. Open http://localhost:5000/faces.html
2. Click "Start Camera"
3. Click "Add Person"
4. Enter Person ID and Name
5. Click "Save Person"

### Mark Attendance

**Automatic (on recognition):**
- System automatically marks attendance when a registered face is recognized
- Duplicate prevention ensures only one entry per configurable time window

**Manual (via API):**
```bash
curl -X POST http://localhost:5000/api/v1/attendance/mark \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "EMP001",
    "person_name": "John Doe",
    "marked_by": "manual",
    "notes": "Late arrival"
  }'
```

### Get Today's Attendance

```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:5000/api/v1/attendance/today
```

### Generate Report

```bash
# Get monthly attendance report
curl -H "X-API-Key: your-api-key" \
  "http://localhost:5000/api/v1/reports/attendance?start_date=2025-01-01&end_date=2025-01-31"

# Export to CSV
curl -H "X-API-Key: your-api-key" \
  "http://localhost:5000/api/v1/reports/export?start_date=2025-01-01&end_date=2025-01-31&format=csv" \
  --output january_attendance.csv
```

### Check System Status

```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:5000/api/v1/status
```

## Configuration

### Attendance Settings

```bash
# Set duplicate prevention window (minutes)
curl -X POST http://localhost:5000/api/v1/config \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"key": "duplicate_window_minutes", "value": 10}'

# Enable/disable automatic marking
curl -X POST http://localhost:5000/api/v1/config \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"key": "auto_mark_enabled", "value": true}'
```

### Environment Variables

- `CAMERA_SOURCE` - Video source (default: "0" for webcam)
- `FACE_MODEL` - Face detection model: "hog" or "cnn" (default: "hog")
- `FACE_TOLERANCE` - Face matching tolerance (default: 0.45)
- `YOLO_DEVICE` - YOLO device: "cpu", "cuda", or "auto" (default: "auto")

## Security & Permissions

### API Permission Levels

- `person:read/write/delete` - Person management
- `attendance:read/write` - Attendance operations
- `reports:read/export` - Reporting and exports
- `config:read/write` - System configuration
- `logs:read` - System logs
- `system:read` - System status
- `admin` or `*` - All permissions

### Creating Restricted Keys

```bash
# Read-only key for mobile app
curl -X POST http://localhost:5000/api/v1/auth/keys \
  -H "X-API-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mobile App Read-Only",
    "permissions": ["attendance:read", "person:read"],
    "expires_days": 90
  }'
```

## Database Schema

The system uses SQLite with the following tables:

- **persons** - Registered persons with details
- **attendance** - Attendance records (check-in, check-out, duration)
- **detection_events** - Audit trail of all face detection events
- **system_config** - System configuration parameters
- **api_keys** - API authentication keys
- **system_logs** - System activity logs

## Troubleshooting

### API Key Errors

Ensure you're passing the key in the header: `-H "X-API-Key: your-key"`

### Attendance Not Auto-Marking

1. Check if auto-marking is enabled:
   ```bash
   curl -H "X-API-Key: your-key" \
     "http://localhost:5000/api/v1/config?key=auto_mark_enabled"
   ```
2. Verify the person has a `person_id` in the database
3. Check system logs for errors

### Duplicate Entries

Increase the duplicate prevention window:
```bash
curl -X POST http://localhost:5000/api/v1/config \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"key": "duplicate_window_minutes", "value": 15}'
```

## Documentation

- **Setup Guide**: [SETUP_GUIDE.md](SETUP_GUIDE.md) - Detailed setup and operational guide
- **API Reference**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Complete API documentation with examples

## Running with Docker

```bash
docker-compose up --build
```

Environment variables (defaults shown):
```
CAMERA_SOURCE=0        # Webcam index or RTSP URL
FACE_MODEL=hog         # hog or cnn
FACE_TOLERANCE=0.45    # Matching tolerance
YOLO_DEVICE=auto       # auto|cpu|cuda:0
```

For GPU support, install nvidia-container-toolkit and set `YOLO_DEVICE=cuda:0`

## What's New

### Attendance Management System v1.0

**Added:**
- ✅ Complete REST API (25+ endpoints)
- ✅ Token-based authentication with permissions
- ✅ Automatic attendance marking on recognition
- ✅ Duplicate prevention with configurable window
- ✅ Reporting and analytics (daily, weekly, monthly)
- ✅ CSV/JSON export functionality
- ✅ Person management system
- ✅ System configuration API
- ✅ Audit trail and logging
- ✅ Setup verification and test scripts
- ✅ Complete documentation

**Unchanged (Core Recognition):**
- ✅ YOLOv8 person detection
- ✅ Face recognition with dlib
- ✅ Person tracking
- ✅ Multi-source support
- ✅ Web interface

## Support

For issues or questions:
1. Check system logs: `GET /api/v1/logs`
2. Verify system status: `GET /api/v1/status`
3. Run test suite: `python test_api.py <API_KEY>`
4. Review [SETUP_GUIDE.md](SETUP_GUIDE.md) and [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
