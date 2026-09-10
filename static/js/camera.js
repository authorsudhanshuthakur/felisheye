/**
 * FelisEye - Real-time Camera & Live HUD Overlay Module
 */

window.FelisEyeCamera = {
  video: null,
  overlayCanvas: null,
  overlayCtx: null,
  stream: null,
  isRunning: false,
  isScanning: false,
  scanInterval: null,
  lastBoxes: [],
  lastResult: null,

  init() {
    this.video = document.getElementById('camera-video');
    this.overlayCanvas = document.getElementById('overlay-canvas');
    if (this.overlayCanvas) {
      this.overlayCtx = this.overlayCanvas.getContext('2d');
    }

    const startBtn = document.getElementById('btn-start-camera');
    const stopBtn = document.getElementById('btn-stop-camera');
    const snapBtn = document.getElementById('btn-snap-camera');

    if (startBtn) startBtn.addEventListener('click', () => this.start());
    if (stopBtn) stopBtn.addEventListener('click', () => this.stop());
    if (snapBtn) snapBtn.addEventListener('click', () => this.snapshotAndLog());

    // Continuous overlay rendering loop for smooth animations
    requestAnimationFrame(() => this.renderHUDLoop());
  },

  async start() {
    if (this.isRunning) return;
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" }
      });
      this.video.srcObject = this.stream;
      await this.video.play();
      this.isRunning = true;
      
      document.getElementById('btn-start-camera').style.display = 'none';
      document.getElementById('btn-stop-camera').style.display = 'inline-flex';
      document.getElementById('camera-placeholder').style.display = 'none';
      document.getElementById('camera-video').style.display = 'block';

      this.updateHudStatus("LIVE ACTIVE", true);
      this.startRecognitionLoop();
      window.FelisEye.toast("Camera started successfully", "success");
    } catch (e) {
      console.error("Camera access error:", e);
      window.FelisEye.toast(`Camera error: ${e.message}`, "error");
    }
  },

  stop() {
    if (this.scanInterval) {
      clearInterval(this.scanInterval);
      this.scanInterval = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
    }
    this.isRunning = false;
    this.lastBoxes = [];
    
    document.getElementById('btn-start-camera').style.display = 'inline-flex';
    document.getElementById('btn-stop-camera').style.display = 'none';
    document.getElementById('camera-placeholder').style.display = 'flex';
    document.getElementById('camera-video').style.display = 'none';
    
    this.updateHudStatus("STANDBY", false);
    if (this.overlayCtx && this.overlayCanvas) {
      this.overlayCtx.clearRect(0, 0, this.overlayCanvas.width, this.overlayCanvas.height);
    }
  },

  updateHudStatus(text, active) {
    const el = document.getElementById('camera-status-text');
    const dot = document.getElementById('camera-status-dot');
    if (el) el.textContent = text;
    if (dot) dot.className = `hud-dot ${active ? 'pulsing' : ''}`;
  },

  startRecognitionLoop() {
    // Throttled frame processing (every 400ms = 2.5 FPS analysis, optimal CPU balance)
    this.scanInterval = setInterval(() => {
      if (!this.isRunning || this.isScanning) return;
      this.processCurrentFrame(false);
    }, 450);
  },

  async processCurrentFrame(logEvent = false) {
    if (!this.isRunning || this.video.videoWidth === 0) return;
    this.isScanning = true;

    try {
      // Capture frame to temporary offscreen canvas
      const canvas = document.createElement('canvas');
      canvas.width = this.video.videoWidth;
      canvas.height = this.video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(this.video, 0, 0, canvas.width, canvas.height);
      
      const b64 = canvas.toDataURL('image/jpeg', 0.85);

      const res = await fetch('/api/scan/frame', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_base64: b64,
          log_event: logEvent,
          source: "Live Camera"
        })
      });

      if (res.ok) {
        const data = await res.json();
        this.lastBoxes = data.results || [];
        if (data.results && data.results.length > 0) {
          this.lastResult = data.results[0];
          window.FelisEyeScan && window.FelisEyeScan.displayRecognitionResult(data.results[0], b64);
        } else {
          window.FelisEyeScan && window.FelisEyeScan.displayNoFace();
        }
      }
    } catch (e) {
      console.warn("Scan frame error:", e);
    } finally {
      this.isScanning = false;
    }
  },

  snapshotAndLog() {
    if (!this.isRunning) {
      window.FelisEye.toast("Start camera first", "warning");
      return;
    }
    this.processCurrentFrame(true);
    window.FelisEye.toast("Snapshot captured and logged to history", "success");
  },

  renderHUDLoop() {
    if (this.overlayCanvas && this.video && this.isRunning) {
      if (this.overlayCanvas.width !== this.video.clientWidth || this.overlayCanvas.height !== this.video.clientHeight) {
        this.overlayCanvas.width = this.video.clientWidth;
        this.overlayCanvas.height = this.video.clientHeight;
      }

      const ctx = this.overlayCtx;
      ctx.clearRect(0, 0, this.overlayCanvas.width, this.overlayCanvas.height);

      const cw = this.overlayCanvas.width;
      const ch = this.overlayCanvas.height;

      // Draw bounding boxes
      for (const item of this.lastBoxes) {
        const norm = item.bbox;
        const x = norm.norm_left * cw;
        const y = norm.norm_top * ch;
        const w = (norm.norm_right - norm.norm_left) * cw;
        const h = (norm.norm_bottom - norm.norm_top) * ch;

        const tier = item.match ? item.match.tier : "UNKNOWN";
        let color = '#ef4444'; // Red for unknown
        if (tier === 'HIGH_CONFIDENCE') color = '#10b981'; // Green
        else if (tier === 'POSSIBLE_MATCH') color = '#f59e0b'; // Amber
        else if (tier === 'LOW_CONFIDENCE') color = '#f97316'; // Orange

        // Neumorphic rounded corner box
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        ctx.shadowColor = color;
        ctx.shadowBlur = 10;

        // Draw corner brackets
        const cornerLen = Math.min(w, h) * 0.25;
        ctx.beginPath();
        // Top-left
        ctx.moveTo(x, y + cornerLen);
        ctx.lineTo(x, y);
        ctx.lineTo(x + cornerLen, y);
        // Top-right
        ctx.moveTo(x + w - cornerLen, y);
        ctx.lineTo(x + w, y);
        ctx.lineTo(x + w, y + cornerLen);
        // Bottom-right
        ctx.moveTo(x + w, y + h - cornerLen);
        ctx.lineTo(x + w, y + h);
        ctx.lineTo(x + w - cornerLen, y + h);
        // Bottom-left
        ctx.moveTo(x + cornerLen, y + h);
        ctx.lineTo(x, y + h);
        ctx.lineTo(x, y + h - cornerLen);
        ctx.stroke();

        ctx.shadowBlur = 0; // reset

        // Label banner
        const name = (item.match && item.match.person) ? item.match.person.full_name : "UNKNOWN PERSON";
        const sim = (item.match && item.match.similarity) ? `${item.match.similarity}%` : "";
        const labelText = `${name} ${sim ? `(${sim})` : ''}`;

        ctx.font = 'bold 13px Inter, sans-serif';
        const textWidth = ctx.measureText(labelText).width;
        
        ctx.fillStyle = 'rgba(10, 23, 38, 0.85)';
        ctx.beginPath();
        ctx.roundRect(x, Math.max(0, y - 28), textWidth + 20, 24, 6);
        ctx.fill();

        ctx.fillStyle = color;
        ctx.fillText(labelText, x + 10, Math.max(0, y - 28) + 16);
      }
    }

    requestAnimationFrame(() => this.renderHUDLoop());
  }
};

document.addEventListener('DOMContentLoaded', () => {
  window.FelisEyeCamera.init();
});
