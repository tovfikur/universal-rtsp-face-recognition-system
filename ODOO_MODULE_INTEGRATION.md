# Odoo Module Integration Guide

## Overview

Your Face Attendance API Server is now **fully compatible** with the Odoo Face Attendance Integration module. The module can control everything via the API.

---

## ✅ API Compatibility

Your API server now supports **all endpoints** required by the Odoo module:

| Odoo Module Expects | Your API Provides | Status |
|---------------------|-------------------|--------|
| `GET /api/v1/persons` | ✅ Yes | Ready |
| `GET /api/v1/persons/{id}` | ✅ Yes | Ready |
| `POST /api/v1/persons` | ✅ Yes | Ready |
| `PUT /api/v1/persons/{id}` | ✅ Yes | Ready |
| `DELETE /api/v1/persons/{id}` | ✅ Yes | Ready |
| `GET /api/v1/attendance` | ✅ Yes | **NEW** |
| `GET /api/v1/attendance/{id}` | ✅ Yes | Ready |
| `GET /api/v1/reports/daily` | ✅ Yes | Ready (`/reports/daily-summary/{date}`) |
| `GET /api/v1/keys` | ✅ Yes | **NEW** |
| `GET /api/v1/logs` | ✅ Yes | Ready |
| `GET /api/v1/config` | ✅ Yes | Ready |
| `GET /api/v1/health` | ✅ Yes | Ready |
| `GET /api/v1/status` | ✅ Yes | Ready |

---

## 🔐 Authentication

The API supports **both** authentication methods expected by Odoo:

### Method 1: X-API-Key Header
```bash
curl -H "X-API-Key: your_api_key_here" \
  http://192.168.50.152:5000/api/v1/persons
```

### Method 2: Bearer Token (Odoo Default)
```bash
curl -H "Authorization: Bearer your_api_key_here" \
  http://192.168.50.152:5000/api/v1/persons
```

Both methods are automatically supported by the API!

---

## 🚀 Quick Setup in Odoo

### Step 1: Configure API Server in Odoo

1. Open **Odoo** → **Face Attendance** → **Configuration** → **API Servers**
2. Click **Create**
3. Fill in:
   - **Name**: Face Recognition Server 1
   - **Base URL**: `http://192.168.50.152:5000`
   - **API Key**: Your API key (get from `backend/create_api_key.py`)
   - **Priority**: 10
   - **Is Default**: ✓ (checked)
4. Click **Test Connection**
5. Should show: ✅ Connection successful!
6. Click **Save**

### Step 2: Enable Auto-Sync

1. Go to **Face Attendance** → **Configuration** → **Settings**
2. Enable these options:
   - ✓ **Enable Automatic Sync**
   - ✓ **Enable Person Sync**
   - ✓ **Enable Attendance Sync**
3. Set **Sync Interval**: 15 minutes (default)
4. Click **Save**

### Step 3: Manual Sync (First Time)

1. Go to **Face Attendance** → **Configuration** → **API Servers**
2. Open your server
3. Click **Actions** → **Sync All Persons**
4. Wait for completion
5. Go to **Operations** → **Persons** to see synced persons

### Step 4: Verify

1. **Check Persons**: Face Attendance → Operations → Persons
2. **Check Attendance**: Face Attendance → Operations → Attendance Records
3. **Check Health**: API Server should show "Healthy" status

---

## 📋 API Endpoints for Odoo Module

### 1. Person Management

#### List All Persons
```bash
GET /api/v1/persons
```

**Query Parameters:**
- `status`: active/inactive/deleted (default: active)
- `limit`: Max records (default: 100)
- `offset`: Skip records (default: 0)

**Odoo Mapping:**
```json
{
  "success": true,
  "data": {
    "persons": [
      {
        "person_id": "EMP001",        → external_person_id
        "name": "John Doe",           → name
        "email": "john@example.com",  → Mapped to partner
        "department": "Engineering",  → Used for grouping
        "position": "Developer",      → Used for reporting
        "status": "active",           → sync_status
        "created_at": "2025-01-15",   → Timestamp
        "metadata": {...}             → api_metadata (JSON)
      }
    ],
    "total": 50
  }
}
```

#### Get Person Details
```bash
GET /api/v1/persons/{person_id}
```

#### Create Person
```bash
POST /api/v1/persons
Content-Type: application/json

{
  "person_id": "EMP001",
  "name": "John Doe",
  "email": "john@example.com",
  "department": "Engineering",
  "position": "Developer"
}
```

#### Update Person
```bash
PUT /api/v1/persons/{person_id}
Content-Type: application/json

{
  "department": "Sales",
  "position": "Manager"
}
```

#### Delete Person
```bash
DELETE /api/v1/persons/{person_id}
```

---

### 2. Attendance Management

#### List Attendance Records
```bash
GET /api/v1/attendance
```

