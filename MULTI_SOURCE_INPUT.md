# Multi-Source Video Input System

## Overview

The system now supports multiple video input sources:
- 🎥 **USB Webcams** (local cameras)
- 📡 **RTSP Streams** (IP cameras)
- 🌐 **HTTP/HTTPS Streams** (MJPEG, HLS)
- 📺 **RTMP Streams** (live streaming)
- 📁 **Video Files** (.mp4, .avi, .mkv, etc.)

All recognition features work identically across all source types!

---

## Features

### ✅ Unified Video Source Manager
- **Single interface** for all source types
- **Automatic reconnection** for network streams
- **Health monitoring** with live status
- **Hot-swapping** between sources without restart

### ✅ Enhanced UI
- **Quick examples** for common sources
- **Test connection** before applying
- **Current source display**
- **Real-time status updates**

### ✅ Robust Stream Handling
- **Auto-reconnect** on connection loss
- **Buffer optimization** per source type
- **Format detection** and configuration
- **Error recovery** with detailed logging

---

## How to Use

### Method 1: Using the UI

1. **Open Settings Panel**
   - Click "⚙ Settings" button in top-right

2. **Enter Video Source**
   - Type source in the "Video Source" field
   - OR click a "Quick Example" button

3. **Test Connection (Optional)**
   - Click "🔍 Test Connection" to validate
   - Wait for success/error message

4. **Apply Source**
   - Click "✓ Apply & Connect"
   - System will switch to new source

---

## Supported Source Formats

### 1. USB Webcam

**Format:** `0`, `1`, `2`, etc.

**Examples:**
```
0          # Default webcam
1          # External USB camera
2          # Third camera
```

**Notes:**
- Most common: `0` for built-in webcam
- Increment number for additional cameras
- Must be connected before starting

---

### 2. RTSP Stream (IP Camera)

**Format:** `rtsp://[user:pass@]ip:port/path`

**Examples:**
```
rtsp://admin:password@192.168.1.100:554/stream
rtsp://192.168.1.100:554/cam/realmonitor?channel=1&subtype=0
rtsp://user:pass@example.com/live
```

**Common Brands:**
- **Hikvision:** `rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101`
- **Dahua:** `rtsp://admin:password@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0`
- **Axis:** `rtsp://root:pass@192.168.0.90/axis-media/media.amp`
- **Reolink:** `rtsp://admin:password@192.168.1.10:554/h264Preview_01_main`

**Port:** Usually `554` (RTSP standard)

**Notes:**
- Requires camera credentials (username/password)
- Check camera documentation for exact path
- Some cameras use different ports

---

### 3. HTTP/HTTPS Stream

**Format:** `http://ip:port/path` or `https://ip:port/path`

**Examples:**
```
http://192.168.1.100:8080/video
http://example.com:8080/stream.mjpg
https://secure-cam.example.com/live
```

**Common Formats:**
- **MJPEG:** `/video.mjpg`, `/stream.mjpg`
- **HLS:** `/stream.m3u8`

**Notes:**
- Common for ESP32-CAM, Raspberry Pi cameras
- Usually port `8080` or `8081`
- Supports both HTTP and HTTPS

---

### 4. RTMP Stream

**Format:** `rtmp://server:port/app/stream`

**Examples:**
```
rtmp://192.168.1.100/live/stream
rtmp://streaming-server.com:1935/app/stream
```

**Notes:**
- Used for live streaming platforms
- Usually port `1935`
- Less common for surveillance

---

### 5. Video File

**Format:** `/path/to/file.ext`

**Examples:**
```
C:\Videos\sample.mp4
/home/user/videos/recording.avi
./test_footage.mkv
```

**Supported Formats:**
- `.mp4` (H.264, H.265)
- `.avi` (various codecs)
- `.mkv` (Matroska)
- `.mov` (QuickTime)
- `.flv` (Flash Video)
- `.webm` (WebM)

**Notes:**
- File plays in loop (restarts at end)
- Useful for testing/development
- Not live stream

---

## API Endpoints

### GET `/api/sources/current`

Get current video source information.

**Response:**
```json
{
  "success": true,
  "source": "0",
  "status": {
    "connected": true,
    "alive": true,
    "source_type": "webcam",
    "width": 1280,
    "height": 720,
    "fps": 30.0,
    "reconnect_count": 0,
    "description": "Webcam 0"
  }
}
```

---

### POST `/api/sources/change`

Change to a new video source.

**Request:**
```json
{
  "source": "rtsp://admin:password@192.168.1.100:554/stream"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Switched to source: rtsp://...",
  "source": "rtsp://admin:password@192.168.1.100:554/stream"
}
```

---

### POST `/api/sources/validate`

Validate if a source is accessible before switching.

**Request:**
```json
{
  "source": "rtsp://192.168.1.100:554/stream"
}
```

**Response (Success):**
```json
{
  "success": true,
  "valid": true,
  "message": "Source is valid",
  "source": "rtsp://192.168.1.100:554/stream"
}
```

**Response (Failure):**
```json
{
  "success": true,
  "valid": false,
  "message": "Cannot open source: rtsp://...",
  "source": "rtsp://192.168.1.100:554/stream"
}
```

---

## Configuration

### Backend Configuration

In `backend/video_sources.py`:

```python
stream = EnhancedVideoStream(
    source=source,
    reconnect_delay=5.0,        # Wait 5s before reconnect attempt
    max_reconnect_attempts=0,   # 0 = infinite reconnects
    buffer_size=1               # Low latency (1 frame buffer)
)
```

