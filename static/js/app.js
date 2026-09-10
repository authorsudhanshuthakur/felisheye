/**
 * FelisEye - Global Application Core
 */

window.FelisEye = {
  activeTab: 'scan',
  theme: 'dark',
  settings: {},
  
  init() {
    this.initTheme();
    this.initNavigation();
    this.fetchSettings();
  },

  initTheme() {
    const savedTheme = localStorage.getItem('feliseye_theme') || 'dark';
    this.setTheme(savedTheme);
  },

  setTheme(theme) {
    this.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('feliseye_theme', theme);
    const themeIcon = document.getElementById('theme-toggle-icon');
    if (themeIcon) {
      themeIcon.innerHTML = theme === 'dark' 
        ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>'
        : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
    }
  },

  toggleTheme() {
    this.setTheme(this.theme === 'dark' ? 'light' : 'dark');
  },

  initNavigation() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const target = tab.getAttribute('data-view');
        this.switchView(target);
      });
    });
  },

  switchView(viewName) {
    this.activeTab = viewName;
    
    // Update nav buttons
    document.querySelectorAll('.nav-tab').forEach(t => {
      t.classList.toggle('active', t.getAttribute('data-view') === viewName);
    });
    
    // Update view panels
    document.querySelectorAll('.view-panel').forEach(p => {
      p.classList.toggle('active', p.id === `view-${viewName}`);
    });

    // View specific hooks
    if (viewName === 'people') {
      window.FelisEyePeople && window.FelisEyePeople.loadPeople();
    } else if (viewName === 'history') {
      window.FelisEyeHistory && window.FelisEyeHistory.loadHistory();
    } else if (viewName === 'settings') {
      window.FelisEyeSettings && window.FelisEyeSettings.loadSettings();
    }
  },

  async fetchSettings() {
    try {
      const res = await fetch('/api/settings');
      if (res.ok) {
        this.settings = await res.json();
      }
    } catch (e) {
      console.warn("Failed to fetch settings:", e);
    }
  },

  toast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  },

  /**
   * Premium Progress Line & Percentage Subsystem
   */
  progress: {
    activeTrackers: {},

    ensureGlobalBar() {
      let bar = document.getElementById('felis-global-progress-bar');
      if (!bar) {
        bar = document.createElement('div');
        bar.id = 'felis-global-progress-bar';
        document.body.prepend(bar);
      }
      return bar;
    },

    setGlobal(percent) {
      const bar = this.ensureGlobalBar();
      if (percent > 0 && percent < 100) {
        bar.classList.add('active');
        bar.style.width = `${Math.min(99, Math.max(5, percent))}%`;
      } else if (percent >= 100) {
        bar.classList.add('active');
        bar.style.width = '100%';
        setTimeout(() => {
          bar.classList.remove('active');
          setTimeout(() => { bar.style.width = '0%'; }, 400);
        }, 350);
      } else {
        bar.classList.remove('active');
        bar.style.width = '0%';
      }
    },

    createInlineTracker(containerEl, initialLabel = 'Processing...') {
      if (!containerEl) return null;
      containerEl.innerHTML = `
        <div class="neu-progress-container">
          <div class="neu-progress-meta">
            <span class="neu-progress-label">
              <span class="neu-progress-spinner"></span>
              <span class="neu-progress-text">${initialLabel}</span>
            </span>
            <span class="neu-progress-percent">0%</span>
          </div>
          <div class="neu-progress-track">
            <div class="neu-progress-fill" style="width: 0%;"></div>
          </div>
        </div>
      `;
      return {
        container: containerEl.querySelector('.neu-progress-container'),
        labelEl: containerEl.querySelector('.neu-progress-text'),
        percentEl: containerEl.querySelector('.neu-progress-percent'),
        fillEl: containerEl.querySelector('.neu-progress-fill'),
        spinnerEl: containerEl.querySelector('.neu-progress-spinner')
      };
    },

    start(trackerId, { containerEl = null, stages = [], onFinish = null } = {}) {
      this.stop(trackerId);

      const inline = containerEl ? this.createInlineTracker(containerEl, stages[0]?.label || 'Starting...') : null;
      this.setGlobal(10);

      const tracker = {
        inline,
        stages: stages.length > 0 ? stages : [
          { percent: 20, label: "Initializing operation...", delay: 200 },
          { percent: 50, label: "Processing data...", delay: 400 },
          { percent: 85, label: "Finalizing...", delay: 600 }
        ],
        currentStageIdx: 0,
        currentPercent: 0,
        targetPercent: 0,
        timer: null,
        animFrame: null,
        onFinish
      };

      this.activeTrackers[trackerId] = tracker;

      // Smooth percentage interpolator
      const interpolate = () => {
        if (!this.activeTrackers[trackerId]) return;
        const diff = tracker.targetPercent - tracker.currentPercent;
        if (Math.abs(diff) > 0.5) {
          tracker.currentPercent += diff * 0.15;
          this.applyPercent(tracker, Math.round(tracker.currentPercent));
          tracker.animFrame = requestAnimationFrame(interpolate);
        } else {
          tracker.currentPercent = tracker.targetPercent;
          this.applyPercent(tracker, tracker.currentPercent);
        }
      };

      const advanceStages = () => {
        if (!this.activeTrackers[trackerId]) return;
        if (tracker.currentStageIdx < tracker.stages.length) {
          const st = tracker.stages[tracker.currentStageIdx];
          tracker.targetPercent = st.percent;
          if (tracker.inline && tracker.inline.labelEl) {
            tracker.inline.labelEl.textContent = st.label;
          }
          if (!tracker.animFrame) {
            tracker.animFrame = requestAnimationFrame(interpolate);
          }
          tracker.currentStageIdx++;
          tracker.timer = setTimeout(advanceStages, st.delay || 500);
        }
      };

      advanceStages();
      return tracker;
    },

    applyPercent(tracker, percent) {
      this.setGlobal(percent);
      if (tracker.inline) {
        if (tracker.inline.percentEl) tracker.inline.percentEl.textContent = `${percent}%`;
        if (tracker.inline.fillEl) tracker.inline.fillEl.style.width = `${percent}%`;
      }
    },

    update(trackerId, percent, label) {
      const tracker = this.activeTrackers[trackerId];
      if (!tracker) return;
      clearTimeout(tracker.timer);
      tracker.targetPercent = percent;
      if (label && tracker.inline && tracker.inline.labelEl) {
        tracker.inline.labelEl.textContent = label;
      }
      this.applyPercent(tracker, percent);
    },

    complete(trackerId, successLabel = 'Completed successfully (100%)', removeAfterMs = 1200) {
      const tracker = this.activeTrackers[trackerId];
      if (!tracker) {
        this.setGlobal(100);
        return;
      }
      clearTimeout(tracker.timer);
      cancelAnimationFrame(tracker.animFrame);
      tracker.currentPercent = 100;
      tracker.targetPercent = 100;

      this.setGlobal(100);
      if (tracker.inline) {
        if (tracker.inline.percentEl) tracker.inline.percentEl.textContent = '100%';
        if (tracker.inline.fillEl) {
          tracker.inline.fillEl.style.width = '100%';
          tracker.inline.fillEl.classList.add('success');
        }
        if (tracker.inline.labelEl) tracker.inline.labelEl.textContent = successLabel;
        if (tracker.inline.spinnerEl) tracker.inline.spinnerEl.style.display = 'none';

        if (removeAfterMs > 0 && tracker.inline.container) {
          setTimeout(() => {
            if (tracker.inline.container) {
              tracker.inline.container.style.opacity = '0';
              tracker.inline.container.style.transition = 'opacity 0.4s ease';
              setTimeout(() => {
                tracker.inline.container.remove();
              }, 400);
            }
          }, removeAfterMs);
        }
      }

      if (tracker.onFinish) tracker.onFinish();
      delete this.activeTrackers[trackerId];
    },

    fail(trackerId, errorLabel = 'Operation failed', removeAfterMs = 2500) {
      const tracker = this.activeTrackers[trackerId];
      if (!tracker) {
        this.setGlobal(0);
        return;
      }
      clearTimeout(tracker.timer);
      cancelAnimationFrame(tracker.animFrame);

      if (tracker.inline) {
        if (tracker.inline.fillEl) tracker.inline.fillEl.classList.add('error');
        if (tracker.inline.labelEl) tracker.inline.labelEl.textContent = errorLabel;
        if (tracker.inline.spinnerEl) tracker.inline.spinnerEl.style.display = 'none';
        if (removeAfterMs > 0 && tracker.inline.container) {
          setTimeout(() => {
            if (tracker.inline.container) tracker.inline.container.remove();
          }, removeAfterMs);
        }
      }

      this.setGlobal(0);
      delete this.activeTrackers[trackerId];
    },

    stop(trackerId) {
      const tracker = this.activeTrackers[trackerId];
      if (tracker) {
        clearTimeout(tracker.timer);
        cancelAnimationFrame(tracker.animFrame);
        if (tracker.inline && tracker.inline.container) {
          tracker.inline.container.remove();
        }
        delete this.activeTrackers[trackerId];
      }
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  window.FelisEye.init();
});
