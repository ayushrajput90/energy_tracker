/**
 * Renewable Source Performance & Detailed Comparison
 */
let sourceComparisonChart = null;

async function loadSourceComparison() {
  const sourceFilter = document.getElementById('sources-source-filter')?.value || '';
  const timeFilter = document.getElementById('sources-time-filter')?.value || 'this_year';
  const startDate = document.getElementById('sources-start-date')?.value || '';
  const endDate = document.getElementById('sources-end-date')?.value || '';

  const params = {
    source: sourceFilter,
    time_filter: timeFilter
  };
  if (timeFilter === 'custom') {
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
  }

  try {
    const data = await API.get('/analytics/sources', params);
    const sym = data.currency_symbol || CONFIG.getCurrencySymbol();
    document.querySelectorAll('.currency-sym-label').forEach(el => el.textContent = sym);

    renderSourceCards(data.sources_data || {}, sym);
    renderSourceTable(data.table_data || [], sym);
    renderSourceComparisonChart(data.chart || {});
  } catch (err) {
    console.error('Failed to load source comparison:', err);
    UI.showToast('Could not load sources comparison data.', 'error');
  }
}

function renderSourceCards(sourcesData, sym) {
  const container = document.getElementById('sources-cards-container');
  if (!container) return;

  const icons = {
    'Solar': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>',
    'Wind': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" stroke-width="2"><path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"></path></svg>',
    'Hydro': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"></path></svg>',
    'Biomass': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#84cc16" stroke-width="2"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"></path><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"></path></svg>',
    'Geothermal': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>',
    'Other Renewable': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M12 6v6l4 2"></path></svg>'
  };

  container.innerHTML = CONFIG.RENEWABLE_SOURCES.map(src => {
    const s = sourcesData[src] || { total_generated_kwh: 0, total_renewable_consumed_kwh: 0, contribution_percentage: 0, estimated_co2_avoided_kg: 0, estimated_cost_savings: 0, record_count: 0 };
    return `
      <div class="kpi-card">
        <div class="kpi-header">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            ${icons[src] || ''}
            <span class="kpi-title" style="font-size: 0.875rem; font-weight: 700; color: var(--text-main);">${src}</span>
          </div>
          <span class="badge ${s.contribution_percentage > 0 ? 'badge-success' : 'badge-neutral'}">${s.contribution_percentage}% Share</span>
        </div>
        <div style="margin: 0.75rem 0;">
          <div class="kpi-value">${(s.total_generated_kwh || 0).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} <span class="kpi-unit">kWh</span></div>
          <div class="text-xs text-muted">Generated (${s.record_count || 0} records logged)</div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; padding-top: 0.75rem; border-top: 1px solid var(--border-subtle); font-size: 0.75rem;">
          <div>
            <div class="text-muted">Consumed</div>
            <strong>${(s.total_renewable_consumed_kwh || 0).toFixed(1)} kWh</strong>
          </div>
          <div>
            <div class="text-muted">CO2 Avoided</div>
            <strong class="text-primary">${(s.estimated_co2_avoided_kg || 0).toFixed(1)} kg</strong>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function renderSourceTable(tableData, sym) {
  const tbody = document.getElementById('sources-tbody');
  if (!tbody) return;

  if (!tableData.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted" style="padding: 2rem;">No data logged for the selected filter.</td></tr>`;
    return;
  }

  tbody.innerHTML = tableData.map(s => {
    const srcClass = `badge-${s.source.toLowerCase().replace(' ', '-')}`;
    return `
      <tr>
        <td><span class="badge ${srcClass}">${s.source}</span></td>
        <td><strong>${s.record_count}</strong></td>
        <td><strong class="text-primary">${(s.total_generated_kwh || 0).toFixed(1)} kWh</strong></td>
        <td>${(s.total_renewable_consumed_kwh || 0).toFixed(1)} kWh</td>
        <td><span class="badge badge-success">${s.contribution_percentage}%</span></td>
        <td>${(s.estimated_co2_avoided_kg || 0).toFixed(1)} kg</td>
        <td><strong>${sym}${(s.estimated_cost_savings || 0).toFixed(2)}</strong></td>
      </tr>
    `;
  }).join('');
}

function renderSourceComparisonChart(chartData) {
  const ctx = document.getElementById('sourceComparisonChart');
  if (!ctx || !chartData.labels) return;

  if (sourceComparisonChart) sourceComparisonChart.destroy();
  sourceComparisonChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: chartData.labels,
      datasets: [
        {
          label: 'Energy Generated (kWh)',
          data: chartData.generated || [],
          backgroundColor: '#10b981',
          borderRadius: 6
        },
        {
          label: 'Renewable Consumed (kWh)',
          data: chartData.consumed || [],
          backgroundColor: '#0284c7',
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'top' } },
      scales: {
        y: { beginAtZero: true, grid: { color: 'rgba(150, 150, 150, 0.1)' } },
        x: { grid: { display: false } }
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('sources-cards-container')) {
    loadSourceComparison();

    document.getElementById('sources-source-filter')?.addEventListener('change', loadSourceComparison);
    document.getElementById('sources-time-filter')?.addEventListener('change', (e) => {
      const customDates = document.getElementById('sources-custom-date-fields');
      if (customDates) {
        customDates.style.display = e.target.value === 'custom' ? 'flex' : 'none';
      }
      loadSourceComparison();
    });
    document.getElementById('sources-start-date')?.addEventListener('change', loadSourceComparison);
    document.getElementById('sources-end-date')?.addEventListener('change', loadSourceComparison);
  }
});
