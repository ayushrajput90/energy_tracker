/**
 * Smart Data-Driven Insights Feed
 */
let allInsightsList = [];

async function loadSmartInsights() {
  try {
    const data = await API.get('/analytics/insights');
    allInsightsList = data.insights || [];
    renderInsights(allInsightsList);
  } catch (err) {
    console.error('Failed to load insights:', err);
    UI.showToast('Could not load smart insights.', 'error');
  }
}

function renderInsights(insights) {
  const container = document.getElementById('insights-feed-container');
  if (!container) return;

  if (!insights.length) {
    container.innerHTML = `
      <div style="text-align: center; padding: 3rem; background: var(--bg-surface); border-radius: var(--radius-lg); border: 1px dashed var(--border-strong);">
        <p class="text-muted">No insights available yet. Record more renewable energy data to generate automated performance recommendations.</p>
      </div>
    `;
    return;
  }

  const icons = {
    sun: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line></svg>',
    'trending-up': '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>',
    'trending-down': '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"></polyline><polyline points="17 18 23 18 23 12"></polyline></svg>',
    award: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="2"><circle cx="12" cy="8" r="7"></circle><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>',
    'check-circle': '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
    zap: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>',
    leaf: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"></path><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"></path></svg>',
    'dollar-sign': '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>',
    target: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>'
  };

  container.innerHTML = insights.map(ins => `
    <div class="insight-card" style="padding: 1.5rem;">
      <div class="insight-icon-box" style="width: 50px; height: 50px;">
        ${icons[ins.icon] || icons.zap}
      </div>
      <div style="flex: 1;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.5rem;">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span class="badge badge-neutral">${ins.category}</span>
            <h3 class="insight-title" style="margin: 0; font-size: 1.125rem;">${ins.title}</h3>
          </div>
          <span class="badge badge-success">${ins.badge || 'Insight'}</span>
        </div>
        <p class="insight-message" style="font-size: 0.9375rem;">${ins.message}</p>
      </div>
    </div>
  `).join('');
}

function filterInsightsCategory(category) {
  if (!category || category === 'All') {
    renderInsights(allInsightsList);
  } else {
    const filtered = allInsightsList.filter(i => i.category === category);
    renderInsights(filtered);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('insights-feed-container')) {
    loadSmartInsights();
    document.getElementById('insights-filter-category')?.addEventListener('change', (e) => {
      filterInsightsCategory(e.target.value);
    });
  }
});
