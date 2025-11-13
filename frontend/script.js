console.log("[Init] Script loading...");

const ui = {
  video: document.getElementById("liveVideo"),
  canvas: document.getElementById("overlayCanvas"),
  ctx: document.getElementById("overlayCanvas")?.getContext("2d"),
  offscreenCanvas: null, // Will be created dynamically
  offscreenCtx: null,
  loadingOverlay: document.getElementById("loadingOverlay"),
  statusBadge: document.getElementById("statusBadge"),
  eventsList: document.getElementById("eventsList"),
  faceGallery: document.getElementById("faceGallery"),
  recognizedCounter: document.getElementById("recognizedCounter"),
  remoteStream: document.getElementById("remoteStream"),
  cameraSourceInput: document.getElementById("cameraSourceInput"),
  alertContainer: document.getElementById("alertContainer"),
  systemStatus: document.getElementById("systemStatus"),
  fpsCounter: document.getElementById("fpsCounter"),
  sourceDisplay: document.getElementById("sourceDisplay"),
  stopCameraBtn: document.getElementById("stopCameraBtn"),
  startCameraBtn: document.getElementById("startCameraBtn"),
  snapshotImage: document.getElementById("snapshotImage"),
  snapshotPlaceholder: document.getElementById("snapshotPlaceholder"),
  snapshotTime: document.getElementById("snapshotTime"),
  snapshotHistoryGrid: document.getElementById("snapshotHistoryGrid"),
};

console.log("[Init] UI elements loaded:", {
  video: !!ui.video,
  canvas: !!ui.canvas,
  cameraSourceInput: !!ui.cameraSourceInput
});

const FACE_PLACEHOLDER =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Crect width='100%25' height='100%25' fill='%232b2b40'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%239ea6c9' font-family='Inter' font-size='18'%3ENo Image%3C/text%3E%3C/svg%3E";

const DEBUG = true; // Global debug flag

const state = {
  stream: null,
  recognitionTimer: null,
  recognitionRunning: false, // Flag to control recognition loop
  events: [],
  faces: [],
  frameInterval: 500, // Send frame every 500ms (faster for RTSP)
  remoteSource: null,
  modal: null,
  isProcessing: false,
  lastResults: [],
  skipFrames: 0,
  frameSkipCount: 0,
  eventUpdateInterval: null,
  requestTimeout: 5000,
  consecutiveFailures: 0,
  maxTimeout: 10000,
  minFrameInterval: 300, // Minimum 300ms between frames
  lowResMode: false,
  processingTimes: [],
  adaptiveQuality: 0.6, // Lower quality for faster encoding (RTSP optimization)
  debug: DEBUG,
  lastFrameTime: 0,
  fps: 0,
  frameCount: 0,
  lastFpsUpdate: 0,
  isRTSP: false, // Track if using RTSP source
  lastOverlayUpdateTime: 0, // Track when overlay was last updated
  overlayMaxAge: 1000, // Clear overlay if no update for 1 second
  bboxScaleX: 1.0, // Bbox coordinate scale factor for X axis
  bboxScaleY: 1.0, // Bbox coordinate scale factor for Y axis
  snapshotInterval: null, // Interval for snapshot polling
  snapshotRunning: false, // Flag to control snapshot updates
};

const registerModal = new bootstrap.Modal(
  document.getElementById("registerModal")
);

// Performance monitoring
const performanceMonitor = {
  frameCount: 0,
  lastTime: performance.now(),
  fps: 0,

  update() {
    this.frameCount++;
    const now = performance.now();
    if (now - this.lastTime >= 1000) {
      this.fps = Math.round((this.frameCount * 1000) / (now - this.lastTime));
      this.frameCount = 0;
      this.lastTime = now;
      // Update FPS display if needed (with null check)
      if (ui.statusBadge && ui.statusBadge.textContent && ui.statusBadge.textContent.includes("Streaming")) {
        updateStatus(`Streaming (${this.fps} FPS)`, "success");
      }
    }
  },
};

// ----------------------------------------------------------------------------- //
// Helpers
// ----------------------------------------------------------------------------- //
const showAlert = (message, type = "success", timeout = 4000) => {
  const alert = document.createElement("div");
  alert.className = `floating-alert ${type === "error" ? "error" : "success"}`;
  alert.textContent = message;
  ui.alertContainer.appendChild(alert);

  setTimeout(() => {
    alert.style.opacity = "0";
    setTimeout(() => alert.remove(), 400);
  }, timeout);
};

const updateStatus = (text, tone = "info") => {
  // Update system status indicator
  if (ui.systemStatus) {
    const statusDot = ui.systemStatus.querySelector('.status-dot');
    const statusText = ui.systemStatus.querySelector('.status-text');

    if (statusDot && statusText) {
      statusDot.classList.remove('offline', 'online', 'streaming');

      if (tone === 'success' || text.includes('Streaming')) {
        statusDot.classList.add('streaming');
        statusText.textContent = 'System Active';
      } else if (tone === 'danger' || text.includes('Offline')) {
        statusDot.classList.add('offline');
        statusText.textContent = 'System Offline';
      } else {
        statusDot.classList.add('online');
        statusText.textContent = 'System Online';
      }
    }
  }

  // Legacy badge update (kept for compatibility)
  if (ui.statusBadge) {
    ui.statusBadge.textContent = text;
    ui.statusBadge.classList.remove(
      "bg-danger",
      "bg-success",
      "bg-warning",
      "bg-info"
    );
    const map = {
      danger: "bg-danger",
      success: "bg-success",
      warning: "bg-warning",
      info: "bg-info",
    };
    ui.statusBadge.classList.add(map[tone] || "bg-info");
  }
};