**Query Parameters:**
- `start_date`: YYYY-MM-DD
- `end_date`: YYYY-MM-DD
- `person_id`: Filter by person
- `limit`: Max records (default: 100)
- `offset`: Skip records (default: 0)

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://192.168.50.152:5000/api/v1/attendance?start_date=2025-01-01&end_date=2025-01-31&limit=1000"
```

**Odoo Mapping:**
```json
{
  "success": true,
  "data": {
    "records": [
      {
        "id": 123,                    → Used for updates
        "person_id": "EMP001",        → Links to person
        "person_name": "John Doe",
        "check_in": "2025-01-15 09:00:00",  → check_in
        "check_out": "2025-01-15 17:30:00", → check_out
        "date": "2025-01-15",         → date
        "duration_minutes": 510,      → duration (calculated)
        "status": "checked_out",      → status
        "source": "face",             → source (face/manual/card)
        "confidence": 95.5,           → confidence score
        "marked_by": "auto"           → marked_by
      }
    ],
    "total": 150
  }
}
```

#### Get Specific Attendance
```bash
GET /api/v1/attendance/{id}
```

#### Mark Attendance
```bash
POST /api/v1/attendance/mark
Content-Type: application/json

{
  "person_id": "EMP001",
  "person_name": "John Doe",
  "marked_by": "manual",
  "notes": "Late arrival"
}
```

#### Mark Checkout
```bash
POST /api/v1/attendance/{id}/checkout
```

---

### 3. Reporting

#### Daily Summary
```bash
GET /api/v1/reports/daily-summary/{date}
```

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://192.168.50.152:5000/api/v1/reports/daily-summary/2025-01-15
```

**Response:**
```json
{
  "success": true,
  "data": {
    "date": "2025-01-15",
    "present_count": 45,
    "total_persons": 50,
    "avg_duration_hours": 8.5,
    "earliest_checkin": "07:30:00",
    "latest_checkout": "19:45:00"
  }
}
```

---

### 4. API Keys

#### List API Keys
```bash
GET /api/v1/keys
```

**Query Parameters:**
- `status`: active/inactive/revoked
- `limit`: Max records (default: 100)

**Response:**
```json
{
  "success": true,
  "data": {
    "keys": [
      {
        "id": 1,
        "name": "Odoo Integration Key",
        "permissions": ["*"],
        "status": "active",
        "created_at": "2025-01-15T10:00:00",
        "last_used": "2025-01-15T14:30:00",
        "expires_at": null
      }
    ],
    "total": 1
  }
}
```

---

### 5. System Monitoring

#### Health Check
```bash
GET /api/v1/health
```

**No authentication required**

**Response:**
```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2025-01-15T14:30:00",
  "version": "1.0.0"
}
```

#### System Status
```bash
GET /api/v1/status
```

**Requires authentication**

**Response:**
```json
{
  "success": true,
  "data": {
    "background_recognition_running": true,
    "snapshot_analysis_running": true,
    "active_video_stream": true,
    "current_source": "camera_0",
    "uptime_seconds": 86400
  }
}
```

#### System Logs
```bash
GET /api/v1/logs
```

**Query Parameters:**
- `level`: info/warning/error
- `category`: sync/api/system/attendance
- `limit`: Max records (default: 100)

---

### 6. Configuration

#### Get Configuration
```bash
GET /api/v1/config
```

**Response:**
```json
{
  "success": true,
  "data": {
    "config": {
      "duplicate_window_minutes": 5,
      "auto_mark_enabled": true,
      "working_hours_start": "09:00",
      "working_hours_end": "18:00"
    }
  }
}
```

#### Update Configuration
```bash
POST /api/v1/config
Content-Type: application/json

{
  "key": "duplicate_window_minutes",
  "value": 10,
  "description": "Prevent duplicates within 10 minutes"
}
```

---

## 🔄 Sync Workflows

### Workflow 1: Odoo Pulls Persons from API

```
Odoo Scheduled Job (every 15 min)
    ↓
GET /api/v1/persons
    ↓
For each person:
  • Check if exists in Odoo (by external_person_id)
  • Create or update attendance.person record
  • Link to hr.employee if match found
  • Update sync_status = 'synced'
    ↓
Log sync results
```

### Workflow 2: Odoo Pulls Attendance from API

```
Odoo Scheduled Job (every 15 min)
    ↓
GET /api/v1/attendance?start_date=X&end_date=Y
    ↓
For each attendance record:
  • Check for duplicates (by external_attendance_id)
  • Skip if already exists
  • Create attendance.record
  • Link to attendance.person
  • Update daily_summary statistics
    ↓
Log sync results
```

### Workflow 3: Face Recognition → Attendance

```
Person approaches camera
    ↓
Face detected and recognized
    ↓
API creates attendance record automatically
    ↓
Odoo sync job pulls new records
    ↓
Attendance appears in Odoo
```

---

## 🎯 Odoo Module Features Using Your API

### 1. Health Monitoring
- **Circuit Breaker**: Tracks API failures
- **Health Status**: GET /api/v1/health every 5 min
- **Metrics**: Success rate, latency, error count

