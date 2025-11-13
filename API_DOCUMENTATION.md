# Attendance Management System - API Documentation

## Overview

This is a complete API-driven attendance management system built on top of a facial recognition engine. All operations are controlled through RESTful APIs with token-based authentication.

**Base URL:** `http://your-server:5000/api/v1`

**Authentication:** All endpoints (except `/health`) require an API key passed in the `X-API-Key` header.

```http
X-API-Key: your-api-key-here
```

---

## Table of Contents

1. [Authentication](#authentication)
2. [Person Management](#person-management)
3. [Attendance Management](#attendance-management)
4. [Reporting & Analytics](#reporting--analytics)
5. [System Configuration](#system-configuration)
6. [Logging & Monitoring](#logging--monitoring)
7. [External Sync (Placeholder)](#external-sync)
8. [Response Formats](#response-formats)
9. [Error Codes](#error-codes)

---

## Authentication

### Create API Key

**Endpoint:** `POST /api/v1/auth/keys`

**Permission Required:** `admin`

**Description:** Generate a new API key for system access.

**Request Body:**
```json
{
  "name": "Mobile App Key",
  "permissions": ["attendance:read", "attendance:write", "person:read"],
  "expires_days": 365
}
```

**Response:**
```json
{
  "success": true,
  "api_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "API key created successfully. Store it securely - it won't be shown again."
}
```

**Available Permissions:**
- `person:read`, `person:write`, `person:delete`
- `attendance:read`, `attendance:write`
- `reports:read`, `reports:export`
- `config:read`, `config:write`
- `logs:read`
- `system:read`, `system:write`
- `detection:write`
- `sync:read`, `sync:write`
- `admin` (all permissions)
- `*` (wildcard - all permissions)

---

## Person Management

### Create Person

**Endpoint:** `POST /api/v1/persons`

**Permission:** `person:write`

**Description:** Register a new person in the system.

**Request Body:**
```json
{
  "person_id": "EMP001",
  "name": "John Doe",
  "email": "john@example.com",
  "department": "Engineering",
  "position": "Software Developer",
  "phone": "+1234567890",
  "metadata": {
    "employee_type": "full-time",
    "shift": "morning"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Person John Doe added successfully",
  "person_id": "EMP001"
}
```

---

### Get Person

**Endpoint:** `GET /api/v1/persons/{person_id}`

**Permission:** `person:read`

**Description:** Retrieve details of a specific person.

**Response:**
```json
{
  "success": true,
  "person": {
    "id": 1,
    "person_id": "EMP001",
    "name": "John Doe",
    "email": "john@example.com",
    "department": "Engineering",
    "position": "Software Developer",
    "phone": "+1234567890",
    "status": "active",
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:30:00",
    "metadata": {
      "employee_type": "full-time"
    }
  }
}
```

---

### List Persons

**Endpoint:** `GET /api/v1/persons`

**Permission:** `person:read`

**Query Parameters:**
- `status` (optional): Filter by status (`active`, `inactive`, `deleted`)
- `limit` (optional): Results per page (default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
{
  "success": true,
  "count": 50,
  "limit": 100,
  "offset": 0,
  "persons": [
    {
      "id": 1,
      "person_id": "EMP001",
      "name": "John Doe",
      "department": "Engineering",
      "status": "active"
    }
  ]
}
```

---

### Update Person

**Endpoint:** `PUT /api/v1/persons/{person_id}`

**Permission:** `person:write`

**Request Body:**
```json
{
  "name": "John Smith",
  "email": "john.smith@example.com",
  "department": "Operations",
  "status": "active"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Person updated successfully"
}
```

---

### Delete Person

**Endpoint:** `DELETE /api/v1/persons/{person_id}`

**Permission:** `person:delete`

**Description:** Soft delete a person (sets status to 'deleted').

**Response:**
```json
{
  "success": true,
  "message": "Person deleted successfully"
}
```

---

## Attendance Management

### Mark Attendance

**Endpoint:** `POST /api/v1/attendance/mark`

**Permission:** `attendance:write`

**Description:** Manually mark attendance for a person.

**Request Body:**
```json
{
  "person_id": "EMP001",
  "person_name": "John Doe",
  "confidence": 0.95,
  "source": "camera_1",
  "marked_by": "manual",
  "location": "Main Entrance",
  "notes": "Early arrival",
  "metadata": {
    "temperature": "36.5C"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Attendance marked successfully",
  "attendance_id": 123,
  "check_in": "2025-01-15T09:00:00"
}
```

**Note:** The system automatically prevents duplicate entries within a configurable time window (default: 5 minutes).

---

### Mark Checkout

**Endpoint:** `POST /api/v1/attendance/{attendance_id}/checkout`

**Permission:** `attendance:write`

**Description:** Mark checkout time for an attendance record.

**Response:**
```json
{
  "success": true,
  "message": "Checkout marked successfully",
  "check_out": "2025-01-15T18:00:00",
  "duration_minutes": 540
}
```

---

### Get Attendance Record

**Endpoint:** `GET /api/v1/attendance/{attendance_id}`

**Permission:** `attendance:read`

**Response:**
```json
{
  "success": true,
  "attendance": {
    "id": 123,
    "person_id": "EMP001",
    "person_name": "John Doe",
    "check_in": "2025-01-15T09:00:00",
    "check_out": "2025-01-15T18:00:00",
    "date": "2025-01-15",
    "duration_minutes": 540,
    "source": "camera_1",
    "confidence": 0.95,
    "status": "present",
    "marked_by": "auto"
  }
}
```

---

### Get Daily Attendance

**Endpoint:** `GET /api/v1/attendance/daily/{date}`

**Permission:** `attendance:read`

**Description:** Get all attendance records for a specific date.

**URL Parameter:**
- `date`: Date in YYYY-MM-DD format

**Response:**
```json
{
  "success": true,
  "date": "2025-01-15",
  "count": 45,
  "attendance": [
    {
      "id": 123,
      "person_id": "EMP001",
      "person_name": "John Doe",
      "check_in": "2025-01-15T09:00:00",
      "check_out": "2025-01-15T18:00:00"
    }
  ]
}
```

---

### Get Today's Attendance

**Endpoint:** `GET /api/v1/attendance/today`

**Permission:** `attendance:read`

**Description:** Get all attendance records for today.

**Response:** Same as Get Daily Attendance

---

### Get Person Attendance History

**Endpoint:** `GET /api/v1/attendance/person/{person_id}`

**Permission:** `attendance:read`

**Query Parameters:**
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)

**Response:**
```json
{
  "success": true,
  "person_id": "EMP001",
  "count": 20,
  "attendance": [
    {
      "id": 123,
      "check_in": "2025-01-15T09:00:00",
      "check_out": "2025-01-15T18:00:00",
      "duration_minutes": 540
    }
  ]
}
```

---

## Reporting & Analytics

### Generate Attendance Report

**Endpoint:** `GET /api/v1/reports/attendance`

**Permission:** `reports:read`

**Query Parameters:**
- `start_date` (required): Start date (YYYY-MM-DD)
- `end_date` (required): End date (YYYY-MM-DD)
- `person_id` (optional): Filter by specific person

**Response:**
```json
{
  "success": true,
  "period": {
    "start": "2025-01-01",
    "end": "2025-01-31"
  },
  "report": [
    {
      "person_id": "EMP001",
      "person_name": "John Doe",
      "total_days": 20,
      "present_days": 18,
      "absent_days": 2,
      "avg_duration_minutes": 510,
      "total_duration_minutes": 9180
    }
  ]
}
```

---

### Get Daily Summary

**Endpoint:** `GET /api/v1/reports/daily-summary/{date}`

**Permission:** `reports:read`

**Description:** Get statistical summary for a specific date.

**Response:**
```json
{
  "success": true,
  "date": "2025-01-15",
  "total_records": 45,
  "unique_persons": 45,
  "present": 45,
  "avg_confidence": 0.92,
  "avg_duration_minutes": 520
}
```

---

### Export Attendance Data

**Endpoint:** `GET /api/v1/reports/export`

**Permission:** `reports:export`

**Query Parameters:**
- `start_date` (required): Start date (YYYY-MM-DD)
- `end_date` (required): End date (YYYY-MM-DD)
- `format` (optional): Export format (`csv` or `json`, default: `csv`)
- `person_id` (optional): Filter by specific person

**Response:**
- **CSV:** Returns a downloadable CSV file
- **JSON:** Returns JSON data (same as attendance report)

**Example CSV Output:**
```csv
Person ID,Person Name,Total Days,Present Days,Absent Days,Avg Duration (mins),Total Duration (mins)
EMP001,John Doe,20,18,2,510,9180
EMP002,Jane Smith,20,20,0,525,10500
```

---

## System Configuration

### Get Configuration

**Endpoint:** `GET /api/v1/config`

**Permission:** `config:read`

**Query Parameters:**
- `key` (optional): Get specific configuration key

**Response (all config):**
```json
{
  "success": true,
  "config": {
    "duplicate_window_minutes": {
      "value": 5,
      "description": "Prevent duplicate attendance within X minutes"
    },
    "auto_mark_enabled": {
      "value": true,
      "description": "Enable automatic attendance marking"
    },
    "working_hours_start": {
      "value": "09:00",
      "description": "Working hours start time"
    }
  }
}
```

**Response (specific key):**
```json
{
  "success": true,
  "config": {
    "key": "duplicate_window_minutes",
    "value": 5,
    "description": "Prevent duplicate attendance within X minutes"
  }
}
```

---

### Update Configuration

**Endpoint:** `POST /api/v1/config`

**Permission:** `config:write`

**Request Body:**
```json
{
  "key": "duplicate_window_minutes",
  "value": 10,
  "description": "Prevent duplicate attendance within X minutes"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Configuration updated"
}
```

---

## Logging & Monitoring

### Get System Logs

**Endpoint:** `GET /api/v1/logs`

**Permission:** `logs:read`

**Query Parameters:**
- `level` (optional): Filter by level (`info`, `warning`, `error`)
- `category` (optional): Filter by category
- `limit` (optional): Number of logs (default: 100)

**Response:**
```json
{
  "success": true,
  "count": 50,
  "logs": [
    {
      "id": 1,
      "level": "info",
      "category": "attendance",
      "message": "Marked attendance for John Doe (EMP001)",
      "details": {
        "confidence": 0.95
      },
      "timestamp": "2025-01-15T09:00:00"
    }
  ]
}
```

---

### Health Check

**Endpoint:** `GET /api/v1/health`

**Permission:** None (public)

**Description:** Check if the system is running.

**Response:**
```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00",
  "version": "1.0.0"
}
```

---

### System Status

**Endpoint:** `GET /api/v1/status`

**Permission:** `system:read`

**Description:** Get detailed system status including recognition threads.

**Response:**
```json
{
  "success": true,
  "system": {
    "background_recognition": true,
    "snapshot_analysis": true,
    "stream_active": true,
    "current_source": "rtsp://192.168.1.100:554/stream"
  },
  "timestamp": "2025-01-15T10:30:00"
}
```

---

## External Sync

### Odoo Sync Pull (Placeholder)

**Endpoint:** `POST /api/v1/sync/odoo/pull`

**Permission:** `sync:write`

**Status:** Not yet implemented (501)

**Description:** Reserved for future Odoo integration to pull employee data.

---

### Odoo Sync Push (Placeholder)

**Endpoint:** `POST /api/v1/sync/odoo/push`

**Permission:** `sync:write`

**Status:** Not yet implemented (501)

**Description:** Reserved for future Odoo integration to push attendance data.

---

### Get Sync Status

**Endpoint:** `GET /api/v1/sync/status`

**Permission:** `sync:read`

**Response:**
```json
{
  "success": true,
  "sync": {
    "odoo": {
      "enabled": false,
      "last_sync": null,
      "status": "not_configured"
    }
  }
}
```

---

## Response Formats

### Success Response

```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {}
}
```

### Error Response

```json
{
  "success": false,
  "error": "Error type",
  "message": "Detailed error message"
}
```

---

## Error Codes

| HTTP Code | Meaning |
|-----------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (missing/invalid parameters) |
| 401 | Unauthorized (missing API key) |
| 403 | Forbidden (invalid API key or insufficient permissions) |
| 404 | Not Found |
| 422 | Unprocessable Entity (validation error) |
| 500 | Internal Server Error |
| 501 | Not Implemented (placeholder endpoints) |

---

## Quick Start Example

### 1. Create API Key (Admin Access Required)

```bash
curl -X POST http://localhost:5000/api/v1/auth/keys \
  -H "X-API-Key: initial-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My App",
    "permissions": ["*"],
    "expires_days": 365
  }'
```

### 2. Add a Person

```bash
curl -X POST http://localhost:5000/api/v1/persons \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "EMP001",
    "name": "John Doe",
    "email": "john@example.com",
    "department": "Engineering"
  }'
```

### 3. Mark Attendance

```bash
curl -X POST http://localhost:5000/api/v1/attendance/mark \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "EMP001",
    "person_name": "John Doe",
    "source": "main_entrance",
    "marked_by": "manual"
  }'
```

### 4. Get Today's Attendance

```bash
curl -X GET http://localhost:5000/api/v1/attendance/today \
  -H "X-API-Key: your-api-key"
```

### 5. Export Monthly Report (CSV)

```bash
curl -X GET "http://localhost:5000/api/v1/reports/export?start_date=2025-01-01&end_date=2025-01-31&format=csv" \
  -H "X-API-Key: your-api-key" \
  --output attendance_report.csv
```

---

## Notes

1. **Automatic Attendance Marking**: When a person is recognized by the facial recognition system, attendance is automatically marked. This happens independently of API calls.

2. **Duplicate Prevention**: The system automatically prevents duplicate attendance entries within a configurable time window (default: 5 minutes).

3. **Face Registration**: When registering a face through the legacy `/api/register` endpoint, the person is automatically added to the attendance system as well.

4. **Security**: Always use HTTPS in production and rotate API keys regularly.

5. **Rate Limiting**: Consider implementing rate limiting for production deployments.

6. **Backup**: The attendance database (`attendance.db`) should be backed up regularly.

---

## Database Schema

### Tables

1. **persons** - Registered persons
2. **attendance** - Attendance records
3. **detection_events** - All face detection events (audit trail)
4. **system_config** - System configuration
5. **api_keys** - API authentication keys
6. **system_logs** - System activity logs

### Relationships

- `attendance.person_id` → `persons.person_id`
- `detection_events.person_id` → `persons.person_id`
- `detection_events.attendance_id` → `attendance.id`

---

## Support & Integration

For integration with external systems (like Odoo), the placeholder sync endpoints are available. Implementation details will be provided when the integration module is ready.

For any questions or issues, please refer to the system logs or contact the development team.
