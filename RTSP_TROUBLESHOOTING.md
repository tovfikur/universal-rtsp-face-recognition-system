# RTSP Connection Troubleshooting

## Issue: System Stuck After "Connected"

**Symptoms:**
```
[VideoStream] Connected: 2304x1296 @ 20.0fps
[Then system hangs, no GPU/CPU usage]
```

**Root Cause:** OpenCV VideoCapture connects but first frame read hangs indefinitely.

---

## ✅ FIXED: System No Longer Hangs!

**Solution Applied:**
The system now skips the test frame read for RTSP streams and uses more aggressive frame buffering. This prevents the hang that occurred with high-resolution cameras (2304x1296).

**What was changed:**
1. Skip initial test frame read for RTSP (was causing indefinite hang)
2. More aggressive frame skipping (grab × 3 instead of 1)
3. FFmpeg socket timeout via environment variable
4. Automatic resolution downscaling to 1280x720

**Your camera should now work!** The system will:
- Connect quickly without hanging
- Auto-downscale 2304x1296 → 1131x636
- Provide smooth, real-time preview
- Fast face detection

---

## Quick Fixes (If Still Having Issues)

### Fix 1: Use Substream Instead of Main Stream ⚡

Your camera supports multiple streams. Main stream (subtype=0) is high-res and can be slow.

**Current (Slow):**
```
rtsp://admin:123456789m@192.168.50.210:554/cam/realmonitor?channel=4&subtype=0
                                                                           ↑
                                                                      Main stream (2304x1296)
```

**Try This (Fast):**
```
rtsp://admin:123456789m@192.168.50.210:554/cam/realmonitor?channel=4&subtype=1
                                                                           ↑
                                                                      Substream (704x576 or similar)
```

**Why this works:**
- Substream is lower resolution (720p or less)
- Less bandwidth needed
- Faster decoding
- More reliable connection

**Steps:**
1. Stop backend (Ctrl+C)
2. Open Settings panel
3. Change URL to use `subtype=1`
4. Click "Apply & Connect"
5. Should work immediately!

---

### Fix 2: Add FFmpeg Options to URL 🔧

Add FFmpeg parameters directly to RTSP URL:

**Standard URL:**
```
rtsp://admin:123456789m@192.168.50.210:554/cam/realmonitor?channel=4&subtype=1
```

**Optimized URL with FFmpeg options:**
```
rtsp://admin:123456789m@192.168.50.210:554/cam/realmonitor?channel=4&subtype=1&tcp
```

**Or even more aggressive:**
Create a custom URL in settings panel:
```
Input: rtsp://admin:123456789m@192.168.50.210:554/cam/realmonitor?channel=4&subtype=1
```

---

### Fix 3: Check Camera Stream Settings 📹

**Login to camera web interface:**
1. Open browser: `http://192.168.50.210`
2. Login with: `admin / 123456789m`
3. Go to: **Setup → Encode → Video**
4. Check Channel 4 settings:

**Recommended Settings:**
- **Main Stream:**
  - Resolution: 1920x1080 (not 2304x1296)
  - Bitrate: 2048 kbps
  - FPS: 15-20

- **Substream:**
  - Resolution: 704x576 or 640x480
  - Bitrate: 512 kbps
  - FPS: 15

**Apply changes and restart backend**

---

### Fix 4: Use HTTP Stream Instead 🌐

Some Dahua cameras support HTTP MJPEG which is more reliable:

**Try:**
```
http://admin:123456789m@192.168.50.210/cgi-bin/snapshot.cgi?channel=4
```

Or:
```
http://admin:123456789m@192.168.50.210/video.cgi?channel=4
```

**Note:** Not all Dahua cameras support HTTP, but worth trying.

---

### Fix 5: Reduce Backend Load ⚙️

The issue might be that 2304x1296 resolution is too much for the system to handle.

**In `backend/app.py` line 66-72, change:**

