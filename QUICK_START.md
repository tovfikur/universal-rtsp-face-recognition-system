# Quick Start Guide - Attendance Management System

## 🚀 Get Started in 5 Minutes

### Step 1: Verify Everything Is Ready (30 seconds)

```bash
cd backend
python verify_setup.py
```

**Expected output:** All checks should pass ✓

If any checks fail, install dependencies:
```bash
pip install -r requirements.txt
```

---

### Step 2: Start the Server (10 seconds)

```bash
cd backend
hypercorn app:app --bind 0.0.0.0:5000
```

**Expected output:**
```
[AttendanceSystem] Database initialized at: data/attendance.db
[AttendanceSystem] API routes registered at /api/v1
Running on http://0.0.0.0:5000
```

Keep this terminal open!

---

### Step 3: Generate Your Admin API Key (1 minute)

Open a **new terminal** and run:

```bash
cd backend
python create_api_key.py
```

**Follow the prompts:**
- Press Enter to accept defaults (Admin Master Key with all permissions)
- **Copy the API key shown** - you'll need it for all API requests!

**Example output:**
```
✓ API KEY CREATED SUCCESSFULLY
API Key: sk_1234567890abcdefghijklmnopqrstuvwxyz
⚠️  IMPORTANT: Save this key securely!
```

---

### Step 4: Test the System (1 minute)

Replace `<YOUR_API_KEY>` with the key from Step 3:

```bash
python test_api.py <YOUR_API_KEY>
```

**Expected output:**
```
✓ PASS  Health Check
✓ PASS  System Status
✓ PASS  Person Management
...
Result: 7/7 tests passed
```

---

### Step 5: Use the System

#### Option A: Web Interface (Easiest)

1. **Open browser** to http://localhost:5000/faces.html
2. **Click "Start Camera"**
3. **Click "Add Person"** and fill in:
   - Person ID: `EMP001`
   - Name: `Your Name`
4. **Click "Save Person"**

The system will now automatically mark your attendance when it recognizes you!

#### Option B: API (Most Powerful)

**Register a person:**
```bash
curl -X POST http://localhost:5000/api/v1/persons \
  -H "X-API-Key: <YOUR_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "EMP001",
    "name": "John Doe",
    "email": "john@company.com",
    "department": "Engineering"
  }'
```

**Get today's attendance:**
```bash
curl -H "X-API-Key: <YOUR_API_KEY>" \
  http://localhost:5000/api/v1/attendance/today
```

**Check system status:**
```bash
curl -H "X-API-Key: <YOUR_API_KEY>" \
  http://localhost:5000/api/v1/status
```

---

## 📊 Key URLs

| Purpose | URL |
|---------|-----|
| Main Dashboard | http://localhost:5000 |
| Face Registration | http://localhost:5000/faces.html |
| Health Check (no auth) | http://localhost:5000/api/v1/health |
| System Status | http://localhost:5000/api/v1/status |
| Today's Attendance | http://localhost:5000/api/v1/attendance/today |

---

## 🔑 Common API Operations

### Mark Attendance Manually
```bash
curl -X POST http://localhost:5000/api/v1/attendance/mark \
  -H "X-API-Key: <YOUR_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "EMP001",
    "person_name": "John Doe",
    "marked_by": "manual"
  }'
```

### Get Attendance Report (Last 7 Days)
```bash
curl -H "X-API-Key: <YOUR_API_KEY>" \
  "http://localhost:5000/api/v1/reports/attendance?start_date=2025-01-05&end_date=2025-01-12"
```

### Export to CSV
```bash
curl -H "X-API-Key: <YOUR_API_KEY>" \
  "http://localhost:5000/api/v1/reports/export?start_date=2025-01-01&end_date=2025-01-31&format=csv" \
  --output january_attendance.csv
```

### List All Persons
```bash
curl -H "X-API-Key: <YOUR_API_KEY>" \
  http://localhost:5000/api/v1/persons
```

---

## ⚙️ Quick Configuration

### Change Duplicate Prevention Window
```bash
curl -X POST http://localhost:5000/api/v1/config \
  -H "X-API-Key: <YOUR_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"key": "duplicate_window_minutes", "value": 10}'
```

### Disable Auto-Attendance (for testing)
```bash
curl -X POST http://localhost:5000/api/v1/config \
  -H "X-API-Key: <YOUR_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"key": "auto_mark_enabled", "value": false}'
```