const captureFrame = () => {
  // For remote sources (RTSP), backend captures frames directly
  // We only need to capture for webcam
  if (state.remoteSource) {
    return null; // Backend handles frame capture for remote sources
  }

  if (!ui.video.videoWidth) return null;

  // Adaptive scaling based on performance
  const scale = state.lowResMode ? 0.33 : 0.5;
  const buffer = document.createElement("canvas");
  buffer.width = ui.video.videoWidth * scale;
  buffer.height = ui.video.videoHeight * scale;
  const ctx = buffer.getContext("2d");

  // Use better image scaling algorithm in high res mode
  ctx.imageSmoothingEnabled = !state.lowResMode;
  ctx.imageSmoothingQuality = state.lowResMode ? "low" : "medium";

  ctx.drawImage(ui.video, 0, 0, buffer.width, buffer.height);
  return buffer.toDataURL("image/jpeg", state.adaptiveQuality);
};

// ----------------------------------------------------------------------------- //
// Snapshot Analysis Functions
// ----------------------------------------------------------------------------- //
const updateSnapshot = async () => {
  if (!state.snapshotRunning) return;

  try {
    const response = await fetch(`/api/snapshot?t=${Date.now()}`);

    if (response.ok && response.headers.get('content-type')?.includes('image')) {
      // Successfully got snapshot image
      const blob = await response.blob();
      const imageUrl = URL.createObjectURL(blob);

      // Update image
      if (ui.snapshotImage) {
        ui.snapshotImage.src = imageUrl;
        ui.snapshotImage.classList.remove('d-none');
      }

      // Hide placeholder
      if (ui.snapshotPlaceholder) {
        ui.snapshotPlaceholder.classList.add('d-none');
      }

      // Update timestamp
      if (ui.snapshotTime) {
        const now = new Date();
        ui.snapshotTime.textContent = now.toLocaleTimeString();
      }
    } else {
      // No snapshot available yet
      if (DEBUG && Math.random() < 0.1) {
        console.log('[Snapshot] No snapshot available yet');
      }
    }
  } catch (error) {
    if (DEBUG && Math.random() < 0.05) {
      console.warn('[Snapshot] Error fetching snapshot:', error);
    }
  }
};

const updateSnapshotHistory = async () => {
  if (!ui.snapshotHistoryGrid) return;

  try {
    const response = await fetch('/api/snapshot/history');
    const data = await response.json();

    if (data.success && data.history && data.history.length > 0) {
      // Clear grid
      ui.snapshotHistoryGrid.innerHTML = '';

      // Add thumbnails (most recent first, max 4)
      const thumbnails = data.history.slice(0, 4);

      thumbnails.forEach((item, index) => {
        const thumbnail = document.createElement('div');
        thumbnail.className = 'snapshot-thumbnail';

        const img = document.createElement('img');
        img.src = `/api/snapshot/history/${item.filename}?t=${Date.now()}`;
        img.alt = `Snapshot ${index + 1}`;

        const timeLabel = document.createElement('div');
        timeLabel.className = 'snapshot-thumbnail-time';
        // Format timestamp: YYYYMMDD_HHMMSS -> HH:MM:SS
        const timeStr = item.timestamp.split('_')[1];
        const formatted = `${timeStr.slice(0, 2)}:${timeStr.slice(2, 4)}:${timeStr.slice(4, 6)}`;
        timeLabel.textContent = formatted;

        thumbnail.appendChild(img);
        thumbnail.appendChild(timeLabel);
        ui.snapshotHistoryGrid.appendChild(thumbnail);
      });

      // Fill remaining slots with placeholders
      while (ui.snapshotHistoryGrid.children.length < 4) {
        const placeholder = document.createElement('div');
        placeholder.className = 'snapshot-thumbnail-placeholder';
        placeholder.innerHTML = '<i class="fas fa-image"></i>';
        ui.snapshotHistoryGrid.appendChild(placeholder);
      }
    }
  } catch (error) {
    if (DEBUG && Math.random() < 0.05) {
      console.warn('[Snapshot History] Error fetching history:', error);
    }
  }
};

const startSnapshotUpdates = () => {
  if (state.snapshotRunning) return;

  console.log('[Snapshot] Starting snapshot updates');
  state.snapshotRunning = true;

  // Update immediately
  updateSnapshot();
  updateSnapshotHistory();

  // Then update every 2 seconds
  state.snapshotInterval = setInterval(() => {
    updateSnapshot();
    updateSnapshotHistory();
  }, 2000);
};

const stopSnapshotUpdates = () => {
  console.log('[Snapshot] Stopping snapshot updates');
  state.snapshotRunning = false;

  if (state.snapshotInterval) {
    clearInterval(state.snapshotInterval);
    state.snapshotInterval = null;
  }

  // Reset snapshot display
  if (ui.snapshotImage) {
    ui.snapshotImage.src = '';
    ui.snapshotImage.classList.add('d-none');
  }

  if (ui.snapshotPlaceholder) {
    ui.snapshotPlaceholder.classList.remove('d-none');
  }

  if (ui.snapshotTime) {
    ui.snapshotTime.textContent = '--';
  }
};

// ----------------------------------------------------------------------------- //
// FPS Counter (lightweight, no processing)
// ----------------------------------------------------------------------------- //
let fpsInterval = null;

const startFPSCounter = () => {
  if (fpsInterval) return;

  // Simple FPS counter based on video/stream playback
  fpsInterval = setInterval(() => {
    // For webcam - use video element
    if (state.stream && ui.video) {
      // Estimate FPS from video playback
      state.fps = 30; // Default webcam FPS
      if (ui.fpsCounter) ui.fpsCounter.textContent = state.fps;
    }
    // For RTSP - use MJPEG stream updates
    else if (state.remoteSource && ui.remoteStream) {
      state.fps = 25; // RTSP typical FPS
      if (ui.fpsCounter) ui.fpsCounter.textContent = state.fps;
    }

    // Update recognized counter to 0 (no processing)
    if (ui.recognizedCounter) {
      ui.recognizedCounter.textContent = 0;
    }
  }, 1000);
};

const stopFPSCounter = () => {
  if (fpsInterval) {
    clearInterval(fpsInterval);
    fpsInterval = null;
  }

  if (ui.fpsCounter) {
    ui.fpsCounter.textContent = 0;
  }

  if (ui.recognizedCounter) {
    ui.recognizedCounter.textContent = 0;
  }
};

