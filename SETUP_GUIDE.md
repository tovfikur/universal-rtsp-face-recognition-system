# Attendance Management System - Setup Guide

## Quick Start

### 1. Install Dependencies

All dependencies should already be installed from the original face recognition system. No additional packages are required.

### 2. Start the Server

```bash
cd backend
hypercorn app:app --bind 0.0.0.0:5000
```

The system will automatically:
- Initialize the attendance database
- Register all API routes at `/api/v1`
- Start the recognition and snapshot analysis threads
- Load existing persons and faces from the database

### 3. Generate Initial API Key

On first run, you'll need to create an initial API key to access the system.

**Method 1: Using Python Console**

```python
from attendance_system import AttendanceSystem
from pathlib import Path

# Initialize system
attendance_system = AttendanceSystem(Path("data/attendance.db"))

# Create admin key
result = attendance_system.create_api_key(
    name="Admin Master Key",
    permissions=["*"],  # All permissions
    expires_days=None   # Never expires
)

print(f"API Key: {result['api_key']}")
print("⚠️ Save this key securely - it won't be shown again!")
```

**Method 2: Directly via API (if you have temporary access)**

```bash
curl -X POST http://localhost:5000/api/v1/auth/keys \
  -H "X-API-Key: temporary-bootstrap-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Admin Master Key",
    "permissions": ["*"],
    "expires_days": null
  }'
```

### 4. Test the API

**Health Check (No Auth Required)**

```bash
curl http://localhost:5000/api/v1/health
```

Expected response:
```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00",
  "version": "1.0.0"
}
```

**Get System Status (Auth Required)**

```bash
curl -H "X-API-Key: your-api-key-here" \
  http://localhost:5000/api/v1/status
```

### 5. Create Your First Person

```bash
curl -X POST http://localhost:5000/api/v1/persons \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "EMP001",
    "name": "John Doe",
    "email": "john@company.com",
    "department": "Engineering",
    "position": "Developer"
  }'
```

### 6. Register Face (Using Web Interface)

1. Open your browser to `http://localhost:5000`
2. Click "Start Camera"
3. Click "Add Person"
4. Enter the same Person ID and Name as created above
5. Click "Save Person"

The system will automatically:
- Register the face in the recognition system
- Link it to the person in the attendance database
- Start tracking attendance automatically

---

## System Architecture

### Components

1. **Face Recognition Engine** (Original)
   - YOLOv8 person detection
   - Face recognition with dlib
   - Person tracking

2. **Attendance System** (New)
   - SQLite database for attendance records
   - API-driven person and attendance management
   - Automatic attendance marking on recognition
   - Reporting and analytics

3. **API Layer** (New)
   - RESTful API at `/api/v1`
   - Token-based authentication
   - Permission-based access control

### Data Flow

```
Camera/RTSP Stream
    ↓
Person Detection (YOLOv8)
    ↓
Face Recognition (dlib)
    ↓
Person Matching
    ↓
Automatic Attendance Marking ← API: Manual Attendance
    ↓
Attendance Database
    ↓
API: Reports & Export
```

---

## Database Structure

The system creates an `attendance.db` SQLite database with the following tables:

### persons
Stores all registered persons with their details.

### attendance
Records all attendance entries (check-in, check-out, duration).

### detection_events
Audit trail of all face detection events.

### system_config
System configuration parameters.

### api_keys
API authentication keys.

### system_logs
System activity logs.

---

## Configuration

### Attendance Settings

You can configure attendance behavior via the API:

```bash
# Set duplicate prevention window
curl -X POST http://localhost:5000/api/v1/config \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "duplicate_window_minutes",
    "value": 10,
    "description": "Prevent duplicate attendance within 10 minutes"
  }'

# Enable/disable automatic marking
curl -X POST http://localhost:5000/api/v1/config \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "auto_mark_enabled",
    "value": true,
    "description": "Enable automatic attendance marking"
  }'
```

