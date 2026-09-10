/**
 * FelisEye - People Directory & Multi-Photo Enrollment Subsystem
 */

window.FelisEyePeople = {
  people: [],
  enrollFiles: [],
  customFieldCount: 0,
  currentProfileId: null,
  currentEditPersonId: null,
  currentEditData: null,
  editNewPhotos: [],
  selectedPrimaryPhotoPath: null,

  init() {
    this.initControls();
    this.initEnrollmentModal();
    this.initEditModal();
  },

  initControls() {
    const searchInput = document.getElementById('people-search');
    const genderSelect = document.getElementById('people-gender-filter');
    const enrollBtn = document.getElementById('btn-open-enroll');

    if (searchInput) {
      let timeout = null;
      searchInput.addEventListener('input', () => {
        clearTimeout(timeout);
        timeout = setTimeout(() => this.loadPeople(), 300);
      });
    }

    if (genderSelect) {
      genderSelect.addEventListener('change', () => this.loadPeople());
    }

    if (enrollBtn) {
      enrollBtn.addEventListener('click', () => this.openEnrollModal());
    }
  },

  async loadPeople() {
    const search = document.getElementById('people-search')?.value || '';
    const gender = document.getElementById('people-gender-filter')?.value || '';

    const progressSlot = document.getElementById('people-progress-slot');
    if (progressSlot) {
      window.FelisEye.progress.start('load_people', {
        containerEl: progressSlot,
        initialLabel: "Searching profiles..."
      });
    }

    try {
      if (progressSlot) window.FelisEye.progress.update('load_people', 30, "Querying database...");
      const url = new URL('/api/people', window.location.origin);
      if (search) url.searchParams.set('search', search);
      if (gender) url.searchParams.set('gender', gender);
      url.searchParams.set('limit', '100');

      const res = await fetch(url);
      if (progressSlot) window.FelisEye.progress.update('load_people', 70, "Processing results...");
      
      if (res.ok) {
        const data = await res.json();
        this.people = data.people || [];
        this.renderPeopleGrid();
        if (progressSlot) window.FelisEye.progress.complete('load_people', "Search complete: 100% done", 1000);
      } else {
        if (progressSlot) window.FelisEye.progress.fail('load_people', `Search error: Server returned ${res.status}`, 3000);
      }
    } catch (e) {
      console.error("Failed to load people:", e);
      window.FelisEye.toast("Failed to load people directory", "error");
      if (progressSlot) window.FelisEye.progress.fail('load_people', `Search error: ${e.message}`, 3000);
    }
  },

  renderPeopleGrid() {
    const grid = document.getElementById('people-grid');
    const countEl = document.getElementById('people-total-count');
    if (!grid) return;

    if (countEl) countEl.textContent = `${this.people.length} Profiles`;

    if (this.people.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1/-1; text-align:center; padding: 48px 20px;" class="neu-raised">
          <p style="color:var(--text-secondary); margin-bottom: 12px;">No people registered yet.</p>
          <button class="neu-btn neu-btn-primary" onclick="window.FelisEyePeople.openEnrollModal()">+ Enroll First Person</button>
        </div>
      `;
      return;
    }

    grid.innerHTML = this.people.map(p => `
      <div class="person-card neu-raised" onclick="window.FelisEyePeople.openProfileModal('${p.id}')">
        <div class="person-card-header">
          <img src="${p.profile_photo_path ? `/data/${p.profile_photo_path}` : 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="%23888" stroke-width="2"><circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 1 0-16 0"/></svg>'}" 
               class="person-avatar" style="width:64px;height:64px;" />
          <div style="flex:1; overflow:hidden;">
            <h4 style="font-size:1.1rem; font-weight:700; white-space:nowrap; text-overflow:ellipsis; overflow:hidden;">${p.full_name}</h4>
            <span class="person-id" style="font-size:0.75rem;">${p.id}</span>
            <div style="font-size:0.8rem; color:var(--text-secondary); margin-top:2px;">
              ${p.gender ? `${p.gender} • ` : ''}${p.dob_or_age || 'Age: N/A'}
            </div>
          </div>
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.8rem; color:var(--text-muted); border-top:1px solid var(--border-subtle); padding-top:8px;">
          <span>📸 ${p.photos_count || 1} Biometric Sample(s)</span>
          <div style="display:flex; gap:8px; align-items:center;">
            <button type="button" class="neu-btn card-action-btn" onclick="event.stopPropagation(); window.FelisEyePeople.openEditModal('${p.id}')">✏️ Edit</button>
            <span style="color:var(--accent-primary); font-weight:600;">View Profile →</span>
          </div>
        </div>
      </div>
    `).join('');
  },

  async openProfileModal(personId) {
    this.currentProfileId = personId;
    try {
      const res = await fetch(`/api/people/${personId}`);
      if (!res.ok) throw new Error("Profile not found");
      const p = await res.json();

      document.getElementById('modal-prof-name').textContent = p.full_name;
      document.getElementById('modal-prof-id').textContent = p.id;
      document.getElementById('modal-prof-avatar').src = p.profile_photo_path ? `/data/${p.profile_photo_path}` : '';
      document.getElementById('modal-prof-age').textContent = p.dob_or_age || 'Not specified';
      document.getElementById('modal-prof-gender').textContent = p.gender || 'Not specified';
      document.getElementById('modal-prof-notes').textContent = p.notes || 'No notes provided.';
      document.getElementById('modal-prof-created').textContent = new Date(p.created_at).toLocaleString();

      // Render custom fields
      const customContainer = document.getElementById('modal-prof-custom-fields');
      const customEntries = Object.entries(p.custom_fields || {});
      if (customEntries.length > 0) {
        customContainer.innerHTML = customEntries.map(([k, v]) => `
          <div class="metric-box neu-inset-sm">
            <div class="metric-label">${k}</div>
            <div style="font-weight:600; font-size:0.95rem;">${v}</div>
          </div>
        `).join('');
        document.getElementById('modal-prof-custom-section').style.display = 'block';
      } else {
        document.getElementById('modal-prof-custom-section').style.display = 'none';
      }

      document.getElementById('profile-detail-modal').classList.add('open');
    } catch (e) {
      window.FelisEye.toast(`Error: ${e.message}`, "error");
    }
  },

  closeProfileModal() {
    document.getElementById('profile-detail-modal').classList.remove('open');
    this.currentProfileId = null;
  },

  switchToEditModal() {
    const id = this.currentProfileId;
    if (!id) return;
    this.closeProfileModal();
    this.openEditModal(id);
  },

  async confirmDeletePerson() {
    if (!this.currentProfileId) return;
    if (!confirm("Are you sure you want to permanently delete this person and all associated facial biometric data?")) return;

    try {
      const res = await fetch(`/api/people/${this.currentProfileId}`, { method: 'DELETE' });
      if (res.ok) {
        window.FelisEye.toast("Profile and biometrics deleted", "success");
        this.closeProfileModal();
        this.loadPeople();
      }
    } catch (e) {
      window.FelisEye.toast(`Delete error: ${e.message}`, "error");
    }
  },

  // ----------------- ENROLLMENT WIZARD ----------------- //

  initEnrollmentModal() {
    const fileInput = document.getElementById('enroll-photos-input');
    const addCustomBtn = document.getElementById('btn-add-custom-field');
    const form = document.getElementById('enroll-form');

    if (fileInput) {
      fileInput.addEventListener('change', (e) => this.handleEnrollPhotosSelect(e.target.files));
    }

    if (addCustomBtn) {
      addCustomBtn.addEventListener('click', () => this.addCustomFieldRow());
    }

    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        this.submitEnrollment(false);
      });
    }
  },

  openEnrollModal(initialPhotoB64 = null) {
    this.enrollFiles = [];
    document.getElementById('enroll-form').reset();
    document.getElementById('enroll-photos-preview').innerHTML = '';
    document.getElementById('enroll-custom-fields-container').innerHTML = '';
    document.getElementById('duplicate-warning-banner').style.display = 'none';

    if (initialPhotoB64) {
      // Convert base64 to File object
      fetch(initialPhotoB64)
        .then(res => res.blob())
        .then(blob => {
          const file = new File([blob], "scan_snapshot.jpg", { type: "image/jpeg" });
          this.handleEnrollPhotosSelect([file]);
        });
    }

    document.getElementById('enroll-modal').classList.add('open');
  },

  closeEnrollModal() {
    document.getElementById('enroll-modal').classList.remove('open');
  },

  addCustomFieldRow(key = '', val = '') {
    this.customFieldCount++;
    const container = document.getElementById('enroll-custom-fields-container');
    const row = document.createElement('div');
    row.className = 'custom-field-row';
    row.style = 'display:flex; gap:8px; margin-bottom:8px;';
    row.innerHTML = `
      <input type="text" placeholder="Field Name (e.g. Role, Dept)" class="neu-input field-key" value="${key}" style="flex:1;" required />
      <input type="text" placeholder="Value (e.g. Engineer)" class="neu-input field-val" value="${val}" style="flex:1;" required />
      <button type="button" class="neu-btn neu-btn-danger" style="padding:6px 12px;" onclick="this.parentElement.remove()">✕</button>
    `;
    container.appendChild(row);
  },

  async handleEnrollPhotosSelect(files) {
    if (!files || files.length === 0) return;

    for (const file of Array.from(files)) {
      // Pre-validate photo with backend
      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch('/api/people/validate-photo', {
          method: 'POST',
          body: formData
        });

        const data = await res.json();
        
        if (!data.valid) {
          window.FelisEye.toast(`Photo rejected: ${data.message}`, "error");
          continue;
        }

        // Check if duplicate warning
        if (data.duplicate_warning) {
          const banner = document.getElementById('duplicate-warning-banner');
          banner.style.display = 'block';
          banner.innerHTML = `
            <strong>⚠ Potential Duplicate Detected:</strong> This face is very similar (${data.duplicate_warning.similarity}%) to existing profile 
            <strong>${data.duplicate_warning.full_name}</strong> (${data.duplicate_warning.person_id}).
          `;
        }

        this.enrollFiles.push(file);
        this.renderEnrollPhotosPreview();
      } catch (e) {
        console.error(e);
        window.FelisEye.toast("Validation error on photo", "error");
      }
    }
  },

  renderEnrollPhotosPreview() {
    const container = document.getElementById('enroll-photos-preview');
    container.innerHTML = this.enrollFiles.map((f, idx) => `
      <div style="position:relative; width:64px; height:64px;">
        <img src="${URL.createObjectURL(f)}" style="width:100%; height:100%; object-fit:cover; border-radius:8px; border:1px solid var(--accent-primary);" />
        <span onclick="window.FelisEyePeople.removeEnrollPhoto(${idx})" style="position:absolute; top:-6px; right:-6px; background:var(--danger); color:#fff; border-radius:50%; width:18px; height:18px; font-size:10px; display:flex; align-items:center; justify-content:center; cursor:pointer;">✕</span>
      </div>
    `).join('');
  },

  removeEnrollPhoto(idx) {
    this.enrollFiles.splice(idx, 1);
    this.renderEnrollPhotosPreview();
  },

  async submitEnrollment(forceDuplicate = false) {
    const name = document.getElementById('enroll-name').value;
    const dob = document.getElementById('enroll-dob').value;
    const gender = document.getElementById('enroll-gender').value;
    const notes = document.getElementById('enroll-notes').value;

    if (!name.trim()) {
      window.FelisEye.toast("Please enter a full name", "warning");
      return;
    }

    if (this.enrollFiles.length === 0) {
      window.FelisEye.toast("Please add at least one valid face photo", "warning");
      return;
    }

    // Collect custom fields
    const customFields = {};
    document.querySelectorAll('#enroll-custom-fields-container .custom-field-row').forEach(row => {
      const k = row.querySelector('.field-key')?.value.trim();
      const v = row.querySelector('.field-val')?.value.trim();
      if (k && v) customFields[k] = v;
    });

    const formData = new FormData();
    formData.append('full_name', name.trim());
    if (dob) formData.append('dob_or_age', dob);
    if (gender) formData.append('gender', gender);
    if (notes) formData.append('notes', notes);
    formData.append('custom_fields', JSON.stringify(customFields));
    formData.append('force_duplicate', forceDuplicate ? 'true' : 'false');

    for (const file of this.enrollFiles) {
      formData.append('photos', file);
    }

    const submitBtn = document.getElementById('btn-submit-enroll');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Enrolling...";
    }

    const progressSlot = document.getElementById('enroll-progress-slot');
    window.FelisEye.progress.start('enroll_person', {
      containerEl: progressSlot,
      stages: [
        { percent: 20, label: "Uploading biometric photo assets...", delay: 200 },
        { percent: 45, label: "Extracting landmarks & validating sharpness...", delay: 450 },
        { percent: 70, label: "Synthesizing facial vector centroid...", delay: 650 },
        { percent: 90, label: "Executing duplicate check against database...", delay: 800 }
      ]
    });

    try {
      const res = await fetch('/api/people', {
        method: 'POST',
        body: formData
      });

      if (res.status === 409) {
        window.FelisEye.progress.stop('enroll_person');
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "Enroll Biometric Profile";
        }
        const errData = await res.json();
        if (confirm(`${errData.detail.message}\n\nDo you still want to proceed with duplicate enrollment?`)) {
          return this.submitEnrollment(true);
        }
        return;
      }

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Enrollment failed");
      }

      const result = await res.json();
      window.FelisEye.progress.complete(
        'enroll_person',
        `Successfully registered ${result.full_name} (100% completed)`,
        1000
      );

      setTimeout(() => {
        this.closeEnrollModal();
        this.loadPeople();
        window.FelisEye.toast(`Successfully enrolled ${result.full_name} (${result.person_id})`, "success");
      }, 700);

    } catch (e) {
      console.error(e);
      window.FelisEye.progress.fail('enroll_person', `Enrollment error: ${e.message}`, 3000);
      window.FelisEye.toast(`Enrollment error: ${e.message}`, "error");
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Enroll Biometric Profile";
      }
    }
  },

  // ----------------- EDIT PERSON MODAL ----------------- //

  initEditModal() {
    const editForm = document.getElementById('edit-person-form');
    const addCustomBtn = document.getElementById('btn-add-edit-custom-field');
    const photoInput = document.getElementById('edit-photos-input');

    if (editForm) {
      editForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.savePersonEdit();
      });
    }

    if (addCustomBtn) {
      addCustomBtn.addEventListener('click', () => this.addEditCustomFieldRow());
    }

    if (photoInput) {
      photoInput.addEventListener('change', (e) => this.handleEditPhotosSelect(e.target.files));
    }

    // Quick preset suggestion buttons
    document.querySelectorAll('#edit-person-modal .preset-pill').forEach(btn => {
      btn.addEventListener('click', () => {
        const fieldName = btn.getAttribute('data-field');
        if (fieldName) {
          this.addEditCustomFieldRow(fieldName, '');
        }
      });
    });

    // Close on backdrop click
    const modal = document.getElementById('edit-person-modal');
    if (modal) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) this.closeEditModal();
      });
    }
  },

  async openEditModal(personId) {
    this.currentEditPersonId = personId;
    this.editNewPhotos = [];
    
    try {
      const res = await fetch(`/api/people/${personId}`);
      if (!res.ok) throw new Error("Could not load person profile.");
      const p = await res.json();
      this.currentEditData = p;

      document.getElementById('edit-person-id').value = p.id;
      document.getElementById('edit-person-id-badge').textContent = `#${p.id}`;
      document.getElementById('edit-name').value = p.full_name || '';
      document.getElementById('edit-dob').value = p.dob_or_age || '';
      document.getElementById('edit-gender').value = p.gender || '';
      document.getElementById('edit-notes').value = p.notes || '';
      
      this.selectedPrimaryPhotoPath = p.profile_photo_path || null;
      this.renderEditExistingPhotos();
      this.renderEditNewPhotosPreview();

      // Populate custom fields
      const container = document.getElementById('edit-custom-fields-container');
      container.innerHTML = '';
      const customEntries = Object.entries(p.custom_fields || {});
      if (customEntries.length > 0) {
        customEntries.forEach(([k, v]) => this.addEditCustomFieldRow(k, v));
      }

      document.getElementById('edit-person-modal').classList.add('open');
    } catch (e) {
      window.FelisEye.toast(`Error opening edit profile: ${e.message}`, "error");
    }
  },

  closeEditModal() {
    document.getElementById('edit-person-modal').classList.remove('open');
    this.currentEditPersonId = null;
    this.currentEditData = null;
    this.editNewPhotos = [];
    this.selectedPrimaryPhotoPath = null;
    const photoInput = document.getElementById('edit-photos-input');
    if (photoInput) photoInput.value = '';
  },

  renderEditExistingPhotos() {
    const container = document.getElementById('edit-photos-list');
    if (!container || !this.currentEditData) return;

    const photos = this.currentEditData.photos || [];
    if (photos.length === 0) {
      if (this.currentEditData.profile_photo_path) {
        container.innerHTML = `
          <div class="photo-thumb-item is-primary neu-inset-sm" title="Primary Profile Photo">
            <img src="/data/${this.currentEditData.profile_photo_path}" />
            <div class="photo-primary-badge">Primary</div>
          </div>
        `;
      } else {
        container.innerHTML = '<span style="font-size:0.8rem; color:var(--text-muted);">No photos enrolled.</span>';
      }
      return;
    }

    container.innerHTML = photos.map(ph => {
      const isPrimary = ph.photo_path === this.selectedPrimaryPhotoPath;
      const canDelete = photos.length > 1;
      return `
        <div class="photo-thumb-item neu-inset-sm ${isPrimary ? 'is-primary' : ''}" 
             title="${isPrimary ? 'Primary Photo (Active)' : 'Click to set as Primary Photo'}"
             onclick="window.FelisEyePeople.selectPrimaryPhoto('${ph.photo_path}')">
          <img src="/data/${ph.photo_path}" />
          ${isPrimary ? '<div class="photo-primary-badge">Primary</div>' : ''}
          ${canDelete ? `
            <span class="photo-delete-btn" 
                  title="Remove this photo sample" 
                  onclick="event.stopPropagation(); window.FelisEyePeople.confirmDeletePhoto('${this.currentEditPersonId}', ${ph.embedding_id})">✕</span>
          ` : ''}
        </div>
      `;
    }).join('');
  },

  selectPrimaryPhoto(path) {
    this.selectedPrimaryPhotoPath = path;
    this.renderEditExistingPhotos();
  },

  async confirmDeletePhoto(personId, embeddingId) {
    if (!confirm("Are you sure you want to remove this biometric photo sample from the profile?")) return;
    try {
      const res = await fetch(`/api/people/${personId}/photos/${embeddingId}`, { method: 'DELETE' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to remove photo");

      window.FelisEye.toast(data.message || "Photo removed", "success");
      this.currentEditData = data.person;
      this.selectedPrimaryPhotoPath = data.person.profile_photo_path;
      this.renderEditExistingPhotos();
      this.loadPeople();
    } catch (e) {
      window.FelisEye.toast(e.message, "error");
    }
  },

  addEditCustomFieldRow(key = '', val = '') {
    const container = document.getElementById('edit-custom-fields-container');
    const row = document.createElement('div');
    row.className = 'custom-field-row';
    row.style = 'display:flex; gap:8px; margin-bottom:8px;';
    row.innerHTML = `
      <input type="text" placeholder="Field Name (e.g. Role, Clearance, Phone)" class="neu-input field-key" value="${String(key).replace(/"/g, '&quot;')}" style="flex:1;" required />
      <input type="text" placeholder="Value (e.g. Lead Researcher, +1 555-0199)" class="neu-input field-val" value="${String(val).replace(/"/g, '&quot;')}" style="flex:1;" required />
      <button type="button" class="neu-btn neu-btn-danger" style="padding:6px 12px;" onclick="this.parentElement.remove()">✕</button>
    `;
    container.appendChild(row);

    const valInput = row.querySelector('.field-val');
    if (!val && valInput) valInput.focus();
  },

  async handleEditPhotosSelect(files) {
    if (!files || files.length === 0) return;

    for (const file of Array.from(files)) {
      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch('/api/people/validate-photo', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (!data.valid) {
          window.FelisEye.toast(`Photo rejected: ${data.message}`, "error");
          continue;
        }
        this.editNewPhotos.push(file);
        this.renderEditNewPhotosPreview();
      } catch (e) {
        console.error(e);
        window.FelisEye.toast("Validation error on photo", "error");
      }
    }
  },

  renderEditNewPhotosPreview() {
    const container = document.getElementById('edit-new-photos-preview');
    if (!container) return;

    if (this.editNewPhotos.length === 0) {
      container.innerHTML = '';
      return;
    }

    container.innerHTML = `
      <div style="font-size:0.8rem; color:var(--accent-primary); width:100%; margin-bottom:4px; font-weight:600;">
        + ${this.editNewPhotos.length} New Photo(s) ready to add upon saving:
      </div>
      <div style="display:flex; gap:8px; flex-wrap:wrap;">
        ${this.editNewPhotos.map((f, idx) => `
          <div style="position:relative; width:64px; height:64px;">
            <img src="${URL.createObjectURL(f)}" style="width:100%; height:100%; object-fit:cover; border-radius:8px; border:2px solid var(--accent-primary);" />
            <span onclick="window.FelisEyePeople.removeEditNewPhoto(${idx})" 
                  style="position:absolute; top:-6px; right:-6px; background:var(--danger); color:#fff; border-radius:50%; width:18px; height:18px; font-size:10px; display:flex; align-items:center; justify-content:center; cursor:pointer;">✕</span>
          </div>
        `).join('')}
      </div>
    `;
  },

  removeEditNewPhoto(idx) {
    this.editNewPhotos.splice(idx, 1);
    this.renderEditNewPhotosPreview();
  },

  async savePersonEdit() {
    const personId = this.currentEditPersonId;
    if (!personId) return;

    const name = document.getElementById('edit-name').value.trim();
    const dob = document.getElementById('edit-dob').value.trim();
    const gender = document.getElementById('edit-gender').value;
    const notes = document.getElementById('edit-notes').value.trim();
    const saveBtn = document.getElementById('btn-save-person-edit');

    if (!name) {
      window.FelisEye.toast("Full name is required", "warning");
      return;
    }

    // Collect custom fields
    const customFields = {};
    document.querySelectorAll('#edit-custom-fields-container .custom-field-row').forEach(row => {
      const k = row.querySelector('.field-key')?.value.trim();
      const v = row.querySelector('.field-val')?.value.trim();
      if (k) customFields[k] = v || '';
    });

    const payload = {
      full_name: name,
      dob_or_age: dob,
      gender: gender,
      notes: notes,
      custom_fields: customFields,
      profile_photo_path: this.selectedPrimaryPhotoPath
    };

    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.textContent = "Saving...";
    }

    const progressSlot = document.getElementById('edit-progress-slot');
    window.FelisEye.progress.start('edit_person', {
      containerEl: progressSlot,
      stages: [
        { percent: 25, label: "Persisting updated profile metadata (25%)...", delay: 200 },
        { percent: 60, label: this.editNewPhotos.length > 0 ? "Uploading new photos & extracting embeddings (60%)..." : "Synchronizing profile state (60%)...", delay: 400 },
        { percent: 88, label: "Recalculating biometric centroid & saving (88%)...", delay: 600 }
      ]
    });

    try {
      // 1. Update text fields and primary photo
      const res = await fetch(`/api/people/${personId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to update profile");
      }

      // 2. Upload any new photos if attached
      if (this.editNewPhotos.length > 0) {
        window.FelisEye.progress.update('edit_person', 75, "Processing newly uploaded photos & recalculating facial centroid...");
        const photoFormData = new FormData();
        for (const f of this.editNewPhotos) {
          photoFormData.append('photos', f);
        }
        const photoRes = await fetch(`/api/people/${personId}/photos`, {
          method: 'POST',
          body: photoFormData
        });
        if (!photoRes.ok) {
          const photoErr = await photoRes.json();
          throw new Error(photoErr.detail || "Failed to upload new photos");
        }
      }

      window.FelisEye.progress.complete('edit_person', "Profile updated and biometrics synced: 100% done", 900);
      
      setTimeout(() => {
        this.closeEditModal();
        this.loadPeople();
        window.FelisEye.toast("Profile updated successfully", "success");

        // If profile detail modal was active, update it
        if (document.getElementById('profile-detail-modal')?.classList.contains('open')) {
          this.openProfileModal(personId);
        }
      }, 650);

    } catch (e) {
      console.error(e);
      window.FelisEye.progress.fail('edit_person', `Save error: ${e.message}`, 3000);
      window.FelisEye.toast(`Save error: ${e.message}`, "error");
    } finally {
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.textContent = "Save Changes";
      }
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  window.FelisEyePeople.init();
});