// ----------------------------------------------------------------------------- //
// Overlay Drawing (DISABLED - overlays only in snapshot)
// ----------------------------------------------------------------------------- //
const drawOverlays = (results = []) => {
  // DISABLED: This function is no longer used for clean stream
  // Overlays only appear in the independent snapshot analysis
  return;
};

// Draw ellipse bounding box (instead of rectangle)
const drawSimpleBox = (ctx, box, color, item) => {
  const width = box.x2 - box.x1;
  const height = box.y2 - box.y1;

  // Calculate ellipse center and radii
  let centerX = box.x1 + width / 2;
  let centerY = box.y1 + height / 2;
  let radiusX = width / 2;
  let radiusY = height / 2;

  // Add padding to account for stroke width
  const strokePadding = 2;

  // Constrain ellipse to stay within canvas bounds
  const canvasWidth = ctx.canvas.width;
  const canvasHeight = ctx.canvas.height;

  // Check if ellipse would be clipped and adjust if needed
  if (centerX - radiusX < strokePadding) {
    // Too far left - shrink or shift
    centerX = radiusX + strokePadding;
  }
  if (centerX + radiusX > canvasWidth - strokePadding) {
    // Too far right - shrink or shift
    centerX = canvasWidth - radiusX - strokePadding;
  }
  if (centerY - radiusY < strokePadding) {
    // Too far top - shrink or shift
    centerY = radiusY + strokePadding;
  }
  if (centerY + radiusY > canvasHeight - strokePadding) {
    // Too far bottom - shrink or shift
    centerY = canvasHeight - radiusY - strokePadding;
  }

  // If still too large, reduce radius
  if (centerX - radiusX < strokePadding) {
    radiusX = centerX - strokePadding;
  }
  if (centerX + radiusX > canvasWidth - strokePadding) {
    radiusX = canvasWidth - centerX - strokePadding;
  }
  if (centerY - radiusY < strokePadding) {
    radiusY = centerY - strokePadding;
  }
  if (centerY + radiusY > canvasHeight - strokePadding) {
    radiusY = canvasHeight - centerY - strokePadding;
  }

  // Draw ellipse
  ctx.strokeStyle = color;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.ellipse(centerX, centerY, Math.max(radiusX, 5), Math.max(radiusY, 5), 0, 0, 2 * Math.PI);
  ctx.stroke();
};

// Draw simple label (positioned for ellipse)
const drawSimpleLabel = (ctx, box, color, item) => {
  const trackId = `person_${item.track_id}`;
  let label;

  if (item.status === "Known" && item.face_confidence > 0) {
    const conf = (item.face_confidence * 100).toFixed(0);
    // Include person ID if available
    const personIdLabel = item.person_id ? `[${item.person_id}] ` : '';
    label = `${trackId}: ${personIdLabel}${item.name} (${conf}%)`;
  } else if (item.status === "Unknown") {
    label = `${trackId}: Unknown`;
  } else {
    label = `${trackId}: Tracking...`;
  }

  ctx.font = "bold 14px Inter";
  const textMetrics = ctx.measureText(label);
  const padding = 8;
  const labelWidth = textMetrics.width + padding * 2;
  const labelHeight = 24;

  // Calculate center position for label (top of ellipse)
  const width = box.x2 - box.x1;
  const centerX = box.x1 + width / 2;
  const labelX = centerX - labelWidth / 2;

  // Simple background (centered above ellipse)
  ctx.fillStyle = "rgba(0, 0, 0, 0.85)";
  ctx.fillRect(labelX, box.y1 - labelHeight - 4, labelWidth, labelHeight);

  // Label text (centered)
  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 14px Inter";
  ctx.fillText(label, labelX + padding, box.y1 - 11);
};

// Draw stats overlay (FPS, track count)
const drawStatsOverlay = (ctx, results) => {
  const knownCount = results.filter((r) => r.status === "Known").length;
  const unknownCount = results.filter((r) => r.status === "Unknown").length;
  const trackingCount = results.filter((r) => r.status === "Tracking").length;

  const statsX = ui.canvas.width - 200;
  const statsY = 10;

  // Background
  ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
  ctx.fillRect(statsX, statsY, 190, 90);

  ctx.strokeStyle = "rgba(79, 70, 229, 0.8)";
  ctx.lineWidth = 2;
  ctx.strokeRect(statsX, statsY, 190, 90);

  // Stats text
  ctx.font = "bold 12px Inter";
  ctx.fillStyle = "#ffffff";

  ctx.fillText(`FPS: ${state.fps}`, statsX + 10, statsY + 20);
  ctx.fillStyle = "#00ff00";
  ctx.fillText(`✓ Known: ${knownCount}`, statsX + 10, statsY + 40);
  ctx.fillStyle = "#ff4444";
  ctx.fillText(`? Unknown: ${unknownCount}`, statsX + 10, statsY + 60);
  ctx.fillStyle = "#ffff00";
  ctx.fillText(`⟳ Tracking: ${trackingCount}`, statsX + 10, statsY + 80);
};

// Draw FPS counter
const drawFpsCounter = (ctx) => {
  ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
  ctx.fillRect(ui.canvas.width - 100, 10, 90, 30);

  ctx.font = "bold 12px Inter";
  ctx.fillStyle = "#ffffff";
  ctx.fillText(`FPS: ${state.fps}`, ui.canvas.width - 90, 30);
};

const pollRecognition = async () => {
  // DISABLED: Recognition polling is completely disabled for clean stream
  // All detection happens in the independent snapshot analysis thread
  // This function is kept for compatibility but does nothing

  if (DEBUG && Math.random() < 0.01) {
    console.log("[pollRecognition] DISABLED - detection only in snapshot analysis");
  }

  return; // Do nothing - no polling, no processing
};

const fetchEvents = async (silent = false) => {
  try {
    const response = await fetch("/api/events");
    if (!response.ok) throw new Error("Failed to load events");
    const data = await response.json();

    // Only update if events changed
    if (JSON.stringify(state.events) !== JSON.stringify(data.events)) {
      state.events = data.events || [];
      renderEvents();
    }

    if (!silent) {
      updateStatus("Ready", "success");
    }
  } catch (error) {
    if (!silent) {
      console.error("Event fetch error:", error);
    }
  }
};

