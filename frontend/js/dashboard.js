/**
 * Dashboard Logic: Period Aggregation, Real-Time Stats, Storage & Telemetry Rendering
 */
let dashboardGenChart = null;
let dashboardSourceChart = null;

async function loadDashboard() {
  const periodSelect = document.getElementById('dashboard-period-select');
  const period = periodSelect ? periodSelect.value : 'all';

  const params = { period: period };
  if (period === 'custom') {
    const sDate = document.getElementById('dash-start-date')?.value;
    const eDate = document.getElementById('dash-end-date')?.value;
    if (sDate) params.start_date = sDate;
    if (eDate) params.end_date = eDate;
  }

  try {
    const [stats, recent] = await Promise.all([
      API.get('/dashboard/stats', params),
      API.get('/dashboard/recent')
    ]);

    renderKPICards(stats);
    renderSystemBanner(stats);
    renderSummaryBoxes(stats);
    renderDashboardCharts(stats);
    renderRecentRecords(recent.recent_records || []);
    renderRecentActivities(recent.recent_activities || []);
    renderDashboardInsights(recent.top_insights || []);
  } catch (err) {
    console.error('Failed to load dashboard data:', err);
    UI.showToast('Could not load dashboard statistics.', 'error');
  }
}

function handlePeriodChange() {
  const periodSelect = document.getElementById('dashboard-period-select');
  const customBox = document.getElementById('dash-custom-range');
  if (periodSelect && customBox) {
    customBox.style.display = periodSelect.value === 'custom' ? 'flex' : 'none';
  }
  if (periodSelect.value !== 'custom') {
    loadDashboard();
  }
}

function renderKPICards(data) {
  // Use period summary if specific period selected, else overall
  const periodData = data.period_summary || data.overall || {};
  const currSym = data.system?.currency_symbol || CONFIG.getCurrencySymbol();
  
  const elGen = document.getElementById('kpi-total-gen');
  if (elGen) elGen.textContent = (periodData.total_generated_kwh || 0).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  const elRenCon = document.getElementById('kpi-total-ren-con');
  if (elRenCon) elRenCon.textContent = (periodData.total_renewable_consumed_kwh || 0).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  const elTotCon = document.getElementById('kpi-total-con');
  if (elTotCon) elTotCon.textContent = (periodData.total_consumed_kwh || 0).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  const elPct = document.getElementById('kpi-ren-pct');
  if (elPct) elPct.textContent = `${periodData.renewable_percentage || 0}%`;

  const elCo2 = document.getElementById('kpi-co2-avoided');
  if (elCo2) elCo2.textContent = (periodData.estimated_co2_avoided_kg || 0).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  const elGrid = document.getElementById('kpi-grid-displaced');
  if (elGrid) elGrid.textContent = (periodData.estimated_grid_displaced_kwh || 0).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  const elSavings = document.getElementById('kpi-savings');
  if (elSavings) elSavings.textContent = `${currSym}${(periodData.estimated_cost_savings || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const elGoals = document.getElementById('kpi-goals-count');
  if (elGoals) elGoals.textContent = `${data.active_goals_count || 0} Active`;
}

function renderSystemBanner(data) {
  const telemetry = data.telemetry_today || {};
  const storage = data.storage || {};
  const system = data.system || {};

  // Today's Generation & Mode Badge
  const todayGenEl = document.getElementById('dash-today-gen');
  const genModeBadge = document.getElementById('dash-gen-status-badge');
  const autoExpectedEl = document.getElementById('dash-auto-expected');

  const finalGen = telemetry.total_final_generation_kwh !== undefined ? telemetry.total_final_generation_kwh : (data.today?.total_generated_kwh || 0);
  const autoGen = telemetry.total_automatic_generation_kwh !== undefined ? telemetry.total_automatic_generation_kwh : finalGen;

  if (todayGenEl) todayGenEl.textContent = `${finalGen.toFixed(1)} kWh`;
  if (autoExpectedEl) autoExpectedEl.textContent = `${autoGen.toFixed(1)} kWh`;

  if (genModeBadge) {
    if (telemetry.has_override) {
      genModeBadge.textContent = 'Manual Weather Override';
      genModeBadge.className = 'badge badge-warning';
    } else {
      genModeBadge.textContent = 'Automatic Mode';
      genModeBadge.className = 'badge badge-success';
    }
  }

  // Storage Stats
  const storageBalEl = document.getElementById('dash-storage-bal');
  if (storageBalEl) storageBalEl.textContent = `${(storage.available_kwh || 0).toFixed(1)} kWh`;

  const todaySurpEl = document.getElementById('dash-today-surplus');
  if (todaySurpEl) todaySurpEl.textContent = `+${(storage.today_surplus_kwh || 0).toFixed(1)} kWh`;

  const todayUsedEl = document.getElementById('dash-today-storage-used');
  if (todayUsedEl) todayUsedEl.textContent = `${(storage.today_storage_used_kwh || 0).toFixed(1)} kWh`;

  // Capacity & Sources
  const totalCapEl = document.getElementById('dash-total-cap');
  if (totalCapEl) totalCapEl.textContent = `${(system.installed_capacity_kw || 0).toFixed(1)} kW`;

  const sourcesCountBadge = document.getElementById('dash-active-sources-count');
  if (sourcesCountBadge) sourcesCountBadge.textContent = `${system.active_sources_count || 0} Sources`;
}

function renderSummaryBoxes(data) {
  const today = data.today || {};
  const period = data.period_summary || data.this_month || {};
  const periodBadge = document.getElementById('dash-period-badge');

  if (periodBadge) {
    const pNames = {
      'today': 'Today',
      'yesterday': 'Yesterday',
      'this_week': 'This Week',
      'this_month': 'This Month',
      'this_year': 'This Year',
      'all': 'All Time',
      'custom': 'Custom Range'
    };
    periodBadge.textContent = pNames[data.selected_period] || 'Period Summary';
  }

  const todayGen = document.getElementById('sum-today-gen');
  if (todayGen) todayGen.textContent = `${today.total_generated_kwh || 0} kWh`;

  const todayCon = document.getElementById('sum-today-con');
  if (todayCon) todayCon.textContent = `${today.total_consumed_kwh || 0} kWh`;

  const monthGen = document.getElementById('sum-month-gen');
  if (monthGen) monthGen.textContent = `${period.total_generated_kwh || 0} kWh`;

  const monthCon = document.getElementById('sum-month-con');
  if (monthCon) monthCon.textContent = `${period.total_consumed_kwh || 0} kWh`;
}

function renderDashboardCharts(data) {
  const sources = data.sources_summary || [];
  const labels = sources.map(s => s.source);
  const genData = sources.map(s => s.total_generated_kwh);
  const conData = sources.map(s => s.total_renewable_consumed_kwh);
  const bgColors = labels.map(l => CONFIG.SOURCE_COLORS[l] || '#8b5cf6');

  // Chart 1: Generation vs Consumption by Source (Bar)
  const ctxGen = document.getElementById('dashboardGenChart');
  if (ctxGen) {
    if (dashboardGenChart) dashboardGenChart.destroy();
    dashboardGenChart = new Chart(ctxGen, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Generated (kWh)',
            data: genData,
            backgroundColor: '#10b981',
            borderRadius: 6
          },
          {
            label: 'Renewable Consumed (kWh)',
            data: conData,
            backgroundColor: '#0284c7',
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top' }
        },
        scales: {
          y: { beginAtZero: true, grid: { color: 'rgba(150, 150, 150, 0.1)' } },
          x: { grid: { display: false } }
        }
      }
    });
  }

  // Chart 2: Source Distribution (Doughnut)
  const ctxSource = document.getElementById('dashboardSourceChart');
  if (ctxSource) {
    if (dashboardSourceChart) dashboardSourceChart.destroy();
    const hasData = genData.some(v => v > 0);
    dashboardSourceChart = new Chart(ctxSource, {
      type: 'doughnut',
      data: {
        labels: hasData ? labels : ['No Data Recorded'],
        datasets: [{
          data: hasData ? genData : [1],
          backgroundColor: hasData ? bgColors : ['#cbd5e1'],
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right' }
        },
        cutout: '68%'
      }
    });
  }
}

function renderRecentRecords(records) {
  const tbody = document.getElementById('recent-records-tbody');
  if (!tbody) return;

  if (!records.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted" style="padding: 2rem;">No energy records found. Click <strong>Add Energy Data</strong> to create your first record.</td></tr>`;
    return;
  }

  tbody.innerHTML = records.map(r => {
    const srcClass = `badge-${r.renewable_source.toLowerCase().replace(' ', '-')}`;
    const modeBadge = r.is_override
      ? '<span class="badge badge-warning" style="font-size: 0.7rem;">Override</span>'
      : '<span class="badge badge-neutral" style="font-size: 0.7rem;">Auto</span>';

    return `
      <tr>
        <td><strong>${r.date}</strong></td>
        <td><span class="badge ${srcClass}">${r.renewable_source}</span></td>
        <td>${modeBadge}</td>
        <td><span class="font-semibold text-primary">${r.energy_generated_kwh.toFixed(1)} kWh</span></td>
        <td>${r.renewable_energy_consumed_kwh.toFixed(1)} kWh</td>
        <td><span class="badge badge-success">${r.renewable_percentage}%</span></td>
      </tr>
    `;
  }).join('');
}

