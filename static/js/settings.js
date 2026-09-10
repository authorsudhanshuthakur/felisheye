/**
 * FelisEye - System Settings & Backup/Restore Controller
 */

window.FelisEyeSettings = {
  init() {
    this.initForm();
    this.initBackupRestore();
  },

  initForm() {
    const form = document.getElementById('settings-form');
    if (!form) return;

    // Link slider outputs
    const sliders = [
      'threshold_high_confidence',
      'threshold_possible_match',
      'threshold_low_confidence',
      'threshold_duplicate_warn',
      'liveness_min_score'
    ];

    sliders.forEach(key => {
      const input = document.getElementById(`set-${key}`);
      const label = document.getElementById(`val-${key}`);
      if (input && label) {
        input.addEventListener('input', () => {
          label.textContent = input.value;
        });
      }
    });

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      this.saveSettings();
    });
  },

  async loadSettings() {
    try {
      const res = await fetch('/api/settings');
      if (res.ok) {
        const s = await res.json();
        
        // Populate sliders & switches
        const map = {
          'threshold_high_confidence': 'set-threshold_high_confidence',
          'threshold_possible_match': 'set-threshold_possible_match',
          'threshold_low_confidence': 'set-threshold_low_confidence',
          'threshold_duplicate_warn': 'set-threshold_duplicate_warn',
          'liveness_min_score': 'set-liveness_min_score'
        };

        for (const [key, id] of Object.entries(map)) {
          const el = document.getElementById(id);
          const valEl = document.getElementById(`val-${key}`);
          if (el && s[key] !== undefined) {
            el.value = s[key];
            if (valEl) valEl.textContent = s[key];
          }
        }

        const liveToggle = document.getElementById('set-liveness_enabled');
        if (liveToggle) liveToggle.checked = !!s.liveness_enabled;

        const encToggle = document.getElementById('set-encrypt_embeddings');
        if (encToggle) encToggle.checked = !!s.encrypt_embeddings;
      }

      this.loadStats();
    } catch (e) {
      console.error("Failed to load settings:", e);
    }
  },

  async loadStats() {
    try {
      const res = await fetch('/api/settings/stats');
      if (res.ok) {
        const stats = await res.json();
        document.getElementById('stat-people').textContent = stats.people_count;
        document.getElementById('stat-embeddings').textContent = stats.embeddings_count;
        document.getElementById('stat-history').textContent = stats.history_count;
        document.getElementById('stat-storage').textContent = `${stats.photo_storage_mb} MB (DB: ${stats.db_size_kb} KB)`;
      }
    } catch (e) {
      console.error("Failed to load stats:", e);
    }
  },

  async saveSettings() {
    const payload = {
      threshold_high_confidence: parseFloat(document.getElementById('set-threshold_high_confidence').value),
      threshold_possible_match: parseFloat(document.getElementById('set-threshold_possible_match').value),
      threshold_low_confidence: parseFloat(document.getElementById('set-threshold_low_confidence').value),
      threshold_duplicate_warn: parseFloat(document.getElementById('set-threshold_duplicate_warn').value),
      liveness_min_score: parseFloat(document.getElementById('set-liveness_min_score').value),
      liveness_enabled: document.getElementById('set-liveness_enabled').checked,
      encrypt_embeddings: document.getElementById('set-encrypt_embeddings').checked
    };

    try {
      const res = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        window.FelisEye.toast("Settings updated successfully", "success");
        window.FelisEye.fetchSettings();
      }
    } catch (e) {
      window.FelisEye.toast(`Save error: ${e.message}`, "error");
    }
  },

  initBackupRestore() {
    const backupBtn = document.getElementById('btn-download-backup');
    const restoreInput = document.getElementById('restore-file-input');

    if (backupBtn) {
      backupBtn.addEventListener('click', () => {
        window.location.href = '/api/settings/backup';
      });
    }

    if (restoreInput) {
      restoreInput.addEventListener('change', async () => {
        if (!restoreInput.files || restoreInput.files.length === 0) return;
        if (!confirm("Restoring will replace or merge database and photo assets. Proceed?")) return;

        const formData = new FormData();
        formData.append('file', restoreInput.files[0]);

        const progressSlot = document.getElementById('restore-progress-slot');
        window.FelisEye.progress.start('restore_backup', {
          containerEl: progressSlot,
          stages: [
            { percent: 25, label: "Uploading ZIP archive (25%)...", delay: 200 },
            { percent: 55, label: "Decompressing archive & verifying SQLite integrity (55%)...", delay: 500 },
            { percent: 85, label: "Restoring encrypted embeddings & photo repository (85%)...", delay: 800 }
          ]
        });

        try {
          const res = await fetch('/api/settings/restore', {
            method: 'POST',
            body: formData
          });

          if (res.ok) {
            window.FelisEye.progress.complete('restore_backup', "Backup restored and database re-indexed: 100% done", 1500);
            window.FelisEye.toast("Backup restored successfully!", "success");
            this.loadStats();
          } else {
            const err = await res.json();
            throw new Error(err.detail || "Restore failed");
          }
        } catch (e) {
          window.FelisEye.progress.fail('restore_backup', `Restore error: ${e.message}`, 3000);
          window.FelisEye.toast(`Restore error: ${e.message}`, "error");
        } finally {
          restoreInput.value = '';
        }
      });
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  window.FelisEyeSettings.init();
});