const renderEvents = () => {
  // Use document fragment for better performance
  const fragment = document.createDocumentFragment();

  if (!state.events.length) {
    const li = document.createElement("li");
    li.className = "text-muted small text-center py-4";
    li.textContent = "No recognition events yet.";
    fragment.appendChild(li);
  } else {
    // Limit displayed events for performance
    const recentEvents = state.events.slice(-20).reverse();
    recentEvents.forEach((event) => {
      const li = document.createElement("li");
      li.className = "timeline-item";
      li.innerHTML = `
                <div>
                    <strong>${event.name}</strong>
                    <p class="mb-0 text-muted small">Confidence ${(
                      event.confidence * 100
                    ).toFixed(0)}%</p>
                </div>
                <span>${new Date(event.timestamp).toLocaleTimeString()}</span>
            `;
      fragment.appendChild(li);
    });
  }

  ui.eventsList.innerHTML = "";
  ui.eventsList.appendChild(fragment);
};

const fetchFaces = async () => {
  try {
    const response = await fetch("/api/faces");
    if (!response.ok) throw new Error("Failed to fetch faces");
    const data = await response.json();
    state.faces = data.faces || [];
    renderFaces();
  } catch (error) {
    showAlert("Unable to load registered faces", "error");
  }
};

const renderFaces = () => {
  // Only render if faceGallery element exists (on faces.html page)
  if (!ui.faceGallery) return;

  ui.faceGallery.innerHTML = "";
  if (!state.faces.length) {
    ui.faceGallery.innerHTML =
      '<p class="text-muted small">No faces registered yet.</p>';
    return;
  }

  // Use document fragment
  const fragment = document.createDocumentFragment();
  state.faces.forEach((face) => {
    const card = document.createElement("div");
    card.className = "face-card";
    const personId = face.person_id ? `<div class="badge bg-primary mb-1">${face.person_id}</div>` : '';
    card.innerHTML = `
            <img src="${face.image_url || FACE_PLACEHOLDER}" alt="${face.name}" loading="lazy">
            ${personId}
            <strong>${face.name}</strong>
            <small>${new Date(face.created_at).toLocaleString()}</small>
        `;
    fragment.appendChild(card);
  });
  ui.faceGallery.appendChild(fragment);
};

const startRecognitionLoop = () => {
  if (state.recognitionRunning) {
    console.log("[startRecognitionLoop] Already running, skipping");
    return; // Already running
  }

  console.log("[startRecognitionLoop] Starting FPS counter (recognition disabled for clean stream)");
  state.recognitionRunning = true;
  state.lastResults = []; // Clear old results

  // Start FPS counter for video display
  startFPSCounter();

  // Separate event fetching to avoid blocking
  if (state.eventUpdateInterval) clearInterval(state.eventUpdateInterval);
  state.eventUpdateInterval = setInterval(() => fetchEvents(true), 3000);
};

const stopRecognitionLoop = () => {
  console.log("[stopRecognitionLoop] Stopping recognition loop and FPS counter");
  state.recognitionRunning = false;
  state.lastResults = []; // Clear results

  // Stop FPS counter
  stopFPSCounter();

  // Clear canvas overlays
  const ctx = ui.canvas.getContext("2d");
  ctx.clearRect(0, 0, ui.canvas.width, ui.canvas.height);

  if (state.eventUpdateInterval) {
    clearInterval(state.eventUpdateInterval);
    state.eventUpdateInterval = null;
  }
};

const startCamera = async () => {
  if (!navigator.mediaDevices) {
    showAlert("Camera API not supported in this browser", "error");
    return;
  }
  try {
    ui.loadingOverlay.classList.remove("d-none");
    updateStatus("Starting...", "warning");

    // Request higher resolution for better face detection
    state.stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        frameRate: { ideal: 30 },
      },
      audio: false,
    });

    // Clear remote source and show video/canvas for webcam
    state.remoteSource = null;
    ui.remoteStream.src = ""; // Clear MJPEG stream
    ui.remoteStream.classList.add('d-none'); // Hide remote stream img
    ui.remoteStream.style.display = 'none';

    ui.video.style.display = 'block'; // Show video element
    ui.video.srcObject = state.stream;
    ui.canvas.style.display = 'block'; // Show canvas overlay for webcam

    // Wait for video metadata to load
    await new Promise((resolve) => {
      ui.video.onloadedmetadata = () => {
        ui.video.play();
        resolve();
      };
    });

    // Wait a bit more to ensure video dimensions are available
    await new Promise(resolve => setTimeout(resolve, 100));

    // Set canvas to match video actual dimensions
    if (ui.video.videoWidth && ui.video.videoHeight) {
      ui.canvas.width = ui.video.videoWidth;
      ui.canvas.height = ui.video.videoHeight;

      if (DEBUG) {
        console.log("[DEBUG] Video dimensions:", ui.video.videoWidth, "x", ui.video.videoHeight);
        console.log("[DEBUG] Canvas dimensions:", ui.canvas.width, "x", ui.canvas.height);
      }
    }

    ui.loadingOverlay.classList.add("d-none");
    updateStatus("Streaming", "success");
    startRecognitionLoop();
    startSnapshotUpdates(); // Start snapshot display updates
    showAlert("Camera started successfully");

    // Update UI buttons and source display
    if (ui.startCameraBtn) ui.startCameraBtn.classList.add("d-none");
    if (ui.stopCameraBtn) ui.stopCameraBtn.classList.remove("d-none");
    if (ui.sourceDisplay) ui.sourceDisplay.textContent = "Webcam";
  } catch (error) {
    console.error(error);
    ui.loadingOverlay.classList.add("d-none");
    updateStatus("Camera error", "danger");
    showAlert("Unable to access camera", "error");
  }
};

