# Odoo Integration Guide

## Overview

The Face Attendance System now includes **full Odoo ERP integration** via XML-RPC. This allows you to:

- **Pull employees** from Odoo and register them in the face attendance system
- **Push attendance records** from the face system to Odoo
- **Bi-directional sync** for complete integration

---

## Quick Start

### Step 1: Install Dependencies

The Odoo integration uses Python's built-in `xmlrpc.client`, but you need to ensure you have the latest dependencies:

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Configure Odoo Connection

**Option A: Interactive Configuration (Recommended)**

```bash
cd backend
python configure_odoo.py
```

Follow the prompts to enter:
- **Odoo URL**: e.g., `http://localhost:8069`
- **Database name**: Your Odoo database name
- **Username**: Your Odoo username (usually `admin`)
- **Password**: Your Odoo password or API key

The script will test the connection and save the configuration.

**Option B: Via API**

```bash
curl -X POST http://192.168.50.152:5000/api/v1/sync/odoo/config \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://localhost:8069",
    "db": "your_database_name",
    "username": "admin",
    "password": "your_password"
  }'
```

### Step 3: Test Connection

```bash
# Using the script
python configure_odoo.py --test

# OR via API
curl -X POST http://192.168.50.152:5000/api/v1/sync/odoo/test \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://localhost:8069",
    "db": "your_database_name",
    "username": "admin",
    "password": "your_password"
  }'
```

### Step 4: Sync Employees from Odoo

```bash
curl -X POST http://192.168.50.152:5000/api/v1/sync/odoo/pull \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json"
```

This will:
- Fetch all active employees from Odoo
- Create/update persons in the face attendance system
- Link them using employee barcode or Odoo ID

### Step 5: Register Faces

Now register faces for the synced employees using the web interface:

1. Go to http://192.168.50.152:5000/faces.html
2. Register faces for each employee
3. The system will automatically link them using the person_id

### Step 6: Push Attendance to Odoo

After attendance is automatically marked by face recognition, push it to Odoo:

```bash
curl -X POST http://192.168.50.152:5000/api/v1/sync/odoo/push \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-01",
    "end_date": "2025-01-31"
  }'
```

---

## API Endpoints

### 1. Test Connection

**POST** `/api/v1/sync/odoo/test`

Test Odoo connection with provided credentials.

**Request:**
```json
{
  "url": "http://localhost:8069",
  "db": "database_name",
  "username": "admin",
  "password": "password"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Connection test successful",
  "server_version": "17.0",
  "protocol_version": 1
}
```

---

### 2. Save Configuration

**POST** `/api/v1/sync/odoo/config`

Save Odoo connection configuration for future use.

**Request:**
```json
{
  "url": "http://localhost:8069",
  "db": "database_name",
  "username": "admin",
  "password": "password"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Odoo configuration saved successfully"
}
```

---

### 3. Get Configuration

**GET** `/api/v1/sync/odoo/config`

Get current Odoo configuration (password is masked).

**Response:**
```json
{
  "success": true,
  "configured": true,
  "config": {
    "url": "http://localhost:8069",
    "db": "database_name",
    "username": "admin",
    "password": "***********"
  }
}
```

---

### 4. Pull Employees from Odoo

**POST** `/api/v1/sync/odoo/pull`

Pull employee data from Odoo and sync to local database.

**Request (if config saved):**
```json
{}
```

**Request (with credentials):**
```json
{
  "url": "http://localhost:8069",
  "db": "database_name",
  "username": "admin",
  "password": "password",
  "limit": 1000
}
```

**Response:**
```json
{
  "success": true,
  "message": "Synced 25 employees from Odoo",
  "added": 20,
  "updated": 5,
  "total": 25,
  "errors": null
}
```

**What it does:**
- Fetches active employees from Odoo `hr.employee` model
- Extracts: name, email, phone, department, position, barcode
- Creates new persons in face system or updates existing ones
- Uses employee barcode as person_id (or generates `ODOO_{id}`)

---

### 5. Push Attendance to Odoo

**POST** `/api/v1/sync/odoo/push`

Push attendance records to Odoo for a date range.

**Request:**
```json
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-31"
}
```

**Request (with credentials):**
```json
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "url": "http://localhost:8069",
  "db": "database_name",
  "username": "admin",
  "password": "password"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Pushed 150 attendance records, 2 failed",
  "pushed": 150,
  "failed": 2,
  "total": 152,
  "errors": [
    "Employee not found: EMP999"
  ]
}
```