function renderRecentActivities(activities) {
  const container = document.getElementById('recent-activities-list');
  if (!container) return;

  if (!activities.length) {
    container.innerHTML = `<div class="text-muted text-sm text-center" style="padding: 1.5rem;">No recent activities logged.</div>`;
    return;
  }

  container.innerHTML = activities.map(a => {
    const d = new Date(a.timestamp);
    const timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const dateStr = d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    return `
      <div style="display: flex; gap: 0.75rem; align-items: flex-start; padding: 0.75rem 0; border-bottom: 1px solid var(--border-subtle);">
        <div style="width: 8px; height: 8px; border-radius: 50%; background-color: var(--primary-600); margin-top: 6px; flex-shrink: 0;"></div>
        <div style="flex: 1;">
          <div style="font-size: 0.8125rem; font-weight: 600; color: var(--text-main);">${a.description}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${dateStr} at ${timeStr}</div>
        </div>
      </div>
    `;
  }).join('');
}

function renderDashboardInsights(insights) {
  const container = document.getElementById('dashboard-insights-container');
  if (!container) return;

  if (!insights.length) {
    container.innerHTML = `<div class="text-muted text-sm">Add energy data to generate smart insights.</div>`;
    return;
  }

  container.innerHTML = insights.map(ins => `
    <div class="insight-card">
      <div class="insight-icon-box">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line></svg>
      </div>
      <div style="flex: 1;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.25rem;">
          <h4 class="insight-title" style="margin: 0;">${ins.title}</h4>
          <span class="badge badge-success">${ins.badge || 'Insight'}</span>
        </div>
        <p class="insight-message">${ins.message}</p>
      </div>
    </div>
  `).join('');
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('dashboardGenChart')) {
    loadDashboard();
  }
});
