# 🎯 Person-Face Tracking System Documentation

## Overview

The enhanced face & person recognition system now includes **persistent tracking** with unique IDs that link detected persons with their recognized faces. This provides continuous "who-and-where" tracking across frames.

---

## 🚀 Key Features

### 1. **Persistent Tracking IDs**
- Each person detected gets a unique ID (e.g., `person_1`, `person_2`)
- IDs persist across frames even when face is temporarily not visible
- Uses IoU-based matching to maintain identity continuity

### 2. **Person-Face Linking**
- Automatically links detected faces to their corresponding person bounding box
- Validates face is inside person region before linking
- Maintains face recognition data even when face temporarily disappears

### 3. **Color-Coded Bounding Boxes**

| Color  | Status | Description |
|--------|--------|-------------|
| 🟩 **Green** | Known | Face recognized and matched to database |
| 🟨 **Yellow** | Tracking | Person detected, face not yet identified |
| 🟥 **Red** | Unknown | Face detected but not in database |

### 4. **Intelligent Status Management**
- **Tracking**: Initial state when person first detected
- **Known**: After face matched to database
- **Unknown**: After face detected but not recognized
- Status persists with ID until face re-identification

---

## 🧠 System Architecture

### Backend Components

#### **1. SimpleTracker (`tracker.py`)**
Main tracking engine implementing ByteTrack-style algorithm:

```python
person_tracker = SimpleTracker(
    iou_threshold=0.3,      # Min IoU for matching
    max_age=30,             # Max frames to keep lost tracks
    min_hits=1,             # Min detections before confirmed
    face_memory_time=3.0    # Remember face for 3 seconds
)
```

**Key Methods:**
- `update(detections)` - Update tracker with new person detections
- `update_face_recognition(track_id, face_bbox, name, confidence)` - Link face data to track
- `get_all_tracks()` - Get all active tracked persons

#### **2. TrackedPerson Data Structure**
```python
@dataclass
class TrackedPerson:
    track_id: int                    # Unique persistent ID
    person_bbox: List[float]         # [x1, y1, x2, y2]
    confidence: float                # Person detection confidence

    # Face recognition
    face_bbox: Optional[List[float]] # Face location
    name: str                        # Recognized name or "—"
    face_confidence: float           # Face match confidence
    status: str                      # "Known", "Unknown", "Tracking"

    # Tracking metadata
    last_seen: float                 # Timestamp
    frames_tracked: int              # Total frames
    frames_lost: int                 # Consecutive lost frames
    face_last_seen: float           # Last face detection time
```

#### **3. Detection Pipeline**

```
Frame Input
    ↓
[1] YOLO Person Detection
    ↓
[2] Update Tracker (assign/update IDs)
    ↓
[3] For each tracked person:
    - Extract person region
    - Detect faces in region
    - Match faces to database
    - Link face to person ID
    ↓
[4] Return tracked persons with status
    ↓
Frontend Display
```

### Frontend Components

#### **Bounding Box Rendering**
Each tracked person displays:
```
┌─────────────────────────┐  ← Color-coded border
│ ID: person_3            │
│ Name: Tovfikur Rahman   │  ← Green if Known
│ Conf: 92%               │  ← Face confidence
│ Status: Known           │  ← Color-coded status
└─────────────────────────┘
        ↓
    [Person Box]
        ↓
    [Face Box] ← Dashed line indicator
```

---

## 📊 Tracking Behavior

### Scenario 1: New Person Enters
```
Frame 1: Person detected → Assign ID: person_1
         Status: "Tracking" (Yellow box)
         Name: "—"

Frame 2: Face detected in person box
         → Run face recognition

Frame 3: Face matched to "Tovfikur Rahman"
         → Update person_1
         Status: "Known" (Green box)
         Name: "Tovfikur Rahman"
         Confidence: 0.92
```

### Scenario 2: Face Temporarily Hidden
```
Frame 10: person_1 turns away, face not visible
          → Keep tracking with last known data
          Status: "Known" (Green box)
          Name: "Tovfikur Rahman" (remembered)

Frame 15: Face visible again
          → Re-detect face, update confidence
          Same ID: person_1 maintained
```

### Scenario 3: Unknown Person
```
Frame 1: New person → person_2
         Status: "Tracking" (Yellow)

Frame 3: Face detected but not in database
         Status: "Unknown" (Red box)
         Name: "Unknown"
```

### Scenario 4: Person Leaves and Returns
```
Frame 20: person_1 exits frame
          → frames_lost starts incrementing

Frame 40: Lost for 30 frames
          → Track removed from memory

Frame 45: Same person re-enters
          → New ID assigned: person_3
          → Need face re-recognition
```

---

## ⚙️ Configuration Parameters

