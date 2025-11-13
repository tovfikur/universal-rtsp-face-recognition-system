# Odoo Integration - Quick Start

## ⚡ 5-Minute Setup

### Step 1: Configure Odoo Connection (1 minute)

```bash
cd backend
python configure_odoo.py
```

**Enter when prompted:**
- Odoo URL: `http://localhost:8069`
- Database: Your Odoo database name
- Username: `admin` (or your username)
- Password: Your password

✓ Script will test connection automatically

---

### Step 2: Pull Employees from Odoo (30 seconds)

```bash
curl -X POST http://192.168.50.152:5000/api/v1/sync/odoo/pull \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json"
```

**Result:** All Odoo employees are now in your face system!

---

### Step 3: Register Faces (2 minutes per person)

1. Go to: http://192.168.50.152:5000/faces.html
2. Click "Start Camera"
3. Click "Add Person"
4. Enter the **same Person ID** from Odoo (check with step 2)
5. Click "Save Person"

---

### Step 4: Push Attendance to Odoo (30 seconds)

After face recognition marks attendance, push to Odoo:

```bash
curl -X POST http://192.168.50.152:5000/api/v1/sync/odoo/push \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-15",
    "end_date": "2025-01-15"
  }'
```

---

## 🎯 Complete Workflow

```
1. Odoo (Employees)
   ↓ [Pull]
2. Face System (Persons)
   ↓ [Register Faces via Web UI]
3. Face Recognition (Auto-mark Attendance)
   ↓ [Push]
4. Odoo (Attendance Records)
```

---

## 📋 Useful Commands

### Check Sync Status
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  http://192.168.50.152:5000/api/v1/sync/status
```

### Test Connection
```bash
python backend/configure_odoo.py --test
```

### View Synced Persons
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  http://192.168.50.152:5000/api/v1/persons
```

### Today's Attendance
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  http://192.168.50.152:5000/api/v1/attendance/today
```

### Check Sync Logs
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "http://192.168.50.152:5000/api/v1/logs?category=odoo_sync"
```

---

## 🔧 Troubleshooting

**Problem:** "Odoo not configured"
```bash
# Solution: Run configuration
cd backend
python configure_odoo.py
```

**Problem:** "Employee not found when pushing"
```bash
# Solution: Pull employees first
curl -X POST http://192.168.50.152:5000/api/v1/sync/odoo/pull \
  -H "X-API-Key: YOUR_API_KEY"
```

**Problem:** "Connection failed"
```bash
# Solution: Check Odoo is running
curl http://localhost:8069
# Should return HTML page
```

---

## 📖 Full Documentation

For complete details, see:
- **ODOO_INTEGRATION.md** - Full integration guide
- **API_DOCUMENTATION.md** - All API endpoints
- **SETUP_GUIDE.md** - General setup guide

---

## ✅ You're Done!

Your face attendance system is now fully integrated with Odoo! 🎉

- Employees sync automatically
- Faces are registered via web interface
- Attendance is marked by face recognition
- Data syncs back to Odoo

For automated daily sync, see the automation section in ODOO_INTEGRATION.md
