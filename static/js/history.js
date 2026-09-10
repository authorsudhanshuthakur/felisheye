/**
 * FelisEye - Recognition Event History Controller
 */

window.FelisEyeHistory = {
  events: [],

  init() {
    const filterSelect = document.getElementById('history-status-filter');
    const clearBtn = document.getElementById('btn-clear-history');
    const exportCsvBtn = document.getElementById('btn-export-csv');
    const exportJsonBtn = document.getElementById('btn-export-json');

    if (filterSelect) {
      filterSelect.addEventListener('change', () => this.loadHistory());
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', () => this.clearHistory());
    }

    if (exportCsvBtn) {
      exportCsvBtn.addEventListener('click', () => this.exportHistory('csv'));
    }

    if (exportJsonBtn) {
      exportJsonBtn.addEventListener('click', () => this.exportHistory('json'));
    }
  },

  async loadHistory() {
    const filter = document.getElementById('history-status-filter')?.value || '';
    
    const progressSlot = document.getElementById('history-progress-slot');
    if (progressSlot) {
      window.FelisEye.progress.start('load_history', {
        containerEl: progressSlot,
        initialLabel: "Searching recognition events..."
      });
    }

    try {
      if (progressSlot) window.FelisEye.progress.update('load_history', 30, "Querying database...");
      const url = new URL('/api/history', window.location.origin);
      if (filter) url.searchParams.set('status', filter);
      url.searchParams.set('limit', '100');

      const res = await fetch(url);
      if (progressSlot) window.FelisEye.progress.update('load_history', 70, "Processing results...");
      
      if (res.ok) {
        const data = await res.json();
        this.events = data.events || [];
        this.renderHistoryTable();
        if (progressSlot) window.FelisEye.progress.complete('load_history', "Search complete: 100% done", 1000);
      } else {
        if (progressSlot) window.FelisEye.progress.fail('load_history', `Search error: Server returned ${res.status}`, 3000);
      }
    } catch (e) {
      console.error("Failed to load history:", e);
      window.FelisEye.toast("Failed to load recognition history", "error");
      if (progressSlot) window.FelisEye.progress.fail('load_history', `Search error: ${e.message}`, 3000);
    }
  },

  renderHistoryTable() {
    const tbody = document.getElementById('history-tbody');
    const countEl = document.getElementById('history-total-count');
    if (!tbody) return;

    if (countEl) countEl.textContent = `${this.events.length} Events`;

    if (this.events.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align:center; padding:32px; color:var(--text-muted);">
            No recognition events recorded yet.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = this.events.map(ev => {
      let badgeClass = 'badge-unknown';
      let badgeLabel = 'Unknown';
      if (ev.result_status === 'HIGH_CONFIDENCE') { badgeClass = 'badge-high'; badgeLabel = 'High Confidence'; }
      else if (ev.result_status === 'POSSIBLE_MATCH') { badgeClass = 'badge-possible'; badgeLabel = 'Possible Match'; }
      else if (ev.result_status === 'LOW_CONFIDENCE') { badgeClass = 'badge-low'; badgeLabel = 'Low Confidence'; }

      return `
        <tr>
          <td style="font-family:var(--font-mono); font-size:0.85rem;">${ev.timestamp}</td>
          <td><span class="result-badge ${badgeClass}" style="font-size:0.75rem; padding:3px 8px;">${badgeLabel}</span></td>
          <td>
            <strong>${ev.matched_person_name || 'Unknown Person'}</strong>
            ${ev.matched_person_id ? `<div style="font-size:0.75rem; color:var(--text-secondary); font-family:var(--font-mono);">${ev.matched_person_id}</div>` : ''}
          </td>
          <td style="font-family:var(--font-mono); font-weight:700;">${ev.similarity_score ? `${ev.similarity_score}%` : '—'}</td>
          <td style="font-family:var(--font-mono); font-size:0.85rem; color:var(--text-secondary);">${ev.distance !== null ? ev.distance : '—'}</td>
          <td><span class="neu-inset-sm" style="padding:4px 8px; font-size:0.8rem;">${ev.source}</span></td>
        </tr>
      `;
    }).join('');
  },

  async clearHistory() {
    if (!confirm("Are you sure you want to clear all recognition history logs?")) return;
    
    const progressSlot = document.getElementById('history-progress-slot');
    if (progressSlot) {
      window.FelisEye.progress.start('clear_history', {
        containerEl: progressSlot,
        initialLabel: "Clearing recognition history..."
      });
    }

    try {
      if (progressSlot) window.FelisEye.progress.update('clear_history', 50, "Removing records from database...");
      const res = await fetch('/api/history', { method: 'DELETE' });
      if (res.ok) {
        if (progressSlot) window.FelisEye.progress.complete('clear_history', "History cleared: 100% done", 1000);
        window.FelisEye.toast("History cleared successfully", "success");
        this.loadHistory();
      } else {
        if (progressSlot) window.FelisEye.progress.fail('clear_history', `Clear error: Server returned ${res.status}`, 3000);
      }
    } catch (e) {
      if (progressSlot) window.FelisEye.progress.fail('clear_history', `Clear error: ${e.message}`, 3000);
      window.FelisEye.toast(`Clear error: ${e.message}`, "error");
    }
  },

  exportHistory(format) {
    window.location.href = `/api/history/export?format=${format}`;
  }
};

document.addEventListener('DOMContentLoaded', () => {
  window.FelisEyeHistory.init();
});
