# Complete System Workflow - Face Attendance with Odoo Integration

## 🎯 System Overview

This system provides a complete face attendance solution with seamless Odoo ERP integration. It consists of:

1. **Backend API Server** - Face recognition, attendance tracking, person management
2. **Web Console** - Live monitoring, person management, face registration
3. **Odoo Module** - ERP integration for HR and attendance management

---

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         ODOO ERP                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Face Attendance Integration Module                       │  │
│  │  - Person Sync                                            │  │
│  │  - Face Image Upload                                      │  │
│  │  - Attendance Sync                                        │  │
│  └────────────────────────┬──────────────────────────────────┘  │
└─────────────────────────┬─┴──────────────────────────────────────┘
                          │
                    REST API over HTTP
                          │
┌─────────────────────────▼──────────────────────────────────────┐
│              Face Attendance API Server                         │
│                  (http://192.168.50.152:5000)                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  API Routes (api_routes.py)                              │  │
│  │  - Person Management                                     │  │
│  │  - Face Registration                                     │  │
│  │  - Attendance Management                                 │  │
│  │  - Reports & Analytics                                   │  │
│  └───────────────────┬──────────────────────────────────────┘  │
│                      │                                          │
│  ┌──────────────────▼────────────┬───────────────────────────┐ │
│  │  Attendance System             │  Face Recognition System  │ │
│  │  (attendance.db - SQLite)      │  (faces.pkl - Pickle)     │ │
│  │  - Person metadata             │  - Face encodings         │ │
│  │  - Attendance records          │  - Face images            │ │
│  └────────────────────────────────┴───────────────────────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Face Recognition Engine (app.py)                        │  │
│  │  - YOLOv8 Person Detection                               │  │
│  │  - dlib Face Recognition                                 │  │
│  │  - Real-time Video Processing                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬───────────────────────────────────┘
                             │
                    WebSocket/HTTP Stream
                             │
┌────────────────────────────▼───────────────────────────────────┐
│              Web Console (Frontend)                             │
│              http://127.0.0.1:5000                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Smart Recognition Console (index.html)                  │  │
│  │  - Live Video Feed                                       │  │
│  │  - Snapshot Analysis Tab                                 │  │
│  │  - Persons Management Tab ← NEW!                         │  │
│  │  - Face Registration Modal                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Registered Faces (faces.html)                           │  │
│  │  - View all registered faces                             │  │
│  │  - Search and filter                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

                             ▲
                             │
                    Camera / RTSP Stream
                             │
                      ┌──────┴──────┐
                      │   Camera    │
                      │   Device    │
                      └─────────────┘
```

---

## 🔄 Complete Workflows

### Workflow 1: Person Creation and Face Registration (from Odoo)

**Step 1: HR Creates Employee in Odoo**
```
HR User in Odoo
    ↓
Creates new employee
    ↓
Employee record saved in Odoo database
```

**Step 2: Odoo Syncs Person to Face API**
```
Odoo Scheduled Job (or manual sync)
    ↓
POST /api/v1/persons
{
  "person_id": "EMP001",
  "name": "John Doe",
  "email": "john@example.com",
  "department": "Engineering"
}
    ↓
Person created in attendance.db
    ↓
Status: Person exists but NO face registered yet
```

**Step 3: Person Appears in Web Console**
```
Web Console → Persons Tab
    ↓
Shows: John Doe [EMP001]
Status: ⏳ Pending (No face registered)
Button: [Register] ← Clickable
```

**Step 4: HR Uploads Face Photo in Odoo**
```
HR User in Odoo
    ↓
Opens employee form
    ↓
Uploads face photo (Binary field)
    ↓
Clicks "Register Face" button
    ↓
Odoo converts image to base64
```

**Step 5: Odoo Sends Face Image to API**
```
Odoo Python Code:
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    ↓
POST /api/v1/persons/EMP001/register-face
{
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
    ↓
API receives base64 image
```

**Step 6: API Processes Face Image**
```
API Backend (api_routes.py):
    1. Decode base64 → numpy array
    2. Detect face using face_recognition
    3. Create 128-D face encoding
    4. Save face image to disk
    5. Add encoding to faces.pkl
    6. Update person in attendance.db
    7. Update live recognizer in memory
    ↓
Response: Success! Face registered for John Doe
```

**Step 7: Face Registration Confirmed**
```
Web Console → Persons Tab
    ↓
Shows: John Doe [EMP001]
Status: ✓ Face Registered (Green badge)
Button: [Register] ← Hidden
```

**Step 8: Face Ready for Recognition**
```
Camera detects person
    ↓
YOLOv8 detects person bounding box
    ↓
face_recognition identifies face
    ↓
Matches John Doe (confidence: 95%)
    ↓
Attendance marked automatically
```

---

### Workflow 2: Manual Face Registration (from Web Console)

**Option A: Register from Persons Tab**

**Step 1: User Browses Persons**
```
Open Web Console → http://127.0.0.1:5000
    ↓
Click "Persons" tab (right column)
    ↓
See list of synced persons
```

**Step 2: Find Person Without Face**
```
Search or scroll to find person
    ↓
See: Jane Smith [EMP002]
Status: ⏳ Pending
Button: [Register]
```

**Step 3: Click Register Button**
```
Click [Register] button
    ↓
JavaScript saves person info to sessionStorage
    ↓
Redirects to index.html with ?register=true
    ↓
Page loads and auto-opens registration modal
    ↓
Form pre-filled:
  - Person ID: EMP002 (read-only)
  - Name: Jane Smith (read-only)
```

**Step 4: Capture Face**
```
Ensure person is in camera view
    ↓
Face visible in video feed
    ↓
Click "Save Person" button
```

**Step 5: Backend Processing**
```
Frontend captures frame from video
    ↓
POST /api/register-face
    ↓
Backend detects face
    ↓
Creates encoding
    ↓
Saves to database
    ↓
Updates recognizer
```

**Step 6: Confirmation**
```
Success message displayed
    ↓
Modal closes
    ↓
Switch to Persons tab
    ↓
Status updated: ✓ Face Registered
```

---

**Option B: Register from Live Monitor**

**Step 1: Direct Registration**
```
Open Web Console → http://127.0.0.1:5000
    ↓
Start camera
    ↓
Click "Add Person" button
```

**Step 2: Fill Form**
```
Registration modal opens
    ↓
Enter:
  - Person ID: EMP003
  - Name: Alice Johnson
    ↓
Ensure face visible in camera
    ↓
Click "Save Person"
```

**Step 3: Dual Creation**
```
Backend:
  1. Creates person in attendance.db
  2. Registers face in faces.pkl
  3. Updates recognizer
    ↓
Person created AND face registered in one step!
```

---

### Workflow 3: Attendance Recognition and Sync

**Step 1: Person Arrives at Office**
```
Person approaches camera
    ↓
Face visible in camera view
```

**Step 2: Real-time Detection**
```
Camera captures frames (30 FPS)
    ↓
YOLOv8 detects person bounding box
    ↓
Extracts face region
    ↓
face_recognition creates encoding
    ↓
Compares with known faces
    ↓
Match found: John Doe (confidence: 97%)
```

**Step 3: Attendance Marked**
```
Check for duplicate (within 5 minutes)
    ↓
No duplicate found
    ↓
Create attendance record in attendance.db:
  - person_id: EMP001
  - person_name: John Doe
  - check_in: 2025-01-15 08:30:00
  - status: checked_in
  - source: face
  - confidence: 97.2
```

**Step 4: Visible in Web Console**
```
Timeline page shows:
  ✓ John Doe checked in at 08:30 AM
```

**Step 5: Odoo Pulls Attendance**
```
Odoo Scheduled Job (every 15 minutes)
    ↓
GET /api/v1/attendance?start_date=2025-01-15&end_date=2025-01-15
    ↓
Receives attendance records
    ↓
Creates attendance.record in Odoo
    ↓
Links to attendance.person
    ↓
Updates daily summary
```

**Step 6: Visible in Odoo**
```
Odoo User opens:
  Face Attendance → Operations → Attendance Records
    ↓
Sees: John Doe | 2025-01-15 08:30:00 | Checked In
```

**Step 7: Check-out Process**
```
Person leaves (evening)
    ↓
Camera detects face again
    ↓
System checks: Already checked in today
    ↓
Marks checkout automatically
    ↓
Updates record:
  - check_out: 2025-01-15 17:45:00
  - duration: 9.25 hours
  - status: checked_out
    ↓
Odoo pulls updated record
    ↓
Shows complete attendance with duration
```

---

## 🎨 Web Console User Guide

### Main Console (index.html)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ [Logo] Smart Recognition Console          [Status] [⚙️]    │
├─────────────────────────────────────────────────────────────┤
│  [Live Monitor] [Registered Faces] [Timeline]               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────┐  ┌───────────────────────┐   │
│  │                          │  │ [Snapshot] [Persons]  │   │
│  │   Live Video Feed        │  ├───────────────────────┤   │
│  │                          │  │                       │   │
│  │   [Person Detected]      │  │  📊 Statistics        │   │
│  │   [Face Recognized]      │  │  Total: 50            │   │
│  │                          │  │  With Faces: 45       │   │
│  │                          │  │                       │   │
│  │                          │  │  🔍 Search box        │   │
│  │                          │  │                       │   │
│  └──────────────────────────┘  │  👤 John Doe          │   │
│                                │  [EMP001] ✓ Registered│   │
│  [Start] [Stop] [Add Person]   │                       │   │
│  [RTSP] [Clear Data]           │  👤 Jane Smith        │   │
│                                │  [EMP002] ⏳ Pending  │   │
│  Detected: 45 | FPS: 28        │  [Register] button    │   │
│                                │                       │   │
│                                │  [Refresh]            │   │
│                                └───────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Persons Tab Features:**

1. **Statistics Cards**
   - Total Persons: All persons synced from Odoo
   - With Faces: Persons who have registered faces

2. **Search Box**
   - Search by name, person ID, department, or email
   - Real-time filtering

3. **Person Cards**
   - Name and ID badge
   - Email, department, position (if available)
   - Face status badge:
     - ✓ Face Registered (green)
     - ⏳ Pending (orange)
   - Register button (only for pending)

4. **Actions**
   - Click [Register] → Opens registration modal with pre-filled data
   - Click [Refresh] → Reloads persons list
   - Auto-refresh every 30 seconds when tab is active

---

### Registered Faces Page (faces.html)

**Purpose:** View all registered faces in a gallery

**Features:**
- Grid layout with face photos
- Person name and ID
- Registration timestamp
- Search/filter functionality
- Clear all faces button (admin)

---

### Timeline Page (timeline.html)

**Purpose:** View attendance history

**Features:**
- Chronological attendance events
- Check-in/check-out times
- Person details
- Date filtering
- Export functionality

---

## 🔧 Configuration & Setup

### 1. API Server Configuration

**Create API Key:**
```bash
cd backend
python create_api_key.py
```

**Output:**
```
API Key created successfully!
Key: sk_live_abc123...
Name: Odoo Integration
Permissions: ["*"]
```

**Copy this key to Odoo configuration**

---

### 2. Odoo Module Configuration

**Step 1: Install Module**
```
Odoo → Apps → Update Apps List
Search: Face Attendance Integration
Click: Install
```

**Step 2: Configure API Server**
```
Face Attendance → Configuration → API Servers → Create

Fields:
  - Name: Main Face Recognition Server
  - Base URL: http://192.168.50.152:5000
  - API Key: sk_live_abc123... (from above)
  - Priority: 10
  - Is Default: ✓
  - Timeout: 30 seconds

Click: Test Connection
Should show: ✅ Connection successful!

Click: Save
```

**Step 3: Enable Auto-Sync**
```
Face Attendance → Configuration → Settings

Enable:
  ✓ Enable Automatic Sync
  ✓ Enable Person Sync
  ✓ Enable Attendance Sync

Sync Interval: 15 minutes

Click: Save
```

**Step 4: Manual Initial Sync**
```
Face Attendance → Configuration → API Servers
Open: Main Face Recognition Server
Click: Actions → Sync All Persons

Wait for completion...
```

**Step 5: Verify**
```
Face Attendance → Operations → Persons
Should see: List of persons synced from Face API

Face Attendance → Operations → Attendance Records
Should see: Attendance records pulled from Face API
```

---

### 3. Camera Configuration

**Configure Camera Source:**
```
Web Console → Settings icon (⚙️)
Enter source:
  - Webcam: 0, 1, 2
  - RTSP: rtsp://admin:pass@192.168.1.100:554/stream
  - HTTP: http://192.168.1.100:8080/video

Click: Apply & Connect
```

---

## 📝 API Integration Examples

### Example 1: Create Person and Register Face (Python)

```python
import requests
import base64

BASE_URL = "http://192.168.50.152:5000"
API_KEY = "sk_live_abc123..."

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Step 1: Create person
person_data = {
    "person_id": "EMP001",
    "name": "John Doe",
    "email": "john@example.com",
    "department": "Engineering",
    "position": "Developer"
}

response = requests.post(
    f"{BASE_URL}/api/v1/persons",
    headers=headers,
    json=person_data
)

if response.json()["success"]:
    print("Person created!")

    # Step 2: Register face
    with open("john_face.jpg", "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")

    face_data = {
        "image": image_base64,
        "force_update": False
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/persons/EMP001/register-face",
        headers=headers,
        json=face_data
    )

    if response.json()["success"]:
        print("Face registered!")
        print(f"Total faces: {response.json()['data']['total_faces']}")
```

---

### Example 2: Pull Today's Attendance (Python)

```python
import requests
from datetime import date

BASE_URL = "http://192.168.50.152:5000"
API_KEY = "sk_live_abc123..."

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

today = date.today().isoformat()

response = requests.get(
    f"{BASE_URL}/api/v1/attendance",
    headers=headers,
    params={
        "start_date": today,
        "end_date": today,
        "limit": 1000
    }
)

data = response.json()
if data["success"]:
    records = data["data"]["records"]
    print(f"Total attendance records: {len(records)}")

    for record in records:
        print(f"{record['person_name']} - {record['check_in']}")
```

---

## 🐛 Troubleshooting

### Issue 1: Person appears in Persons tab but shows "0 registered faces"

**Cause:** Person created in attendance.db but no face encoding in faces.pkl

**Solution:**
1. Click [Register] button on the person card
2. Registration modal opens with pre-filled data
3. Ensure person's face is visible in camera
4. Click "Save Person"
5. Face will be registered and status will update

---

### Issue 2: Register button doesn't work

**Cause:** JavaScript error or modal not found

**Solution:**
1. Open browser console (F12)
2. Check for JavaScript errors
3. Ensure you're on index.html (not faces.html)
4. Refresh the page
5. Try clicking [Register] again

---

### Issue 3: Odoo can't connect to Face API

**Cause:** Network issue, wrong URL, or invalid API key

**Solution:**
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

### Issue 4: Face registration fails with "No face detected"

**Cause:** Poor image quality, lighting, or angle

**Solution:**
1. Ensure good lighting
2. Face should be front-facing
3. Face should fill at least 20% of image
4. Remove glasses/masks if possible
5. Try with different image

---

### Issue 5: Persons tab doesn't load

**Cause:** API endpoint error or network issue

**Solution:**
1. Check browser console for errors
2. Verify API server is running
3. Test endpoint manually:
   ```bash
   curl http://127.0.0.1:5000/api/v1/persons
   ```
4. Check backend logs for errors

---

## 📊 Monitoring & Maintenance

### Daily Tasks

1. **Check Attendance Records:**
   - Web Console → Timeline
   - Verify records are being created
   - Check for any anomalies

2. **Monitor System Status:**
   - Web Console → Top right status indicator
   - Should show: System Online (green)

3. **Review Persons Status:**
   - Web Console → Persons tab
   - Check how many have faces registered
   - Register faces for new persons if needed

---

### Weekly Tasks

1. **Backup Databases:**
   ```bash
   cd backend/data
   cp attendance.db attendance.db.backup
   cp faces.pkl faces.pkl.backup
   ```

2. **Review Logs:**
   - Check backend logs for errors
   - Review Odoo sync logs

3. **Performance Check:**
   - Monitor FPS in web console
   - Check if recognition is fast and accurate

---

### Monthly Tasks

1. **Clean Old Data:**
   - Archive old attendance records (optional)
   - Remove inactive persons (optional)

2. **Update System:**
   - Check for updates to dependencies
   - Test in staging environment first

3. **Review Statistics:**
   - Generate monthly reports
   - Analyze attendance patterns
   - Identify system improvements

---

## 🎓 Training Guide

### For HR Staff

**Task 1: Add New Employee with Face**
1. Create employee in Odoo HR
2. Upload face photo in employee form
3. Click "Register Face" button
4. Wait for confirmation
5. Verify in Face Attendance module

**Task 2: Check Attendance**
1. Open Face Attendance → Attendance Records
2. Filter by date and person
3. View check-in/check-out times
4. Export to Excel if needed

---

### For IT Administrators

**Task 1: Configure New API Server**
1. Get API key from backend
2. Add server in Odoo configuration
3. Test connection
4. Enable auto-sync

**Task 2: Troubleshoot Connection Issues**
1. Check API server health endpoint
2. Verify network connectivity
3. Check firewall rules
4. Review API logs
5. Test authentication

---

## 📄 Related Documentation

- **API_ENDPOINTS.md** - Complete API reference
- **ODOO_API_INTEGRATION.md** - Odoo integration guide
- **INTEGRATION_COMPLETE.md** - Implementation summary
- **PROJECT_OVERVIEW.md** - Odoo module architecture

---

**Last Updated:** 2025-01-15
**System Version:** 1.0.0
**Status:** ✅ Production Ready