const stopCamera = () => {
  // Stop webcam if running
  if (state.stream) {
    state.stream.getTracks().forEach((track) => track.stop());
    state.stream = null;
  }

  // Stop remote stream if running
  if (state.remoteSource) {
    ui.remoteStream.src = ""; // Stop MJPEG stream
    state.remoteSource = null;
  }

  // Update UI
  if (ui.startCameraBtn) ui.startCameraBtn.classList.remove("d-none");
  if (ui.stopCameraBtn) ui.stopCameraBtn.classList.add("d-none");
  if (ui.sourceDisplay) ui.sourceDisplay.textContent = "None";

  ui.remoteStream.classList.add('d-none');
  ui.remoteStream.style.display = 'none';

  ui.video.srcObject = null;
  ui.video.style.display = 'block'; // Ensure video visible for next start
  stopRecognitionLoop();
  stopSnapshotUpdates(); // Stop snapshot updates
  updateStatus("Stopped", "warning");

  // Clear canvas
  ui.ctx.clearRect(0, 0, ui.canvas.width, ui.canvas.height);
  ui.canvas.style.display = 'block'; // Ensure canvas is visible for next start
};

const toggleCamera = () => {
  if (state.stream) {
    stopCamera();
  } else {
    startCamera();
  }
};

const registerFace = async (event) => {
  event.preventDefault();
  const nameInput = document.getElementById("personName");
  const personIdInput = document.getElementById("personId");
  const name = nameInput.value.trim();
  const person_id = personIdInput.value.trim();

  // Capture at full resolution for registration
  if (!ui.video.videoWidth) {
    showAlert("Start the camera first", "error");
    return;
  }

  const buffer = document.createElement("canvas");
  buffer.width = ui.video.videoWidth;
  buffer.height = ui.video.videoHeight;
  buffer.getContext("2d").drawImage(ui.video, 0, 0);
  const frame = buffer.toDataURL("image/jpeg", 0.9);

  if (!name || !person_id || !frame) {
    showAlert("Provide name, person ID and start the camera first", "error");
    return;
  }

  try {
    const response = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, person_id, image: frame }),
    });

    const data = await response.json();
    if (!response.ok || !data.success) {
      throw new Error(data.message || "Registration failed");
    }

    showAlert(`Face registered for ${name} (ID: ${person_id})`);
    nameInput.value = "";
    personIdInput.value = "";
    registerModal.hide();
    fetchFaces();
  } catch (error) {
    showAlert(error.message, "error");
  }
};

const clearDatabase = async () => {
  if (!confirm("This will delete all stored encodings. Continue?")) return;
  try {
    const response = await fetch("/api/clear", { method: "DELETE" });
    if (!response.ok) throw new Error("Failed to clear database");
    showAlert("Face database cleared");
    fetchFaces();
    fetchEvents();
  } catch (error) {
    showAlert(error.message, "error");
  }
};

// Get current video source
const getCurrentSource = async () => {
  try {
    const response = await fetch("/api/sources/current");
    const data = await response.json();
    if (data.success && data.source) {
      const currentSourceText = document.getElementById("currentSourceText");
      if (currentSourceText) {
        currentSourceText.textContent = data.source;
      }
    }
  } catch (error) {
    console.error("Error fetching current source:", error);
  }
};

// Validate video source
const validateSource = async (source) => {
  const statusDiv = document.getElementById("sourceStatus");
  if (!statusDiv) return;

  statusDiv.innerHTML = `
    <div class="alert alert-info small">
      <div class="spinner-border spinner-border-sm me-2" role="status"></div>
      Testing connection to: ${source}...
    </div>
  `;

  try {
    const response = await fetch("/api/sources/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source }),
    });

    const data = await response.json();

    if (data.valid) {
      statusDiv.innerHTML = `
        <div class="alert alert-success small">
          ✓ Connection successful! Source is valid.
        </div>
      `;
    } else {
      statusDiv.innerHTML = `
        <div class="alert alert-danger small">
          ✗ ${data.message}
        </div>
      `;
    }

    // Clear after 5 seconds
    setTimeout(() => {
      statusDiv.innerHTML = "";
    }, 5000);
  } catch (error) {
    statusDiv.innerHTML = `
      <div class="alert alert-danger small">
        ✗ Error: ${error.message}
      </div>
    `;
  }
};