**Parameters:**
- `reconnect_delay`: Seconds between reconnection attempts
- `max_reconnect_attempts`: 0 for infinite, N for max attempts
- `buffer_size`: Frame buffer size (1 = lowest latency)

---

### Source-Specific Optimizations

The system automatically optimizes settings based on source type:

**Webcam:**
```python
- Buffer size: 1
- FPS: 30
- Resolution: 1280x720 (if supported)
```

**RTSP:**
```python
- Buffer size: 1 (low latency)
- Codec: H.264
- Auto-reconnect: Enabled
```

**HTTP:**
```python
- Standard settings
- Auto-reconnect: Enabled
```

---

## Troubleshooting

### Issue: Cannot connect to RTSP camera

**Solutions:**
1. **Check credentials:** Ensure username/password are correct
2. **Verify URL:** Check camera documentation for correct RTSP path
3. **Test with VLC:**
   - Open VLC Media Player
   - Media → Open Network Stream
   - Enter same RTSP URL
   - If VLC can't connect, URL is wrong

4. **Check network:**
   - Ping camera IP: `ping 192.168.1.100`
   - Check firewall rules
   - Ensure port 554 is open

5. **Try different paths:**
   ```
   rtsp://ip:554/stream
   rtsp://ip:554/live
   rtsp://ip:554/cam0
   rtsp://ip:554/Streaming/Channels/101
   ```

---

### Issue: Stream disconnects frequently

**Solutions:**
1. **Check network stability:**
   - WiFi signal strength
   - Network bandwidth
   - Router performance

2. **Increase reconnect delay:**
   ```python
   reconnect_delay=10.0  # Wait longer between attempts
   ```

3. **Check camera load:**
   - Too many connections to camera
   - Camera overheating
   - Camera firmware issues

---

### Issue: Video is laggy/choppy

**Solutions:**
1. **Reduce resolution:** Configure camera to lower resolution
2. **Increase buffer:** `buffer_size=3` for smoother playback
3. **Check network:** Ensure sufficient bandwidth
4. **Reduce frame rate:** Camera settings (e.g., 15 FPS instead of 30)

---

### Issue: Wrong source type detected

The system auto-detects source type. If wrong:

**Check:**
```python
# In backend logs
[VideoStream] Connecting to RTSP Stream: rtsp://...
```

**Override if needed:**
Modify `video_sources.py` → `_detect_source_type()`

---

## Examples by Use Case

### Use Case 1: Single USB Webcam
```
Source: 0
```
Simple, most common setup.

---

### Use Case 2: Multiple USB Cameras
```
Camera 1: 0
Camera 2: 1

# Switch between them via UI
```

---

### Use Case 3: IP Camera Network
```
Front Door:    rtsp://admin:pass@192.168.1.100:554/stream
Back Yard:     rtsp://admin:pass@192.168.1.101:554/stream
Garage:        rtsp://admin:pass@192.168.1.102:554/stream

# Switch between cameras via UI
```

---

### Use Case 4: Mixed Sources
```
Local Webcam:  0
RTSP Camera:   rtsp://192.168.1.100:554/stream
HTTP Stream:   http://192.168.1.200:8080/video

# Switch between any source type
```

---

### Use Case 5: Testing with Video File
```
Source: C:\test_videos\crowd.mp4

# Test recognition on recorded footage
```

---

## Advanced Features

### 1. Stream Health Monitoring

Check if stream is alive:
```javascript
const response = await fetch("/api/sources/current");
const data = await response.json();

if (data.status.alive) {
  console.log("Stream is healthy");
} else {
  console.log("Stream is dead - reconnecting...");
}
```

---

### 2. Auto-Reconnection

Streams automatically reconnect on failure:
```
Connection lost → Wait 5s → Reconnect → Success/Retry
```

Logs:
```
[VideoStream] Connection lost
[VideoStream] Reconnecting... (attempt 1)
[VideoStream] Connected: 1280x720 @ 30fps
```

---

### 3. Hot-Swapping Sources

Switch sources without restarting:
```python
# User clicks "Apply & Connect"
# 1. Stop old stream
# 2. Create new stream
# 3. Recognition continues automatically
```

No downtime!

---

## Security Considerations

### 1. Credential Management

**Bad:**
```
http://admin:12345@192.168.1.100/stream
```
Credentials in URL (visible in logs)

**Better:**
```
# Use environment variables
CAMERA_USER=admin
CAMERA_PASS=securePassword123

rtsp://${CAMERA_USER}:${CAMERA_PASS}@192.168.1.100:554/stream
```

---

### 2. Network Security

- **Use VLANs:** Isolate camera network
- **Firewall Rules:** Limit access to camera ports
- **HTTPS/TLS:** Use encrypted streams when possible
- **Change Defaults:** Change default camera passwords

---

### 3. Access Control

- **Limit exposure:** Don't expose cameras to internet
- **VPN Access:** Use VPN for remote access
- **Authentication:** Require login for video sources

---

## Performance Tips

1. **Low latency streams:** Use `buffer_size=1`
2. **Smooth playback:** Use `buffer_size=3`
3. **Multiple cameras:** Process frames at 300ms intervals (unchanged)
4. **High resolution:** Recognition works better with 720p+
5. **Frame rate:** 15-30 FPS is ideal (higher doesn't help much)

---

## Status: ✅ READY

The multi-source input system is fully functional!

**Key Features:**
- ✅ Supports webcam, RTSP, HTTP, RTMP, files
- ✅ Auto-reconnection for network streams
- ✅ Hot-swapping without restart
- ✅ Test connection before switching
- ✅ Real-time health monitoring
- ✅ Easy-to-use UI with examples

**All recognition features work identically across all sources!** 🚀