**What it does:**
- Fetches attendance records from face system for date range
- Matches person_id to Odoo employee (by barcode or ID)
- Creates `hr.attendance` records in Odoo with check_in/check_out times
- Handles errors gracefully and reports failed pushes

---

### 6. Get Sync Status

**GET** `/api/v1/sync/status`

Get synchronization status with Odoo.

**Response:**
```json
{
  "success": true,
  "data": {
    "odoo": {
      "enabled": true,
      "configured": true,
      "url": "http://localhost:8069",
      "db": "database_name",
      "last_sync": "2025-01-15T14:30:00",
      "last_sync_message": "Synced employees from Odoo: 20 added, 5 updated",
      "status": "configured"
    }
  }
}
```

---

## Workflow Examples

### Scenario 1: Initial Setup - Pull Employees from Odoo

```bash
# 1. Configure Odoo
curl -X POST http://192.168.50.152:5000/api/v1/sync/odoo/config \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://localhost:8069",
    "db": "mycompany",
    "username": "admin",
    "password": "admin123"
  }'

# 2. Pull employees
curl -X POST http://192.168.50.152:5000/api/v1/sync/odoo/pull \
  -H "X-API-Key: YOUR_API_KEY"

# 3. Check status
curl -H "X-API-Key: YOUR_API_KEY" \
  http://192.168.50.152:5000/api/v1/sync/status

# 4. List synced persons
curl -H "X-API-Key: YOUR_API_KEY" \
  http://192.168.50.152:5000/api/v1/persons
```

---

### Scenario 2: Daily Attendance Push to Odoo

```bash
# 1. Get today's attendance
curl -H "X-API-Key: YOUR_API_KEY" \
  http://192.168.50.152:5000/api/v1/attendance/today

# 2. Push to Odoo
curl -X POST http://192.168.50.152:5000/api/v1/sync/odoo/push \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-15",
    "end_date": "2025-01-15"
  }'
```

---

### Scenario 3: Monthly Sync

```bash
# Pull latest employees at start of month
curl -X POST http://192.168.50.152:5000/api/v1/sync/odoo/pull \
  -H "X-API-Key: YOUR_API_KEY"

# Push entire month's attendance at end of month
curl -X POST http://192.168.50.152:5000/api/v1/sync/odoo/push \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-01",
    "end_date": "2025-01-31"
  }'
```

---

## Data Mapping

### Employee Pull (Odoo → Face System)

| Odoo Field | Face System Field | Notes |
|------------|-------------------|-------|
| `id` | `person_id` | Used if no barcode (as `ODOO_{id}`) |
| `barcode` | `person_id` | Primary identifier (recommended) |
| `name` | `name` | Full name |
| `work_email` | `email` | Work email |
| `mobile_phone` | `phone` | Mobile phone |
| `department_id` | `department` | Department name |
| `job_id` | `position` | Job title |
| `employee_type` | `metadata` | Stored in metadata |

### Attendance Push (Face System → Odoo)

| Face System Field | Odoo Field | Notes |
|-------------------|------------|-------|
| `person_id` | `employee_id` | Matched by barcode or ID |
| `check_in` | `check_in` | ISO format converted to Odoo format |
| `check_out` | `check_out` | Optional, if marked |
| `duration_minutes` | `worked_hours` | Calculated by Odoo |

---

## Odoo Setup Requirements

### 1. Install HR Module

In Odoo, make sure the **HR** (Human Resources) module is installed:

1. Go to **Apps**
2. Search for "Employees"
3. Install **Employees** module

### 2. Install Attendance Module

1. Go to **Apps**
2. Search for "Attendances"
3. Install **Attendances** module

### 3. Set Employee Barcodes

For best results, set unique barcodes for each employee:

1. Go to **Employees**
2. Open each employee
3. Set **Badge ID** (this becomes the barcode)
4. Use format like: `EMP001`, `EMP002`, etc.

### 4. Grant API Access

The user account used for API access needs these permissions:

- **HR Officer** or **HR Manager** role
- Read access to: `hr.employee`, `hr.department`, `hr.job`
- Write access to: `hr.attendance`

### 5. Enable XML-RPC

Odoo has XML-RPC enabled by default. If you've disabled it, re-enable it in the config file:

```ini
[options]
xmlrpc = True
xmlrpc_interface = 0.0.0.0
xmlrpc_port = 8069
```