// Change video source
const changeVideoSource = async () => {
  console.log("[changeVideoSource] Button clicked!");

  const source = ui.cameraSourceInput.value.trim();
  const statusDiv = document.getElementById("sourceStatus");

  console.log("[changeVideoSource] Source:", source);

  if (!source) {
    showAlert("Please enter a video source", "error");
    return;
  }

  if (statusDiv) {
    statusDiv.innerHTML = `
      <div class="alert alert-info small">
        <div class="spinner-border spinner-border-sm me-2" role="status"></div>
        Connecting to: ${source}...
      </div>
    `;
  }

  // STEP 1: Stop everything and clear frontend state
  console.log("[changeVideoSource] Stopping current stream and clearing state...");
  stopCamera();
  stopRecognitionLoop();

  // Clear all frontend state
  state.lastResults = [];
  state.isProcessing = false;
  state.lastFrameTime = 0;
  state.lastOverlayUpdateTime = 0;
  state.consecutiveFailures = 0;

  // Clear canvas overlay
  if (ui.canvas && ui.ctx) {
    ui.ctx.clearRect(0, 0, ui.canvas.width, ui.canvas.height);
  }
  ui.recognizedCounter.textContent = 0;

  console.log("[changeVideoSource] Frontend state cleared");

  try {
    // STEP 2: Tell backend to reset and change source
    const response = await fetch("/api/sources/change", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source, reset: true }), // Added reset flag
    });

    const data = await response.json();

    if (data.success) {
      // Detect if RTSP source for optimizations
      state.isRTSP = source.toLowerCase().startsWith('rtsp://');

      // Optimize settings for RTSP
      if (state.isRTSP) {
        state.frameInterval = 500;  // Faster interval for RTSP
        state.minFrameInterval = 500;
        state.adaptiveQuality = 0.6;  // Lower quality for speed
        console.log("[RTSP] Optimized settings: 500ms interval, quality 0.6");
      } else {
        state.frameInterval = 300;  // Standard interval for webcam
        state.minFrameInterval = 300;
        state.adaptiveQuality = 0.7;
      }

      showAlert(`✓ Connected to: ${source}`, "success");
      if (statusDiv) {
        statusDiv.innerHTML = `
          <div class="alert alert-success small">
            ✓ ${data.message}
            ${state.isRTSP ? '<br><small>RTSP optimizations enabled (500ms interval)</small>' : ''}
          </div>
        `;
      }

      // Update current source display
      getCurrentSource();

      // Stop current stream/recognition first
      stopCamera();
      stopRecognitionLoop();

      // NOW set remote source AFTER stopping (so stopCamera doesn't clear it)
      state.remoteSource = source;
      console.log("[Remote] state.remoteSource set to:", source);

      // For remote sources, use img element for MJPEG stream
      console.log("[Remote] Setting MJPEG stream to img element");

      // Hide video element (not used for RTSP)
      ui.video.style.display = 'none';

      // Show canvas overlay (for drawing bounding boxes)
      ui.canvas.style.display = 'block';

      // Show and set remote stream img with cache-busting timestamp
      ui.remoteStream.src = `/api/stream?source=${encodeURIComponent(source)}&t=${Date.now()}`;
      ui.remoteStream.classList.remove('d-none');
      ui.remoteStream.style.display = 'block';

      console.log("[Remote] Canvas overlay enabled for RTSP");
      console.log("[Remote] About to set onload handler and setTimeout");

      // Initialize canvas when image loads (MJPEG streams trigger this repeatedly)
      let onloadCount = 0;
      let lastImageUpdate = Date.now();

      ui.remoteStream.onload = function() {
        onloadCount++;
        lastImageUpdate = Date.now();
        const width = ui.remoteStream.naturalWidth || 1280;
        const height = ui.remoteStream.naturalHeight || 720;

        // Only resize canvas if dimensions actually changed (resizing clears the canvas!)
        if (ui.canvas.width !== width || ui.canvas.height !== height) {
          ui.canvas.width = width;
          ui.canvas.height = height;
          console.log(`[Remote] Canvas resized to ${width}x${height} (onload #${onloadCount})`);
        }

        // Only start loop on first load to avoid multiple timers
        if (onloadCount === 1) {
          console.log("[Remote] Starting recognition loop from onload (first time)");
          startRecognitionLoop();
          startSnapshotUpdates(); // Start snapshot display updates
        }
      };

      // Handle image errors - reload stream if it fails
      ui.remoteStream.onerror = function() {
        console.warn("[Remote] Stream image error, attempting to reconnect...");
        setTimeout(() => {
          if (state.remoteSource) {
            ui.remoteStream.src = `/api/stream?source=${encodeURIComponent(source)}&t=${Date.now()}`;
          }
        }, 1000); // Wait 1 second before reconnecting
      };

      // Watchdog: Check if image is still updating (MJPEG should trigger onload frequently)
      const streamWatchdog = setInterval(() => {
        if (!state.remoteSource) {
          clearInterval(streamWatchdog);
          return;
        }

        const timeSinceUpdate = Date.now() - lastImageUpdate;
        if (timeSinceUpdate > 5000) { // No update for 5 seconds
          console.warn("[Remote] Stream appears frozen, reconnecting...");
          ui.remoteStream.src = `/api/stream?source=${encodeURIComponent(source)}&t=${Date.now()}`;
          lastImageUpdate = Date.now();
        }
      }, 3000); // Check every 3 seconds

      // Update status after short delay
      setTimeout(() => {
        console.log("[Remote] setTimeout callback executing!");
        updateStatus("Streaming (Remote)", "success");
        ui.loadingOverlay.classList.add("d-none");
        console.log("[Remote] MJPEG stream started for:", source);

        // Start recognition loop for RTSP (processes frames in background)
        console.log("[Remote] Starting recognition loop from setTimeout");
        console.log("[Remote] Current state:", {
          remoteSource: state.remoteSource,
          recognitionTimer: state.recognitionTimer,
          frameInterval: state.frameInterval
        });
        startRecognitionLoop();
        startSnapshotUpdates(); // Start snapshot display updates
        console.log("[Remote] Recognition loop started, timer ID:", state.recognitionTimer);

        // Update UI buttons and source display
        if (ui.startCameraBtn) ui.startCameraBtn.classList.add("d-none");
        if (ui.stopCameraBtn) ui.stopCameraBtn.classList.remove("d-none");
        if (ui.sourceDisplay) {
          const sourceType = source.startsWith('rtsp://') ? 'RTSP' :
                            source.startsWith('http://') ? 'HTTP' : 'Remote';
          ui.sourceDisplay.textContent = sourceType;
        }
      }, 1000);
    } else {
      showAlert(`✗ ${data.message}`, "error");
      if (statusDiv) {
        statusDiv.innerHTML = `
          <div class="alert alert-danger small">
            ✗ ${data.message}
          </div>
        `;
      }
    }
  } catch (error) {
    console.error("[changeVideoSource] Error:", error);
    showAlert(`Error changing source: ${error.message}`, "error");
    if (statusDiv) {
      statusDiv.innerHTML = `
        <div class="alert alert-danger small">
          ✗ Error: ${error.message}
        </div>
      `;
    }
  }
};

// ----------------------------------------------------------------------------- //
// Event bindings
// ----------------------------------------------------------------------------- //
document
  .getElementById("startCameraBtn")
  .addEventListener("click", toggleCamera);
document
  .getElementById("registerForm")
  .addEventListener("submit", registerFace);
// Clear Data with confirmation modal
document
  .getElementById("clearDataBtn")
  .addEventListener("click", () => {
    const clearModal = new bootstrap.Modal(document.getElementById("clearDataModal"));
    clearModal.show();
  });

// Confirm clear button in modal
const confirmClearBtn = document.getElementById("confirmClearBtn");
if (confirmClearBtn) {
  confirmClearBtn.addEventListener("click", () => {
    const clearModal = bootstrap.Modal.getInstance(document.getElementById("clearDataModal"));
    clearModal.hide();
    clearDatabase();
  });
}

// Refresh Faces button (only on faces.html page)
const refreshFacesBtn = document.getElementById("refreshFacesBtn");
if (refreshFacesBtn) {
  refreshFacesBtn.addEventListener("click", fetchFaces);
}