### Tracker Settings
```python
# backend/app.py

person_tracker = SimpleTracker(
    iou_threshold=0.3,       # Lower = stricter matching
    max_age=30,              # Higher = remember longer
    min_hits=1,              # Confirmations before tracking
    face_memory_time=3.0     # Face data retention (seconds)
)
```

### Face Recognition Settings
```python
# Tolerance for face matching
tolerance = 0.6  # Lower = stricter matching

# Confidence threshold for events
event_threshold = 0.7  # Only log high-confidence matches
```

---

## 🔧 API Response Format

### `/api/recognize` Response
```json
{
  "success": true,
  "timestamp": "2025-11-10T12:30:45.123Z",
  "active_tracks": 2,
  "results": [
    {
      "track_id": 1,
      "person_bbox": [120.5, 50.2, 340.8, 480.1],
      "person_confidence": 0.95,
      "face_bbox": [180.3, 120.5, 280.7, 250.3],
      "name": "Tovfikur Rahman",
      "face_confidence": 0.92,
      "status": "Known",
      "frames_tracked": 45,
      "color": [0, 255, 0]
    },
    {
      "track_id": 2,
      "person_bbox": [450.0, 80.0, 620.0, 450.0],
      "person_confidence": 0.88,
      "face_bbox": null,
      "name": "—",
      "face_confidence": 0.0,
      "status": "Tracking",
      "frames_tracked": 5,
      "color": [255, 255, 0]
    }
  ]
}
```

---

## 🎨 Frontend Display Logic

### Color Mapping
```javascript
// Determined by backend TrackedPerson.get_color()
const colors = {
  "Known": "rgb(0, 255, 0)",      // Green
  "Unknown": "rgb(255, 0, 0)",    // Red
  "Tracking": "rgb(255, 255, 0)"  // Yellow
};
```

### Label Format
```javascript
// Multi-line label with color-coded info
ID: person_{track_id}           // White, bold
Name: {name}                     // Green if Known, white otherwise
Conf: {confidence}%              // Orange (if available)
Status: {status}                 // Color-coded by status
```

---

## 📈 Performance Optimizations

1. **IoU-based Matching**: O(n×m) complexity, efficient for typical scenarios
2. **Face Memory**: Prevents re-processing same face every frame
3. **Lazy Cleanup**: Removes old tracks only when necessary
4. **Single Face Processing**: Only processes primary face per person

---

## 🔮 Future Extensions

### Planned Features
- [ ] **Cross-camera Re-identification**: Track same person across multiple cameras
- [ ] **Movement Analytics**: Log entry/exit times, dwell time, trajectory
- [ ] **Historical Tracking**: Database logging with timestamps
- [ ] **Deep SORT Integration**: More robust tracking with appearance features
- [ ] **Multi-face Tracking**: Handle multiple faces per person
- [ ] **Confidence Smoothing**: Average confidence over time for stability

### Potential Enhancements
```python
# Example: Movement tracking
class TrackedPerson:
    trajectory: List[Tuple[float, float]]  # Center positions over time
    entry_time: datetime
    exit_time: Optional[datetime]
    total_dwell_time: float
```

---

## 🧪 Testing Guide

### Manual Test Scenarios

1. **Single Person Tracking**
   - Start camera
   - Walk into frame
   - Verify: Yellow box appears with ID
   - Turn to show face
   - Verify: Box turns green, name appears
   - Turn away
   - Verify: Stays green with remembered name

2. **Multiple People**
   - Have 2-3 people in frame
   - Verify: Each gets unique ID
   - Verify: IDs don't swap when people move

3. **Face Hiding**
   - Be recognized (green box)
   - Cover face for 2 seconds
   - Verify: Stays green
   - Cover face for 5 seconds
   - Verify: May switch to yellow after face memory expires

4. **Exit and Re-entry**
   - Get recognized as person_1
   - Exit frame completely
   - Wait 5 seconds
   - Re-enter frame
   - Verify: May get new ID (e.g., person_2)
   - Verify: Re-recognition works

---

## 📝 Debug Logging

### Backend Logs
```
[DEBUG] Detected 2 persons
[DEBUG] Tracking 2 persons
[DEBUG] Track 1: Found 1 faces
[DEBUG] Track 1: Recognized as Tovfikur Rahman (0.920)
[DEBUG] Returning 2 tracked persons to frontend
```

### Frontend Console
```javascript
[DEBUG] Recognition response: {
  active_tracks: 2,
  results: [
    { id: 1, name: "Tovfikur Rahman", status: "Known", frames: 45 },
    { id: 2, name: "—", status: "Tracking", frames: 5 }
  ]
}
```

---

## 🎯 Summary

The new tracking system provides:
- ✅ Persistent person IDs across frames
- ✅ Automatic person-face linking
- ✅ Color-coded status visualization
- ✅ Intelligent face memory
- ✅ Robust tracking continuity
- ✅ Clean API with full tracking metadata

**Result**: You can now see "who is where" with continuous tracking, even when faces are temporarily hidden.