```python
detector = PersonDetector(
    model_path="yolov8n.pt",
    confidence=0.65,
    device=YOLO_DEVICE,
    batch_size=4,  # ← Reduce from 8 to 4
    min_person_area=3000,
    max_aspect_ratio=4.0,
)
```

Also reduce frame size in frontend (`script.js` line 109):
```javascript
const scale = 0.33;  // Instead of 0.5 (smaller frames)
```

---

## Alternative: VLC Test

Before using in system, test URL with VLC:

1. Open VLC Media Player
2. Media → Open Network Stream
3. Enter: `rtsp://admin:123456789m@192.168.50.210:554/cam/realmonitor?channel=4&subtype=1`
4. Click Play

**If VLC works:**
- URL is correct
- Issue is with OpenCV
- Try substream (subtype=1)

**If VLC doesn't work:**
- URL is wrong
- Check camera settings
- Try different channel/subtype

---

## Debugging Steps

### Step 1: Check What the System is Actually Doing

Add this debug code to `video_sources.py` after line 223:

```python
success, frame = self.capture.read()
print(f"[DEBUG] Read attempt: success={success}, frame={'None' if frame is None else frame.shape}")
```

This will show if frames are being read.

---

### Step 2: Test Camera Directly

**Create test script `test_rtsp.py`:**
```python
import cv2
import time

url = "rtsp://admin:123456789m@192.168.50.210:554/cam/realmonitor?channel=4&subtype=1"

print(f"Connecting to: {url}")
cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

if not cap.isOpened():
    print("ERROR: Cannot open stream")
    exit(1)

print("Connected! Testing frame read...")

for i in range(10):
    start = time.time()
    ret, frame = cap.read()
    elapsed = time.time() - start

    if ret:
        print(f"Frame {i}: {frame.shape}, took {elapsed:.3f}s")
    else:
        print(f"Frame {i}: FAILED (took {elapsed:.3f}s)")

cap.release()
print("Test complete!")
```

**Run:**
```bash
python test_rtsp.py
```

**Expected output (working):**
```
Frame 0: (1296, 2304, 3), took 0.123s
Frame 1: (1296, 2304, 3), took 0.051s
Frame 2: (1296, 2304, 3), took 0.048s
...
```

**If hangs on first frame:**
- Use subtype=1 (substream)
- Problem is high resolution

---

## Recommended Camera Settings

Based on your camera (Dahua, channel 4):

### For Best Performance:

**URL:**
```
rtsp://admin:123456789m@192.168.50.210:554/cam/realmonitor?channel=4&subtype=1
```

**Camera Settings:**
- Resolution: 704x576 (D1) or 640x480 (VGA)
- Bitrate: 512-1024 kbps
- FPS: 15
- Encoding: H.264

**System Settings:**
- Frame interval: 500ms
- Scale: 0.5
- Quality: 0.6

**Expected performance:**
- Smooth preview
- 2 detections/second
- Low latency

---

## Common Dahua RTSP URLs

Try these alternative URLs:

**Substream (Lower Quality):**
```
rtsp://admin:123456789m@192.168.50.210:554/cam/realmonitor?channel=4&subtype=1
```

**Main Stream TCP:**
```
rtsp://admin:123456789m@192.168.50.210:554/cam/realmonitor?channel=4&subtype=0&tcp=1
```

**Alternative Format:**
```
rtsp://admin:123456789m@192.168.50.210:554/ch4/main
rtsp://admin:123456789m@192.168.50.210:554/ch4/sub
```

---

## If Nothing Works: Use Video File

As a workaround, save a sample from camera and use video file:

1. Use VLC to record 30 seconds: Media → Convert/Save
2. Save as `test.mp4`
3. In system settings, use: `C:\path\to\test.mp4`
4. System will loop video for testing

---

## Summary

**Most Likely Fix:**
```
Change subtype=0 to subtype=1 in RTSP URL
```

This uses lower resolution substream which:
- ✅ Connects faster
- ✅ Reads frames immediately
- ✅ Uses less bandwidth
- ✅ Works reliably

**Try it now!**