// Clear Events button
const clearEventsBtn = document.getElementById("clearEventsBtn");
if (clearEventsBtn) {
  clearEventsBtn.addEventListener("click", () => {
    state.events = [];
    ui.eventsList.innerHTML = `
      <li class="timeline-empty">
        <i class="fas fa-info-circle"></i>
        <span>No events yet. Start the camera to begin monitoring.</span>
      </li>
    `;
    showAlert("Timeline cleared", "success");
  });
}

// Stop Camera button
const stopCameraBtn = document.getElementById("stopCameraBtn");
if (stopCameraBtn) {
  stopCameraBtn.addEventListener("click", () => {
    if (state.stream) {
      state.stream.getTracks().forEach(track => track.stop());
      state.stream = null;
    }
    if (state.recognitionTimer) {
      clearInterval(state.recognitionTimer);
      state.recognitionTimer = null;
    }
    ui.video.srcObject = null;
    ui.remoteStream.classList.add("d-none");

    // Update UI
    if (ui.startCameraBtn) ui.startCameraBtn.classList.remove("d-none");
    if (ui.stopCameraBtn) ui.stopCameraBtn.classList.add("d-none");

    updateStatus("Camera Stopped", "info");
    showAlert("Camera stopped", "success");
  });
}

// Apply & Connect button
const applyBtn = document.getElementById("applyCameraSourceBtn");
if (applyBtn) {
  console.log("[Init] Apply & Connect button found, attaching listener");
  applyBtn.addEventListener("click", changeVideoSource);
} else {
  console.error("[Init] Apply & Connect button NOT FOUND!");
}

document
  .getElementById("validateSourceBtn")
  .addEventListener("click", () => {
    const source = ui.cameraSourceInput.value.trim();
    if (source) {
      validateSource(source);
    } else {
      showAlert("Please enter a source to validate", "error");
    }
  });

// Example buttons
document.querySelectorAll(".example-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const source = btn.getAttribute("data-source");
    ui.cameraSourceInput.value = source;
  });
});

// ----------------------------------------------------------------------------- //
// Auto-reconnect to active stream
// ----------------------------------------------------------------------------- //
const autoReconnectToStream = async () => {
  try {
    console.log("[Auto-Reconnect] Checking for active background stream...");

    // Check if backend has an active stream
    const response = await fetch("/api/background/status");
    const data = await response.json();

    if (data.success && data.stream_active && data.current_source) {
      console.log("[Auto-Reconnect] Found active stream:", data.current_source);
      console.log("[Auto-Reconnect] Background processing:", data.background_running ? "ON" : "OFF");

      // Set the source in state
      state.remoteSource = data.current_source;

      // Update UI to show we're reconnecting
      updateStatus("Reconnecting...", "info");

      // Show remote stream
      ui.video.style.display = 'none';
      ui.canvas.style.display = 'block';
      ui.remoteStream.src = `/api/stream?source=${encodeURIComponent(data.current_source)}&t=${Date.now()}`;
      ui.remoteStream.classList.remove('d-none');
      ui.remoteStream.style.display = 'block';

      // Setup canvas when image loads
      let onloadCount = 0;
      ui.remoteStream.onload = function() {
        onloadCount++;
        const width = ui.remoteStream.naturalWidth || 1280;
        const height = ui.remoteStream.naturalHeight || 720;

        if (ui.canvas.width !== width || ui.canvas.height !== height) {
          ui.canvas.width = width;
          ui.canvas.height = height;
          console.log(`[Auto-Reconnect] Canvas set to ${width}x${height}`);
        }

        if (onloadCount === 1) {
          startRecognitionLoop();
          startSnapshotUpdates(); // Start snapshot display updates
          console.log("[Auto-Reconnect] Recognition loop and snapshot updates started");
        }
      };

      // Update UI
      setTimeout(() => {
        updateStatus("Streaming (Reconnected)", "success");
        ui.loadingOverlay.classList.add("d-none");
        if (ui.startCameraBtn) ui.startCameraBtn.classList.add("d-none");
        if (ui.stopCameraBtn) ui.stopCameraBtn.classList.remove("d-none");
        if (ui.sourceDisplay) {
          const sourceType = data.current_source.startsWith('rtsp://') ? 'RTSP' :
                            data.current_source.startsWith('http://') ? 'HTTP' : 'Remote';
          ui.sourceDisplay.textContent = sourceType;
        }

        showAlert("✓ Reconnected to active stream", "success");
      }, 1000);

    } else {
      console.log("[Auto-Reconnect] No active stream found");
    }
  } catch (error) {
    console.error("[Auto-Reconnect] Error:", error);
  }
};

// ----------------------------------------------------------------------------- //
// Boot
// ----------------------------------------------------------------------------- //
fetchEvents(true);
fetchFaces();
getCurrentSource();

// Auto-reconnect to active stream after a short delay
setTimeout(() => {
  autoReconnectToStream();
}, 500);

// Cleanup on page unload (but DON'T stop the stream - let it run in background)
window.addEventListener("beforeunload", () => {
  // Only stop local resources, not the backend stream
  if (state.stream) {
    state.stream.getTracks().forEach(track => track.stop());
  }
  stopRecognitionLoop(); // Stop frontend polling only
  console.log("[Cleanup] Frontend stopped, backend continues...");
});

// ----------------------------------------------------------------------------- //
// Persons Management Tab
// ----------------------------------------------------------------------------- //

let allPersons = [];
let registeredFaces = [];
let personsLoadInterval = null;