### View Current Configuration
```bash
curl -H "X-API-Key: <YOUR_API_KEY>" \
  http://localhost:5000/api/v1/config
```

---

## 🐛 Troubleshooting

### Problem: "Module not found" errors

**Solution:**
```bash
cd backend
pip install -r requirements.txt
```

### Problem: "API key required" error

**Solution:** Make sure you're passing the API key header:
```bash
-H "X-API-Key: <YOUR_API_KEY>"
```

### Problem: Attendance not being marked automatically

**Solutions:**
1. Check if auto-marking is enabled:
   ```bash
   curl -H "X-API-Key: <YOUR_API_KEY>" \
     "http://localhost:5000/api/v1/config?key=auto_mark_enabled"
   ```

2. Check system logs:
   ```bash
   curl -H "X-API-Key: <YOUR_API_KEY>" \
     "http://localhost:5000/api/v1/logs?limit=20"
   ```

3. Verify person has a face registered:
   ```bash
   curl -H "X-API-Key: <YOUR_API_KEY>" \
     http://localhost:5000/api/v1/persons
   ```

### Problem: Server won't start

**Solution:** Check if port 5000 is already in use:
```bash
# Windows
netstat -ano | findstr :5000

# Linux/Mac
lsof -i :5000
```

If another process is using port 5000, either stop that process or change the port:
```bash
hypercorn app:app --bind 0.0.0.0:8000
```

---

## 📚 Next Steps

### For Administrators
1. **Create restricted API keys** for different users/applications
2. **Set up regular backups** of `backend/data/attendance.db`
3. **Configure working hours** via API
4. **Set up HTTPS** for production (use nginx reverse proxy)

### For Developers
1. **Read API_DOCUMENTATION.md** for complete endpoint reference
2. **Build custom dashboard** using the REST API
3. **Integrate with external systems** (HR, payroll, etc.)
4. **Customize attendance rules** via configuration API

### For Users
1. **Register your face** via web interface
2. **View your attendance** via API or custom app
3. **Report issues** by checking system logs

---

## 📖 Full Documentation

- **Setup Guide**: [SETUP_GUIDE.md](SETUP_GUIDE.md) - Comprehensive setup and operational guide
- **API Reference**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Complete API documentation
- **Implementation Summary**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - What was built and how

---

## 🎯 System at a Glance

### What It Does
✅ Detects persons using YOLOv8
✅ Recognizes faces using dlib
✅ Automatically marks attendance
✅ Prevents duplicate entries
✅ Generates reports (daily, weekly, monthly)
✅ Exports data (CSV, JSON)
✅ Provides secure API access
✅ Logs all activities

### What You Can Do
✅ Register persons with photos
✅ Track attendance automatically
✅ Mark attendance manually (via API)
✅ Generate attendance reports
✅ Export data for payroll/HR
✅ Monitor system health
✅ Configure system behavior
✅ Integrate with other systems

### Database Tables
- **persons** - Who is registered
- **attendance** - Who came when
- **detection_events** - Every face detected (audit)
- **system_config** - System settings
- **api_keys** - Access tokens
- **system_logs** - What happened

---

## 🔐 Security Reminder

**In Production:**
1. ✅ Use HTTPS (not HTTP)
2. ✅ Rotate API keys regularly
3. ✅ Use separate keys for different apps
4. ✅ Monitor API logs for suspicious activity
5. ✅ Backup database regularly
6. ✅ Keep server updated

---

## 💡 Pro Tips

1. **Test with low confidence first**: Start with `FACE_TOLERANCE=0.6` for easier testing
2. **Use person_id wisely**: Use employee IDs for easy integration with HR systems
3. **Check logs regularly**: `GET /api/v1/logs` shows what's happening
4. **Archive old data**: Move old attendance records to separate database monthly
5. **Create read-only keys**: For mobile apps or reporting tools

---

## 🎉 You're Ready!

Your attendance management system is now fully operational. The system will:
- ✅ Automatically mark attendance when registered faces are recognized
- ✅ Prevent duplicate entries within 5 minutes (configurable)
- ✅ Log all detection events for audit
- ✅ Provide complete API access for integration

**Need help?** Check the documentation or review system logs!

**Happy tracking! 🚀**