### Working Hours

```bash
curl -X POST http://localhost:5000/api/v1/config \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "working_hours_start",
    "value": "09:00",
    "description": "Working hours start time"
  }'
```

---

## API Permission Levels

### Available Permissions

- `person:read` - View person data
- `person:write` - Create/update persons
- `person:delete` - Delete persons
- `attendance:read` - View attendance records
- `attendance:write` - Mark/edit attendance
- `reports:read` - Generate reports
- `reports:export` - Export data
- `config:read` - View configuration
- `config:write` - Update configuration
- `logs:read` - View system logs
- `system:read` - View system status
- `detection:write` - Log detection events (internal)
- `sync:read` - View sync status
- `sync:write` - Perform sync operations
- `admin` - All permissions
- `*` - Wildcard (all permissions)

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

# Full attendance management key
curl -X POST http://localhost:5000/api/v1/auth/keys \
  -H "X-API-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Attendance Manager",
    "permissions": [
      "attendance:read",
      "attendance:write",
      "person:read",
      "reports:read",
      "reports:export"
    ],
    "expires_days": 365
  }'
```

---

## Common Operations

### Daily Attendance Workflow

**1. Get Today's Attendance**
```bash
curl -H "X-API-Key: your-key" \
  http://localhost:5000/api/v1/attendance/today
```

**2. Manual Check-In (if needed)**
```bash
curl -X POST http://localhost:5000/api/v1/attendance/mark \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "EMP001",
    "person_name": "John Doe",
    "marked_by": "manual",
    "notes": "Forgot to scan"
  }'
```

**3. Mark Check-Out**
```bash
curl -X POST http://localhost:5000/api/v1/attendance/123/checkout \
  -H "X-API-Key: your-key"
```

**4. Get Daily Summary**
```bash
curl -H "X-API-Key: your-key" \
  http://localhost:5000/api/v1/reports/daily-summary/2025-01-15
```

### Monthly Reporting

**1. Generate Report**
```bash
curl -H "X-API-Key: your-key" \
  "http://localhost:5000/api/v1/reports/attendance?start_date=2025-01-01&end_date=2025-01-31"
```

**2. Export to CSV**
```bash
curl -H "X-API-Key: your-key" \
  "http://localhost:5000/api/v1/reports/export?start_date=2025-01-01&end_date=2025-01-31&format=csv" \
  --output january_attendance.csv
```

### Person Management

**1. List All Active Persons**
```bash
curl -H "X-API-Key: your-key" \
  "http://localhost:5000/api/v1/persons?status=active&limit=100"
```

**2. Update Person Details**
```bash
curl -X PUT http://localhost:5000/api/v1/persons/EMP001 \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "department": "Operations",
    "position": "Senior Developer"
  }'
```

**3. Get Person Attendance History**
```bash
curl -H "X-API-Key: your-key" \
  "http://localhost:5000/api/v1/attendance/person/EMP001?start_date=2025-01-01&end_date=2025-01-31"
```

---

## Monitoring & Debugging

### View System Logs

```bash
# All logs
curl -H "X-API-Key: your-key" \
  "http://localhost:5000/api/v1/logs?limit=50"

# Only errors
curl -H "X-API-Key: your-key" \
  "http://localhost:5000/api/v1/logs?level=error&limit=50"

# Attendance category
curl -H "X-API-Key: your-key" \
  "http://localhost:5000/api/v1/logs?category=attendance&limit=50"
```

### Check System Status

```bash
curl -H "X-API-Key: your-key" \
  http://localhost:5000/api/v1/status