// Load persons when tab is activated
document.addEventListener('DOMContentLoaded', () => {
  const personsTab = document.getElementById('persons-tab');
  if (personsTab) {
    personsTab.addEventListener('shown.bs.tab', () => {
      loadPersonsData();
      // Auto-refresh every 30 seconds when tab is active
      if (!personsLoadInterval) {
        personsLoadInterval = setInterval(() => {
          const activeTab = document.querySelector('#persons-tab.active');
          if (activeTab) {
            loadPersonsData();
          }
        }, 30000);
      }
    });

    personsTab.addEventListener('hidden.bs.tab', () => {
      // Stop auto-refresh when tab is hidden
      if (personsLoadInterval) {
        clearInterval(personsLoadInterval);
        personsLoadInterval = null;
      }
    });
  }

  // Setup search
  const searchBox = document.getElementById('personSearchBox');
  if (searchBox) {
    searchBox.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase();
      filterAndDisplayPersons(query);
    });
  }

  // Check if we need to auto-open registration modal
  const urlParams = new URLSearchParams(window.location.search);
  const shouldRegister = urlParams.get('register') === 'true';
  const storedPersonId = sessionStorage.getItem('registerPersonId');
  const storedPersonName = sessionStorage.getItem('registerPersonName');

  if (shouldRegister && storedPersonId && storedPersonName) {
    // Wait a bit for page to fully load
    setTimeout(() => {
      const modal = new bootstrap.Modal(document.getElementById('registerModal'));
      modal.show();

      // Pre-fill the form
      const personIdField = document.getElementById('personId');
      const personNameField = document.getElementById('personName');

      if (personIdField) {
        personIdField.value = storedPersonId;
        personIdField.readOnly = true;
      }

      if (personNameField) {
        personNameField.value = storedPersonName;
        personNameField.readOnly = true;
      }

      // Clear sessionStorage
      sessionStorage.removeItem('registerPersonId');
      sessionStorage.removeItem('registerPersonName');

      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }, 500);
  }
});

// Load persons from API
async function loadPersonsData() {
  const content = document.getElementById('personsListContent');
  if (!content) return;

  try {
    // Load persons from attendance system
    const personsResponse = await fetch('/api/persons');
    const personsData = await personsResponse.json();

    if (!personsData.success) {
      throw new Error(personsData.error || 'Failed to load persons');
    }

    allPersons = personsData.persons || [];

    // Load registered faces
    const facesResponse = await fetch('/api/faces');
    const facesData = await facesResponse.json();
    registeredFaces = facesData.faces || [];

    // Update stats
    updatePersonsStats();

    // Display persons
    filterAndDisplayPersons();

  } catch (error) {
    console.error('[Persons] Error loading data:', error);
    content.innerHTML = `
      <div class="persons-empty-state">
        <i class="fas fa-exclamation-triangle"></i>
        <p class="mb-0">Error loading persons</p>
        <small>${error.message}</small>
      </div>
    `;
  }
}

// Update statistics
function updatePersonsStats() {
  const total = allPersons.length;
  const withFaces = allPersons.filter(p => hasFaceRegistered(p)).length;

  const totalEl = document.getElementById('totalPersons');
  const withFacesEl = document.getElementById('withFaces');

  if (totalEl) totalEl.textContent = total;
  if (withFacesEl) withFacesEl.textContent = withFaces;
}

// Check if person has registered face
function hasFaceRegistered(person) {
  return registeredFaces.some(face =>
    face.name === person.name || face.person_id === person.person_id
  );
}

// Filter and display persons
function filterAndDisplayPersons(searchQuery = '') {
  let filtered = allPersons;

  // Apply search
  if (searchQuery) {
    filtered = filtered.filter(p =>
      p.name.toLowerCase().includes(searchQuery) ||
      p.person_id.toLowerCase().includes(searchQuery) ||
      (p.department && p.department.toLowerCase().includes(searchQuery)) ||
      (p.email && p.email.toLowerCase().includes(searchQuery))
    );
  }

  displayPersons(filtered);
}

// Display persons list
function displayPersons(persons) {
  const content = document.getElementById('personsListContent');
  if (!content) return;

  if (persons.length === 0) {
    content.innerHTML = `
      <div class="persons-empty-state">
        <i class="fas fa-user-slash"></i>
        <p class="mb-0">No persons found</p>
        <small>Persons synced from Odoo will appear here</small>
      </div>
    `;
    return;
  }

  content.innerHTML = persons.map(person => createPersonItemHTML(person)).join('');
}

// Create person item HTML
function createPersonItemHTML(person) {
  const hasRegisteredFace = hasFaceRegistered(person);
  const statusClass = hasRegisteredFace ? 'registered' : 'pending';
  const statusText = hasRegisteredFace ? '✓ Face Registered' : '⏳ Pending';

  return `
    <div class="person-item">
      <div class="person-item-header">
        <h6 class="person-name">${escapeHtml(person.name)}</h6>
        <span class="person-id-badge">${escapeHtml(person.person_id)}</span>
      </div>
      <div class="person-info">
        ${person.email ? `<div><i class="fas fa-envelope"></i>${escapeHtml(person.email)}</div>` : ''}
        ${person.department ? `<div><i class="fas fa-building"></i>${escapeHtml(person.department)}</div>` : ''}
        ${person.position ? `<div><i class="fas fa-briefcase"></i>${escapeHtml(person.position)}</div>` : ''}
      </div>
      <div class="person-face-status">
        <span class="face-status-badge ${statusClass}">${statusText}</span>
        ${!hasRegisteredFace ? `
          <button class="btn-register-face" onclick="goToRegisterFace('${escapeHtml(person.person_id)}', '${escapeHtml(person.name)}')">
            <i class="fas fa-camera"></i> Register
          </button>
        ` : ''}
      </div>
    </div>
  `;
}

// Navigate to face registration
function goToRegisterFace(personId, personName) {
  // Redirect to main page and open registration modal
  // Store person info in sessionStorage
  sessionStorage.setItem('registerPersonId', personId);
  sessionStorage.setItem('registerPersonName', personName);

  // If already on index.html, just open the modal
  if (window.location.pathname.includes('index.html') || window.location.pathname === '/') {
    // Open the register modal
    const modal = new bootstrap.Modal(document.getElementById('registerModal'));
    modal.show();

    // Pre-fill the form
    document.getElementById('personId').value = personId;
    document.getElementById('personName').value = personName;
    document.getElementById('personId').readOnly = true;
    document.getElementById('personName').readOnly = true;
  } else {
    // Redirect to index.html with flag to open modal
    window.location.href = `index.html?register=true`;
  }
}

// Refresh persons list
function refreshPersonsList() {
  loadPersonsData();
}

// HTML escape utility
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