### 2. Failover Support
- If primary server fails, Odoo switches to secondary
- Your API's health endpoint helps determine server status

### 3. Data Synchronization
- **Person Sync**: Pulls from `/api/v1/persons`
- **Attendance Sync**: Pulls from `/api/v1/attendance`
- **Scheduled Jobs**: Every 15 minutes (configurable)

### 4. Reporting
- **Daily Summaries**: From `/api/v1/reports/daily-summary/{date}`
- **Custom Reports**: Using `/api/v1/attendance` with filters
- **Export**: Built-in Odoo export to Excel/CSV

---

## 🔧 Configuration in Odoo

### API Server Settings

| Field | Value | Description |
|-------|-------|-------------|
| **Base URL** | http://192.168.50.152:5000 | Your API server URL |
| **API Key** | sk_xxxx... | From create_api_key.py |
| **Timeout** | 30 seconds | Request timeout |
| **Retry Count** | 3 | Number of retries |
| **Priority** | 10 | Higher = preferred |
| **Is Default** | ✓ | Primary server |

### Global Settings

| Setting | Recommended Value |
|---------|------------------|
| **Auto-Sync** | Enabled |
| **Sync Interval** | 15 minutes |
| **Duplicate Window** | 5 minutes |
| **Batch Size** | 100 records |
| **Log Retention** | 30 days |

---

## 🐛 Troubleshooting

### Issue: "Connection test failed" in Odoo

**Solutions:**
1. Verify API server is running:
   ```bash
   curl http://192.168.50.152:5000/api/v1/health
   ```
2. Check firewall allows port 5000
3. Verify API key is correct
4. Test from Odoo server:
   ```bash
   curl -H "Authorization: Bearer YOUR_KEY" \
     http://192.168.50.152:5000/api/v1/persons
   ```

---

### Issue: "Persons not syncing"

**Solutions:**
1. Check scheduled job is active: Settings → Technical → Scheduled Actions
2. Verify server health in Odoo: API Servers → Check health_status
3. Review logs: Face Attendance → Logs and Monitoring → System Logs
4. Manually trigger sync: API Server → Actions → Sync All Persons

---

### Issue: "Duplicate attendance records"

**Solutions:**
1. Enable duplicate prevention in API settings
2. Increase duplicate window: `/api/v1/config` → `duplicate_window_minutes: 10`
3. Check Odoo duplicate prevention is enabled

---

### Issue: "Circuit breaker open"

**Solution:** In Odoo, go to API Server → Click "Reset Circuit Breaker"

---

## 📊 Monitoring & Metrics

### In Odoo Dashboard

You can monitor:
- ✅ Server health status (healthy/degraded/unhealthy)
- ✅ Success rate (% of successful API calls)
- ✅ Average latency (response time)
- ✅ Total requests, successes, errors
- ✅ Last sync timestamp
- ✅ Circuit breaker state

### In API Logs

```bash
curl -H "Authorization: Bearer YOUR_KEY" \
  "http://192.168.50.152:5000/api/v1/logs?category=api&limit=50"
```

---

## 🎓 Best Practices

### 1. API Key Management
- Create a dedicated API key for Odoo
- Use permissions: `["*"]` or specific: `["person:read", "attendance:read"]`
- Set reasonable expiration (e.g., 365 days)
- Rotate keys periodically

### 2. Sync Frequency
- **High Traffic**: Every 5-10 minutes
- **Normal**: Every 15 minutes (default)
- **Low Traffic**: Every 30-60 minutes

### 3. Error Handling
- Enable circuit breaker in Odoo
- Set retry count to 3
- Monitor error logs daily
- Set up email notifications for critical errors

### 4. Performance
- Use pagination for large datasets (`limit` and `offset`)
- Filter by date range when possible
- Enable batch processing in Odoo settings

---

## ✅ Checklist

Before going live, ensure:

- [ ] API server running on http://192.168.50.152:5000
- [ ] API key created with appropriate permissions
- [ ] Connection test successful in Odoo
- [ ] Person sync tested and working
- [ ] Attendance sync tested and working
- [ ] Health monitoring configured
- [ ] Circuit breaker settings verified
- [ ] Logs retention configured
- [ ] Backup schedule for attendance.db
- [ ] Firewall rules configured
- [ ] Scheduled jobs enabled in Odoo

---

## 🎉 Summary

Your Face Attendance API is now **fully compatible** with the Odoo Face Attendance Integration module!

**What Odoo Can Do:**
✅ Pull persons from your API
✅ Pull attendance records automatically
✅ Monitor server health
✅ Handle failover scenarios
✅ Generate reports from API data
✅ Manage API keys
✅ View system logs
✅ Configure system settings

**Everything is controlled via API** - exactly as requested!

---

For more details, see:
- **PROJECT_OVERVIEW.md** (Odoo module documentation)
- **API_DOCUMENTATION.md** (Complete API reference)
- **ODOO_INTEGRATION.md** (Odoo XML-RPC guide)
