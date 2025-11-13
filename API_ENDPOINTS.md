# Face Attendance API - Complete Endpoint Reference

## Base URL
```
http://192.168.50.152:5000
```

## Authentication

All API endpoints (except `/api/v1/health`) require authentication using one of these methods:

**Method 1: X-API-Key Header**
```http
X-API-Key: your_api_key_here
```

**Method 2: Bearer Token**
```http
Authorization: Bearer your_api_key_here
```

---

## 📋 Table of Contents

1. [Person Management](#person-management)
2. [Face Registration](#face-registration)
3. [Attendance Management](#attendance-management)
4. [Reports & Analytics](#reports--analytics)
5. [API Keys Management](#api-keys-management)
6. [System Monitoring](#system-monitoring)
7. [Configuration](#configuration)

---

# Person Management

## 1. List All Persons

**Endpoint:** `GET /api/v1/persons`

**Description:** Retrieve a list of all persons in the attendance system.

**Authentication:** Required (`person:read` permission)

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | string | No | `active` | Filter by status: `active`, `inactive`, `deleted`, `all` |
| `limit` | integer | No | `100` | Maximum number of records to return |
| `offset` | integer | No | `0` | Number of records to skip (for pagination) |

**Request Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://192.168.50.152:5000/api/v1/persons?status=active&limit=50"
```

**Response 200 - Success:**
```json
{
  "success": true,
  "data": {
    "persons": [
      {
        "person_id": "EMP001",
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "+1-555-0123",
        "department": "Engineering",
        "position": "Senior Developer",
        "status": "active",
        "created_at": "2025-01-10T09:00:00",
        "updated_at": "2025-01-15T14:30:00",
        "metadata": {
          "face_registered": true,
          "face_count": 3,
          "last_attendance": "2025-01-15T08:30:00"
        }
      },
      {
        "person_id": "EMP002",
        "name": "Jane Smith",
        "email": "jane.smith@example.com",
        "phone": "+1-555-0124",
        "department": "Marketing",
        "position": "Marketing Manager",
        "status": "active",
        "created_at": "2025-01-12T10:15:00",
        "updated_at": "2025-01-15T09:00:00",
        "metadata": {
          "face_registered": false
        }
      }
    ],
    "total": 2,
    "limit": 50,
    "offset": 0
  }
}
```

**Response 401 - Unauthorized:**
```json
{
  "success": false,
  "error": "Unauthorized",
  "message": "Invalid or missing API key"
}
```

---

## 2. Get Person Details

**Endpoint:** `GET /api/v1/persons/{person_id}`

**Description:** Retrieve detailed information about a specific person.

**Authentication:** Required (`person:read` permission)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `person_id` | string | Yes | Unique person identifier |

**Request Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://192.168.50.152:5000/api/v1/persons/EMP001"
```

**Response 200 - Success:**
```json
{
  "success": true,
  "data": {
    "person": {
      "person_id": "EMP001",
      "name": "John Doe",
      "email": "john.doe@example.com",
      "phone": "+1-555-0123",
      "department": "Engineering",
      "position": "Senior Developer",
      "status": "active",
      "created_at": "2025-01-10T09:00:00",
      "updated_at": "2025-01-15T14:30:00",
      "metadata": {
        "face_registered": true,
        "face_count": 3,
        "face_images": [
          "/data/faces/John_Doe_1.jpg",
          "/data/faces/John_Doe_2.jpg",
          "/data/faces/John_Doe_3.jpg"
        ],
        "registered_via": "api",
        "last_attendance": "2025-01-15T08:30:00",
        "total_attendance_days": 45
      }
    }
  }
}
```

**Response 404 - Not Found:**
```json
{
  "success": false,
  "error": "Person not found",
  "message": "Person with ID EMP001 not found"
}
```

---

## 3. Create Person

**Endpoint:** `POST /api/v1/persons`

**Description:** Create a new person in the attendance system.

**Authentication:** Required (`person:write` permission)

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `person_id` | string | Yes | Unique identifier (e.g., employee ID, student ID) |
| `name` | string | Yes | Full name of the person |
| `email` | string | No | Email address |
| `phone` | string | No | Phone number |
| `department` | string | No | Department name |
| `position` | string | No | Job title or position |
| `status` | string | No | Status: `active` (default), `inactive` |
| `metadata` | object | No | Additional custom data (JSON object) |

**Request Example:**
```bash
curl -X POST "http://192.168.50.152:5000/api/v1/persons" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "EMP003",
    "name": "Alice Johnson",
    "email": "alice.johnson@example.com",
    "phone": "+1-555-0125",
    "department": "Sales",
    "position": "Sales Representative",
    "status": "active",
    "metadata": {
      "hire_date": "2025-01-15",
      "employee_type": "full-time"
    }
  }'
```

**Response 201 - Created:**
```json
{
  "success": true,
  "message": "Person created successfully",
  "data": {
    "person_id": "EMP003",
    "name": "Alice Johnson",
    "email": "alice.johnson@example.com",
    "phone": "+1-555-0125",
    "department": "Sales",
    "position": "Sales Representative",
    "status": "active",
    "created_at": "2025-01-15T15:00:00",
    "metadata": {
      "hire_date": "2025-01-15",
      "employee_type": "full-time"
    }
  }
}
```

**Response 400 - Bad Request:**
```json
{
  "success": false,
  "error": "Invalid request",
  "message": "person_id and name are required fields"
}
```

**Response 409 - Conflict:**
```json
{
  "success": false,
  "error": "Person already exists",
  "message": "Person with ID EMP003 already exists"
}
```

---

## 4. Update Person

**Endpoint:** `PUT /api/v1/persons/{person_id}`

**Description:** Update an existing person's information.

**Authentication:** Required (`person:write` permission)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `person_id` | string | Yes | Unique person identifier |

**Request Body:** (All fields optional, only include fields to update)

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Full name |
| `email` | string | Email address |
| `phone` | string | Phone number |
| `department` | string | Department name |
| `position` | string | Job title |
| `status` | string | Status: `active`, `inactive` |
| `metadata` | object | Additional custom data |

**Request Example:**
```bash
curl -X PUT "http://192.168.50.152:5000/api/v1/persons/EMP003" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "department": "Marketing",
    "position": "Marketing Specialist",
    "phone": "+1-555-0199"
  }'
```

**Response 200 - Success:**
```json
{
  "success": true,
  "message": "Person updated successfully",
  "data": {
    "person_id": "EMP003",
    "name": "Alice Johnson",
    "email": "alice.johnson@example.com",
    "phone": "+1-555-0199",
    "department": "Marketing",
    "position": "Marketing Specialist",
    "status": "active",
    "updated_at": "2025-01-15T15:30:00"
  }
}
```

**Response 404 - Not Found:**
```json
{
  "success": false,
  "error": "Person not found",
  "message": "Person with ID EMP003 not found"
}
```

---

## 5. Delete Person

**Endpoint:** `DELETE /api/v1/persons/{person_id}`

**Description:** Delete a person from the system (soft delete - marks as deleted, doesn't physically remove).

**Authentication:** Required (`person:write` permission)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `person_id` | string | Yes | Unique person identifier |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `hard_delete` | boolean | No | `false` | If `true`, permanently delete. If `false`, soft delete (mark as deleted) |

**Request Example:**
```bash
# Soft delete (default)
curl -X DELETE "http://192.168.50.152:5000/api/v1/persons/EMP003" \
  -H "Authorization: Bearer YOUR_API_KEY"

# Hard delete (permanent)
curl -X DELETE "http://192.168.50.152:5000/api/v1/persons/EMP003?hard_delete=true" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Response 200 - Success:**
```json
{
  "success": true,
  "message": "Person deleted successfully",
  "data": {
    "person_id": "EMP003",
    "deleted_at": "2025-01-15T16:00:00"
  }
}
```

**Response 404 - Not Found:**
```json
{
  "success": false,
  "error": "Person not found",
  "message": "Person with ID EMP003 not found"
}
```

---

# Face Registration

## 6. Register Face for Person

**Endpoint:** `POST /api/v1/persons/{person_id}/register-face`

**Description:** Register a face image for an existing person. This endpoint accepts a base64 encoded image, detects the face, creates a face encoding, and makes it immediately available for recognition.

**Authentication:** Required (`person:write` permission)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `person_id` | string | Yes | Unique person identifier |

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | string | Yes | Base64 encoded image data (with or without data URI prefix) |
| `force_update` | boolean | No | If `true`, allows updating existing face registration |

**Supported Image Formats:**
- JPEG / JPG
- PNG
- BMP

**Image Requirements:**
- Must contain exactly one visible face
- Face should be well-lit and front-facing
- Minimum face size: 50x50 pixels
- Recommended image size: 800x600 pixels
- Maximum file size: 5MB (before base64 encoding)

**Request Example:**
```bash
curl -X POST "http://192.168.50.152:5000/api/v1/persons/EMP001/register-face" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
    "force_update": false
  }'
```

**Python Example:**
```python
import base64
import requests

# Read image file
with open('face_photo.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

# Send to API
response = requests.post(
    'http://192.168.50.152:5000/api/v1/persons/EMP001/register-face',
    headers={
        'Authorization': 'Bearer YOUR_API_KEY',
        'Content-Type': 'application/json'
    },
    json={
        'image': image_data,
        'force_update': False
    }
)

result = response.json()
print(result)
```

**Response 201 - Success:**
```json
{
  "success": true,
  "message": "Face registered successfully for John Doe",
  "data": {
    "person_id": "EMP001",
    "name": "John Doe",
    "face_id": "2025-01-15T10:30:00",
    "image_path": "/data/faces/John_Doe_2025-01-15_10-30-00.jpg",
    "total_faces": 25
  }
}
```

**Response 404 - Person Not Found:**
```json
{
  "success": false,
  "error": "Person not found",
  "message": "Person with ID EMP001 not found"
}
```

**Response 400 - Missing Image:**
```json
{
  "success": false,
  "error": "Missing image data",
  "message": "image field is required in request body"
}
```

**Response 422 - No Face Detected:**
```json
{
  "success": false,
  "error": "No face detected",
  "message": "No face was detected in the provided image. Please ensure the image shows a clear, front-facing face."
}
```

**Response 422 - Cannot Encode Face:**
```json
{
  "success": false,
  "error": "Could not encode face",
  "message": "Face was detected but could not be encoded. Image quality may be too low."
}
```

**Response 422 - Invalid Image:**
```json
{
  "success": false,
  "error": "Invalid image data",
  "message": "Could not decode image. Please check the base64 encoding and image format."
}
```

---

# Attendance Management

## 7. List Attendance Records

**Endpoint:** `GET /api/v1/attendance`

**Description:** Retrieve attendance records with optional filtering by date range and person.

**Authentication:** Required (`attendance:read` permission)

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `start_date` | string | No | 30 days ago | Start date (YYYY-MM-DD) |
| `end_date` | string | No | Today | End date (YYYY-MM-DD) |
| `person_id` | string | No | - | Filter by specific person |
| `status` | string | No | `all` | Filter by status: `checked_in`, `checked_out`, `incomplete`, `all` |
| `limit` | integer | No | `100` | Maximum records to return |
| `offset` | integer | No | `0` | Number of records to skip |

**Request Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://192.168.50.152:5000/api/v1/attendance?start_date=2025-01-01&end_date=2025-01-31&limit=500"
```

**Response 200 - Success:**
```json
{
  "success": true,
  "data": {
    "records": [
      {
        "id": 1,
        "person_id": "EMP001",
        "person_name": "John Doe",
        "date": "2025-01-15",
        "check_in": "2025-01-15T08:30:00",
        "check_out": "2025-01-15T17:45:00",
        "duration_minutes": 555,
        "duration_hours": 9.25,
        "status": "checked_out",
        "source": "face",
        "confidence": 95.8,
        "marked_by": "auto",
        "notes": null,
        "created_at": "2025-01-15T08:30:05"
      },
      {
        "id": 2,
        "person_id": "EMP002",
        "person_name": "Jane Smith",
        "date": "2025-01-15",
        "check_in": "2025-01-15T09:00:00",
        "check_out": null,
        "duration_minutes": null,
        "duration_hours": null,
        "status": "checked_in",
        "source": "face",
        "confidence": 97.2,
        "marked_by": "auto",
        "notes": null,
        "created_at": "2025-01-15T09:00:03"
      }
    ],
    "total": 2,
    "limit": 500,
    "offset": 0,
    "date_range": {
      "start": "2025-01-01",
      "end": "2025-01-31"
    }
  }
}
```

---

## 8. Get Specific Attendance Record

**Endpoint:** `GET /api/v1/attendance/{id}`

**Description:** Retrieve details of a specific attendance record.

**Authentication:** Required (`attendance:read` permission)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Attendance record ID |

**Request Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://192.168.50.152:5000/api/v1/attendance/1"
```

**Response 200 - Success:**
```json
{
  "success": true,
  "data": {
    "record": {
      "id": 1,
      "person_id": "EMP001",
      "person_name": "John Doe",
      "date": "2025-01-15",
      "check_in": "2025-01-15T08:30:00",
      "check_out": "2025-01-15T17:45:00",
      "duration_minutes": 555,
      "duration_hours": 9.25,
      "status": "checked_out",
      "source": "face",
      "confidence": 95.8,
      "marked_by": "auto",
      "notes": null,
      "created_at": "2025-01-15T08:30:05",
      "updated_at": "2025-01-15T17:45:02"
    }
  }
}
```

**Response 404 - Not Found:**
```json
{
  "success": false,
  "error": "Attendance record not found",
  "message": "Attendance record with ID 1 not found"
}
```

---

## 9. Mark Attendance (Manual)

**Endpoint:** `POST /api/v1/attendance/mark`

**Description:** Manually mark attendance for a person.

**Authentication:** Required (`attendance:write` permission)

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `person_id` | string | Yes | Person identifier |
| `person_name` | string | No | Person name (if not provided, looked up from person_id) |
| `marked_by` | string | No | Who marked attendance: `manual`, `admin`, username |
| `notes` | string | No | Additional notes |
| `check_in_time` | string | No | Custom check-in time (ISO 8601 format), defaults to now |

**Request Example:**
```bash
curl -X POST "http://192.168.50.152:5000/api/v1/attendance/mark" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "EMP001",
    "marked_by": "admin",
    "notes": "Late arrival due to traffic"
  }'
```

**Response 201 - Created:**
```json
{
  "success": true,
  "message": "Attendance marked successfully",
  "data": {
    "id": 3,
    "person_id": "EMP001",
    "person_name": "John Doe",
    "date": "2025-01-15",
    "check_in": "2025-01-15T10:15:00",
    "status": "checked_in",
    "source": "manual",
    "marked_by": "admin",
    "notes": "Late arrival due to traffic"
  }
}
```

---

## 10. Mark Checkout

**Endpoint:** `POST /api/v1/attendance/{id}/checkout`

**Description:** Mark checkout for an existing attendance record.

**Authentication:** Required (`attendance:write` permission)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Attendance record ID |

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `check_out_time` | string | No | Custom checkout time (ISO 8601), defaults to now |
| `notes` | string | No | Additional notes |

**Request Example:**
```bash
curl -X POST "http://192.168.50.152:5000/api/v1/attendance/3/checkout" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Early departure - approved"
  }'
```

**Response 200 - Success:**
```json
{
  "success": true,
  "message": "Checkout marked successfully",
  "data": {
    "id": 3,
    "person_id": "EMP001",
    "person_name": "John Doe",
    "check_in": "2025-01-15T10:15:00",
    "check_out": "2025-01-15T16:00:00",
    "duration_minutes": 345,
    "duration_hours": 5.75,
    "status": "checked_out"
  }
}
```

---

# Reports & Analytics

## 11. Daily Summary Report

**Endpoint:** `GET /api/v1/reports/daily-summary/{date}`

**Description:** Get attendance summary for a specific date.

**Authentication:** Required (`reports:read` permission)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string | Yes | Date in YYYY-MM-DD format |

**Request Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://192.168.50.152:5000/api/v1/reports/daily-summary/2025-01-15"
```

**Response 200 - Success:**
```json
{
  "success": true,
  "data": {
    "date": "2025-01-15",
    "total_persons": 50,
    "present_count": 45,
    "absent_count": 5,
    "attendance_rate": 90.0,
    "avg_duration_hours": 8.5,
    "avg_confidence": 96.3,
    "earliest_checkin": "07:30:00",
    "latest_checkout": "19:45:00",
    "on_time_count": 40,
    "late_count": 5,
    "by_department": {
      "Engineering": 20,
      "Sales": 15,
      "Marketing": 10
    },
    "by_source": {
      "face": 43,
      "manual": 2
    }
  }
}
```

---

## 12. Monthly Summary Report

**Endpoint:** `GET /api/v1/reports/monthly-summary`

**Description:** Get attendance summary for a month.

**Authentication:** Required (`reports:read` permission)

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `year` | integer | No | Current year | Year (YYYY) |
| `month` | integer | No | Current month | Month (1-12) |

**Request Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://192.168.50.152:5000/api/v1/reports/monthly-summary?year=2025&month=1"
```

**Response 200 - Success:**
```json
{
  "success": true,
  "data": {
    "year": 2025,
    "month": 1,
    "month_name": "January",
    "total_working_days": 22,
    "total_persons": 50,
    "avg_attendance_rate": 92.5,
    "total_attendance_records": 1018,
    "avg_daily_present": 46,
    "top_performers": [
      {
        "person_id": "EMP001",
        "name": "John Doe",
        "attendance_days": 22,
        "attendance_rate": 100.0
      }
    ],
    "by_department": {
      "Engineering": {
        "present_days": 440,
        "avg_rate": 100.0
      },
      "Sales": {
        "present_days": 315,
        "avg_rate": 95.5
      }
    }
  }
}
```

---

# API Keys Management

## 13. List API Keys

**Endpoint:** `GET /api/v1/keys`

**Description:** List all API keys (without exposing actual key values).

**Authentication:** Required (`admin` permission)

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | string | No | `all` | Filter by status: `active`, `inactive`, `revoked`, `all` |
| `limit` | integer | No | `100` | Maximum records to return |

**Request Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://192.168.50.152:5000/api/v1/keys?status=active"
```

**Response 200 - Success:**
```json
{
  "success": true,
  "data": {
    "keys": [
      {
        "id": 1,
        "name": "Odoo Integration Key",
        "key_prefix": "sk_live_abc",
        "permissions": ["*"],
        "status": "active",
        "created_at": "2025-01-10T08:00:00",
        "last_used": "2025-01-15T14:30:00",
        "expires_at": null,
        "usage_count": 1523
      },
      {
        "id": 2,
        "name": "Mobile App Key",
        "key_prefix": "sk_live_xyz",
        "permissions": ["person:read", "attendance:read"],
        "status": "active",
        "created_at": "2025-01-12T09:00:00",
        "last_used": "2025-01-15T15:00:00",
        "expires_at": "2025-12-31T23:59:59",
        "usage_count": 89
      }
    ],
    "total": 2
  }
}
```

**Note:** Actual API key values are never returned by this endpoint for security reasons. Only metadata is shown.

---

# System Monitoring

## 14. Health Check

**Endpoint:** `GET /api/v1/health`

**Description:** Check if the API server is running and healthy.

**Authentication:** Not required (public endpoint)

**Request Example:**
```bash
curl "http://192.168.50.152:5000/api/v1/health"
```

**Response 200 - Healthy:**
```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2025-01-15T15:00:00",
  "version": "1.0.0",
  "uptime_seconds": 86400
}
```

---

## 15. System Status

**Endpoint:** `GET /api/v1/status`

**Description:** Get detailed system status including active services.

**Authentication:** Required (`admin` permission)

**Request Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://192.168.50.152:5000/api/v1/status"
```

**Response 200 - Success:**
```json
{
  "success": true,
  "data": {
    "api_server": "running",
    "background_recognition": true,
    "snapshot_analysis": true,
    "active_video_stream": true,
    "current_source": "camera_0",
    "fps": 28,
    "recognized_count": 45,
    "total_persons": 50,
    "total_faces": 75,
    "database": {
      "attendance_db": "connected",
      "faces_db": "loaded",
      "total_records": 1523
    },
    "uptime_seconds": 86400,
    "memory_usage_mb": 245.6,
    "cpu_usage_percent": 15.3
  }
}
```

---

## 16. System Logs

**Endpoint:** `GET /api/v1/logs`

**Description:** Retrieve system logs for monitoring and debugging.

**Authentication:** Required (`admin` permission)

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `level` | string | No | `all` | Filter by level: `debug`, `info`, `warning`, `error`, `all` |
| `category` | string | No | `all` | Filter by category: `api`, `sync`, `recognition`, `system`, `all` |
| `limit` | integer | No | `100` | Maximum logs to return |
| `offset` | integer | No | `0` | Number of logs to skip |

**Request Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://192.168.50.152:5000/api/v1/logs?level=error&limit=50"
```

**Response 200 - Success:**
```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "id": 1,
        "timestamp": "2025-01-15T10:30:00",
        "level": "error",
        "category": "recognition",
        "message": "Face detection failed for frame",
        "details": {
          "error": "Low light conditions",
          "frame_id": 12345
        }
      },
      {
        "id": 2,
        "timestamp": "2025-01-15T11:00:00",
        "level": "warning",
        "category": "api",
        "message": "Rate limit approaching",
        "details": {
          "requests": 950,
          "limit": 1000
          }
      }
    ],
    "total": 2,
    "limit": 50,
    "offset": 0
  }
}
```

---

# Configuration

## 17. Get Configuration

**Endpoint:** `GET /api/v1/config`

**Description:** Retrieve current system configuration.

**Authentication:** Required (`admin` permission)

**Request Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://192.168.50.152:5000/api/v1/config"
```

**Response 200 - Success:**
```json
{
  "success": true,
  "data": {
    "config": {
      "duplicate_window_minutes": 5,
      "auto_mark_enabled": true,
      "working_hours_start": "09:00",
      "working_hours_end": "18:00",
      "face_confidence_threshold": 0.6,
      "max_face_distance": 0.6,
      "snapshot_interval_seconds": 1.5,
      "attendance_grace_period_minutes": 15,
      "auto_checkout_enabled": false,
      "auto_checkout_time": "18:00"
    }
  }
}
```

---

## 18. Update Configuration

**Endpoint:** `POST /api/v1/config`

**Description:** Update system configuration settings.

**Authentication:** Required (`admin` permission)

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `key` | string | Yes | Configuration key to update |
| `value` | any | Yes | New value (type depends on key) |
| `description` | string | No | Description of the change |

**Request Example:**
```bash
curl -X POST "http://192.168.50.152:5000/api/v1/config" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "duplicate_window_minutes",
    "value": 10,
    "description": "Increased to prevent duplicates"
  }'
```

**Response 200 - Success:**
```json
{
  "success": true,
  "message": "Configuration updated successfully",
  "data": {
    "key": "duplicate_window_minutes",
    "old_value": 5,
    "new_value": 10,
    "updated_at": "2025-01-15T15:30:00"
  }
}
```

---

# Additional Endpoints

## 19. Get Registered Faces

**Endpoint:** `GET /api/faces`

**Description:** Get list of all registered faces from the face recognition database.

**Authentication:** Required (`person:read` permission)

**Request Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://192.168.50.152:5000/api/faces"
```

**Response 200 - Success:**
```json
{
  "success": true,
  "faces": [
    {
      "id": 1,
      "name": "John Doe",
      "person_id": "EMP001",
      "image_path": "/data/faces/John_Doe_1.jpg",
      "registered_at": "2025-01-10T09:00:00"
    },
    {
      "id": 2,
      "name": "John Doe",
      "person_id": "EMP001",
      "image_path": "/data/faces/John_Doe_2.jpg",
      "registered_at": "2025-01-15T10:30:00"
    }
  ],
  "total": 2
}
```

---

## 20. Get Current Camera Source

**Endpoint:** `GET /api/source`

**Description:** Get currently active camera/video source.

**Authentication:** Not required

**Request Example:**
```bash
curl "http://192.168.50.152:5000/api/source"
```

**Response 200 - Success:**
```json
{
  "success": true,
  "source": "0",
  "type": "camera",
  "status": "active"
}
```

---

# Error Responses

All endpoints follow a consistent error response format:

**Error Response Structure:**
```json
{
  "success": false,
  "error": "Error type",
  "message": "Detailed error message",
  "details": {
    "field": "Additional error details (optional)"
  }
}
```

**Common HTTP Status Codes:**

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |

---

# Rate Limiting

**Current Limits:**
- 1000 requests per hour per API key
- 50 face registration requests per hour
- No limit on health check endpoint

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 845
X-RateLimit-Reset: 1642262400
```

---

# Webhooks (Future Feature)

Webhooks are planned but not yet implemented. Future webhook events will include:

- `person.created` - When a new person is created
- `person.updated` - When person details are updated
- `face.registered` - When a face is registered
- `attendance.marked` - When attendance is marked
- `attendance.checkout` - When checkout is recorded

---

# Best Practices

1. **Authentication:** Always use HTTPS in production and keep API keys secure
2. **Pagination:** Use `limit` and `offset` for large datasets
3. **Date Ranges:** Specify date ranges for attendance queries to improve performance
4. **Error Handling:** Always check the `success` field in responses
5. **Face Registration:** Resize images to ~800x600px before sending to reduce latency
6. **Rate Limits:** Implement exponential backoff when rate limited

---

# Support & Documentation

- **Base URL:** http://192.168.50.152:5000
- **API Version:** v1
- **Documentation:** See ODOO_API_INTEGRATION.md for detailed integration guide
- **GitHub:** (if applicable)

---

**Last Updated:** 2025-01-15
**API Version:** 1.0.0
