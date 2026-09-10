/**
 * FelisEye - Scan & Recognition UI Controller
 */

window.FelisEyeScan = {
  currentMode: 'camera', // 'camera' or 'photo'
  lastDetectedFaces: [],
  selectedFaceIndex: 0,
  capturedSnapshotB64: null,

  init() {
    this.initModeSwitch();
    this.initPhotoUpload();
  },

  initModeSwitch() {
    const camBtn = document.getElementById('tab-mode-camera');
    const photoBtn = document.getElementById('tab-mode-photo');

    if (camBtn && photoBtn) {
      camBtn.addEventListener('click', () => this.setMode('camera'));
      photoBtn.addEventListener('click', () => this.setMode('photo'));
    }
  },

  setMode(mode) {
    this.currentMode = mode;
    document.getElementById('tab-mode-camera').classList.toggle('active', mode === 'camera');
    document.getElementById('tab-mode-photo').classList.toggle('active', mode === 'photo');

    document.getElementById('camera-scan-section').style.display = mode === 'camera' ? 'block' : 'none';
    document.getElementById('photo-scan-section').style.display = mode === 'photo' ? 'block' : 'none';

    if (mode === 'photo' && window.FelisEyeCamera.isRunning) {
      window.FelisEyeCamera.stop();
    }
  },

  initPhotoUpload() {
    const dropzone = document.getElementById('photo-dropzone');
    const fileInput = document.getElementById('photo-file-input');

    if (!dropzone || !fileInput) return;

    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
      dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        this.processPhotoUpload(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files && fileInput.files.length > 0) {
        this.processPhotoUpload(fileInput.files[0]);
      }
    });
  },

  async processPhotoUpload(file) {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('log_event', 'true');

    // Show preview in dropzone
    const reader = new FileReader();
    reader.onload = (e) => {
      this.capturedSnapshotB64 = e.target.result;
      document.getElementById('photo-preview-img').src = e.target.result;
      document.getElementById('photo-preview-container').style.display = 'block';
      document.getElementById('dropzone-instructions').style.display = 'none';
    };
    reader.readAsDataURL(file);

    // Initialize premium multi-stage progress line
    const progressSlot = document.getElementById('photo-progress-slot');
    window.FelisEye.progress.start('photo_scan', {
      containerEl: progressSlot,
      stages: [
        { percent: 25, label: "Uploading photograph & checking image format...", delay: 200 },
        { percent: 50, label: "Running neural face detector & alignment...", delay: 450 },
        { percent: 78, label: "Extracting 128D deep facial biometric embeddings...", delay: 600 },
        { percent: 92, label: "Searching database & evaluating cosine similarity...", delay: 750 }
      ]
    });

    try {
      const res = await fetch('/api/scan/photo', {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Photo analysis failed");
      }

      const data = await res.json();
      this.lastDetectedFaces = data.results || [];
      this.renderPhotoFacesGallery(data.results);

      const count = data.results ? data.results.length : 0;
      window.FelisEye.progress.complete(
        'photo_scan', 
        count > 0 ? `Recognition complete: 100% done (${count} face${count > 1 ? 's' : ''} matched)` : 'Scan complete: 100% done (No faces detected)', 
        1800
      );

      if (count > 0) {
        this.selectPhotoFace(0);
        window.FelisEye.toast(`Detected ${count} face(s)`, "success");
      } else {
        this.displayNoFace("No faces found in the photo.");
      }
    } catch (e) {
      console.error(e);
      window.FelisEye.progress.fail('photo_scan', `Scan error: ${e.message}`, 3000);
      window.FelisEye.toast(`Error: ${e.message}`, "error");
    }
  },

  renderPhotoFacesGallery(results) {
    const container = document.getElementById('photo-faces-gallery');
    if (!container) return;

    if (!results || results.length <= 1) {
      container.style.display = 'none';
      return;
    }

    container.style.display = 'flex';
    container.innerHTML = results.map((item, idx) => `
      <div class="face-thumb-chip neu-btn ${idx === 0 ? 'active' : ''}" onclick="window.FelisEyeScan.selectPhotoFace(${idx})">
        <img src="${item.thumbnail || ''}" style="width:28px;height:28px;border-radius:6px;object-fit:cover;"/>
        <span>Face #${idx + 1}</span>
      </div>
    `).join('');
  },

  selectPhotoFace(idx) {
    this.selectedFaceIndex = idx;
    document.querySelectorAll('.face-thumb-chip').forEach((el, i) => {
      el.classList.toggle('active', i === idx);
    });
    if (this.lastDetectedFaces[idx]) {
      this.displayRecognitionResult(this.lastDetectedFaces[idx], this.capturedSnapshotB64);
    }
  },

  displayRecognitionResult(result, snapshotUrl) {
    const card = document.getElementById('scan-result-card');
    if (!card) return;

    card.style.display = 'flex';
    const match = result.match;
    const isMatched = match && match.matched;
    const person = match ? match.person : null;

    // Classification Badge
    const tier = match ? match.tier : "UNKNOWN";
    const badgeEl = document.getElementById('res-tier-badge');
    badgeEl.className = 'result-badge';
    
    if (tier === 'HIGH_CONFIDENCE') {
      badgeEl.classList.add('badge-high');
      badgeEl.textContent = 'High Confidence Match';
    } else if (tier === 'POSSIBLE_MATCH') {
      badgeEl.classList.add('badge-possible');
      badgeEl.textContent = 'Possible Match';
    } else if (tier === 'LOW_CONFIDENCE') {
      badgeEl.classList.add('badge-low');
      badgeEl.textContent = 'Low Confidence';
    } else {
      badgeEl.classList.add('badge-unknown');
      badgeEl.textContent = 'Unknown Person';
    }

    // Person Avatar & Details
    const avatarEl = document.getElementById('res-avatar');
    const nameEl = document.getElementById('res-name');
    const idEl = document.getElementById('res-id');
    const enrollBtn = document.getElementById('btn-enroll-unknown');
    const profileBtn = document.getElementById('btn-view-matched-profile');

    if (person && isMatched) {
      nameEl.textContent = person.full_name;
      idEl.textContent = `ID: ${person.id}`;
      avatarEl.src = person.profile_photo_path ? `/data/${person.profile_photo_path}` : (result.thumbnail || snapshotUrl || '');
      enrollBtn.style.display = 'none';
      profileBtn.style.display = 'inline-flex';
      profileBtn.onclick = () => window.FelisEyePeople.openProfileModal(person.id);
    } else {
      nameEl.textContent = "Unknown Person";
      idEl.textContent = "No database record match";
      avatarEl.src = result.thumbnail || snapshotUrl || 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="%23888" stroke-width="2"><circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 1 0-16 0"/></svg>';
      enrollBtn.style.display = 'inline-flex';
      profileBtn.style.display = 'none';
      enrollBtn.onclick = () => this.quickEnrollPrompt(snapshotUrl);
    }

    // Metrics Row
    const simEl = document.getElementById('res-metric-sim');
    const distEl = document.getElementById('res-metric-dist');
    const liveEl = document.getElementById('res-metric-live');

    simEl.textContent = match ? `${match.similarity}%` : '0%';
    distEl.textContent = match ? match.distance : 'N/A';
    
    const liveness = result.liveness;
    liveEl.textContent = liveness ? (liveness.is_live ? 'Verified Live' : 'Suspicious') : 'N/A';
    liveEl.style.color = liveness && liveness.is_live ? 'var(--success)' : 'var(--warning)';
    
    // Quality feedback tags
    const qual = result.quality;
    const warnContainer = document.getElementById('res-quality-warnings');
    if (qual && qual.warnings && qual.warnings.length > 0) {
      warnContainer.innerHTML = qual.warnings.map(w => `<span class="quality-chip neu-inset-sm">⚠ ${w}</span>`).join('');
      warnContainer.style.display = 'flex';
    } else {
      warnContainer.innerHTML = '';
      warnContainer.style.display = 'none';
    }
  },

  displayNoFace(message = "Searching for visible faces in frame...") {
    const nameEl = document.getElementById('res-name');
    const idEl = document.getElementById('res-id');
    const badgeEl = document.getElementById('res-tier-badge');
    const enrollBtn = document.getElementById('btn-enroll-unknown');
    const profileBtn = document.getElementById('btn-view-matched-profile');

    if (nameEl) nameEl.textContent = "No Face Detected";
    if (idEl) idEl.textContent = message;
    if (badgeEl) {
      badgeEl.className = 'result-badge badge-unknown';
      badgeEl.textContent = 'Standby';
    }
    if (enrollBtn) enrollBtn.style.display = 'none';
    if (profileBtn) profileBtn.style.display = 'none';
  },

  quickEnrollPrompt(snapshotUrl) {
    window.FelisEye.switchView('people');
    window.FelisEyePeople.openEnrollModal(snapshotUrl);
  }
};

document.addEventListener('DOMContentLoaded', () => {
  window.FelisEyeScan.init();
});