```

This shows:
- Background recognition status
- Snapshot analysis status
- Active video stream
- Current source

---

## Integration with External Systems

### Placeholder for Odoo Integration

The API includes placeholder endpoints for future Odoo integration:

- `POST /api/v1/sync/odoo/pull` - Pull employee data from Odoo
- `POST /api/v1/sync/odoo/push` - Push attendance data to Odoo
- `GET /api/v1/sync/status` - Get sync status

These endpoints currently return HTTP 501 (Not Implemented) but are reserved for future use.

### Custom Integration

You can integrate with any system using the RESTful API. Common integration patterns:

1. **Pull Model**: External system periodically fetches attendance data via API
2. **Push Model**: Setup webhooks (to be implemented) to notify external systems
3. **Sync Model**: Bi-directional sync using the sync endpoints

---

## Security Best Practices

1. **Use HTTPS in Production**
   - Never transmit API keys over unencrypted connections
   - Use a reverse proxy (nginx, Apache) with SSL/TLS

2. **Rotate API Keys Regularly**
   - Create new keys
   - Update client applications
   - Delete old keys

3. **Principle of Least Privilege**
   - Give clients only the permissions they need
   - Use separate keys for different applications

4. **Monitor API Usage**
   - Check logs regularly
   - Look for unusual patterns
   - Implement rate limiting if needed

5. **Backup Database**
   - Regular backups of `attendance.db`
   - Store backups securely
   - Test restore procedures

---

## Troubleshooting

### Issue: "API key required" error

**Solution:** Ensure you're passing the API key in the header:
```bash
curl -H "X-API-Key: your-key-here" http://localhost:5000/api/v1/...
```

### Issue: "Invalid or expired API key"

**Solution:**
1. Check if the key has expired
2. Verify you're using the correct key
3. Ensure the key has the required permission

### Issue: Attendance not being marked automatically

**Solution:**
1. Check if `auto_mark_enabled` is true:
   ```bash
   curl -H "X-API-Key: your-key" \
     "http://localhost:5000/api/v1/config?key=auto_mark_enabled"
   ```
2. Verify the person has a face registered
3. Check system logs for recognition errors

### Issue: Duplicate attendance entries

**Solution:** Adjust the duplicate prevention window:
```bash
curl -X POST http://localhost:5000/api/v1/config \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "duplicate_window_minutes",
    "value": 15
  }'
```

---

## Performance Tuning

### For High-Traffic Environments

1. **Increase worker processes** (hypercorn)
   ```bash
   hypercorn app:app --bind 0.0.0.0:5000 --workers 4
   ```

2. **Use connection pooling** for database access

3. **Implement caching** for frequently accessed data

4. **Use a reverse proxy** (nginx) for load balancing

### Database Optimization

The system automatically creates indexes on:
- `attendance(person_id, date)`
- `attendance(date)`
- `detection_events(timestamp)`
- `detection_events(person_id)`

For large datasets, consider:
- Regular VACUUM operations
- Archive old records
- Partition tables by date

---

## Support

For detailed API documentation, see `API_DOCUMENTATION.md`

For issues or questions:
1. Check system logs: `/api/v1/logs`
2. Verify system status: `/api/v1/status`
3. Review this setup guide
4. Check the API documentation

---

## What's New

### Attendance Management System v1.0

**New Features:**
- ✅ Complete REST API for all operations
- ✅ Token-based authentication with permissions
- ✅ Automatic attendance marking on face recognition
- ✅ Duplicate prevention with configurable time window
- ✅ Comprehensive reporting and analytics
- ✅ CSV/JSON export functionality
- ✅ Person management system
- ✅ System configuration API
- ✅ Audit trail with detection events
- ✅ System logs and monitoring
- ✅ Placeholder for Odoo integration

**Unchanged (Core Recognition System):**
- ✅ YOLOv8 person detection
- ✅ Face recognition with dlib
- ✅ Person tracking
- ✅ Multi-source support (webcam, RTSP)
- ✅ Web interface for face registration
- ✅ Real-time video preview
- ✅ Snapshot analysis

The core recognition behavior remains unchanged - we've added a complete API-driven attendance layer on top of it.