---

## Troubleshooting

### Connection Failed

**Error**: "Authentication failed. Check credentials."

**Solutions**:
1. Verify Odoo URL is correct (include `http://` or `https://`)
2. Check database name (case-sensitive)
3. Verify username and password
4. Try logging into Odoo web interface with same credentials
5. Check if Odoo server is running: `curl http://localhost:8069`

---

### Cannot Access Employees

**Error**: "Failed to pull employees: Access Denied"

**Solutions**:
1. Grant user **HR Officer** or **HR Manager** role
2. Check user has read access to `hr.employee` model
3. Try with **admin** user first to verify connection works

---

### Employee Not Found When Pushing

**Error**: "Employee not found: EMP001"

**Solutions**:
1. Verify employee exists in Odoo
2. Check employee barcode matches person_id
3. Pull employees again to sync latest data
4. Manually set correct person_id in face system

---

### SSL Certificate Errors

**Error**: "SSL: CERTIFICATE_VERIFY_FAILED"

**Solution**: For development/local Odoo, this is handled automatically. For production with self-signed certificates, you may need to configure proper SSL certificates.

---

## Automated Sync (Optional)

### Create a Sync Script

```python
# sync_odoo_daily.py
import requests
import sys
from datetime import datetime

API_KEY = "your_api_key_here"
BASE_URL = "http://192.168.50.152:5000/api/v1"

def sync_attendance():
    today = datetime.now().strftime("%Y-%m-%d")

    response = requests.post(
        f"{BASE_URL}/sync/odoo/push",
        headers={"X-API-Key": API_KEY},
        json={
            "start_date": today,
            "end_date": today
        }
    )

    result = response.json()

    if result.get('success'):
        print(f"✓ Pushed {result.get('pushed', 0)} attendance records to Odoo")
        return 0
    else:
        print(f"✗ Sync failed: {result.get('error')}")
        return 1

if __name__ == "__main__":
    sys.exit(sync_attendance())
```

### Schedule with Cron (Linux)

```bash
# Edit crontab
crontab -e

# Add this line to run daily at 11 PM
0 23 * * * cd /path/to/project && python sync_odoo_daily.py >> /var/log/odoo_sync.log 2>&1
```

### Schedule with Task Scheduler (Windows)

1. Open **Task Scheduler**
2. Create new task
3. Set trigger: Daily at 11:00 PM
4. Set action: Run `python sync_odoo_daily.py`
5. Save

---

## Security Considerations

### 1. Secure API Keys

- Never commit API keys to version control
- Use environment variables or secure vaults
- Rotate keys regularly

### 2. Secure Odoo Credentials

- Use dedicated API user in Odoo (not admin)
- Grant minimum required permissions
- Consider using Odoo API keys instead of passwords

### 3. Use HTTPS

In production:
- Use HTTPS for Odoo
- Use HTTPS for Face Attendance API
- Never transmit credentials over HTTP

### 4. Network Security

- Restrict Odoo API access by IP if possible
- Use VPN for remote access
- Implement rate limiting

---

## Performance Tips

### 1. Batch Sync

Instead of syncing after each attendance, batch sync once per day:

```bash
# Daily at end of business day
curl -X POST http://192.168.50.152:5000/api/v1/sync/odoo/push \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-15",
    "end_date": "2025-01-15"
  }'
```

### 2. Incremental Employee Sync

Only pull employees when there are changes, not on every sync.

### 3. Monitor Sync Logs

Check system logs for sync errors:

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "http://192.168.50.152:5000/api/v1/logs?category=odoo_sync&limit=20"
```

---

## Support

For Odoo-specific issues:
- Check Odoo logs: `/var/log/odoo/odoo.log`
- Odoo documentation: https://www.odoo.com/documentation
- Odoo forums: https://www.odoo.com/forum

For integration issues:
- Check system logs: `GET /api/v1/logs?category=odoo_sync`
- Verify configuration: `GET /api/v1/sync/odoo/config`
- Test connection: `POST /api/v1/sync/odoo/test`

---

## What's Next

Your Odoo integration is now fully functional! You can:

1. **Pull employees** from Odoo
2. **Register their faces** via web interface
3. **Automatically mark attendance** via face recognition
4. **Push attendance** back to Odoo
5. **View reports** in both systems

The integration is designed to be flexible - use it manually or automate it completely based on your needs.
