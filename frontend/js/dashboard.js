/**
 * Simple & Professional Dashboard Logic
 * Handles date range selector, 6 KPI cards, and Renewable Generation vs Consumption Bar Chart
 */
let dashboardGenChart = null;

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
    const stats = await API.get('/dashboard/stats', params);
    renderKPICards(stats);
    renderGenerationVsConsumptionChart(stats);
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
  if (periodSelect && periodSelect.value !== 'custom') {
    loadDashboard();
  }
}

function renderKPICards(data) {
  const periodData = data.period_summary || data.overall || {};
  const currSym = data.system?.currency_symbol || CONFIG.getCurrencySymbol();
  const storage = data.storage || {};

  // 1. Renewable Energy Generated
  const elGen = document.getElementById('kpi-total-gen');
  if (elGen) elGen.textContent = (periodData.total_generated_kwh || 0).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  // 2. Renewable Energy Consumed
  const elRenCon = document.getElementById('kpi-total-ren-con');
  if (elRenCon) elRenCon.textContent = (periodData.total_renewable_consumed_kwh || 0).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  // 3. CO2 Emissions Avoided
  const elCo2 = document.getElementById('kpi-co2-avoided');
  if (elCo2) elCo2.textContent = (periodData.estimated_co2_avoided_kg || 0).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  // 4. Cost Savings
  const elSavings = document.getElementById('kpi-savings');
  if (elSavings) elSavings.textContent = `${currSym}${(periodData.estimated_cost_savings || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  // 5. Stored Renewable Energy (current available storage balance)
  const elStorage = document.getElementById('kpi-storage-bal');
  if (elStorage) elStorage.textContent = (storage.available_kwh !== undefined ? storage.available_kwh : 0.0).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  // 6. Active Goals
  const elGoals = document.getElementById('kpi-goals-count');
  const activeCount = data.active_goals_count !== undefined ? data.active_goals_count : (data.active_goals?.length || 0);
  if (elGoals) {
    elGoals.textContent = activeCount > 0 ? `${activeCount} Active` : 'No Active Goals';
  }
}

function renderGenerationVsConsumptionChart(data) {
  const chartData = data.chart_data || {};
  const labels = chartData.labels || [];
  const genData = chartData.generated || [];
  const conData = chartData.consumed || [];

  const periodBadge = document.getElementById('dash-chart-period-badge');
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
    periodBadge.textContent = pNames[data.selected_period] || 'Selected Period';
  }

  const canvas = document.getElementById('dashboardGenChart');
  const emptyState = document.getElementById('dashboard-chart-empty');
  const chartWrapper = document.getElementById('dashboard-chart-wrapper');
  if (!canvas) return;

  const hasData = labels.length > 0 && (genData.some(v => v > 0) || conData.some(v => v > 0));

  if (!hasData) {
    if (chartWrapper) chartWrapper.style.display = 'none';
    if (emptyState) emptyState.style.display = 'block';
    if (dashboardGenChart) {
      dashboardGenChart.destroy();
      dashboardGenChart = null;
    }
    return;
  }

  if (chartWrapper) chartWrapper.style.display = 'block';
  if (emptyState) emptyState.style.display = 'none';

  if (dashboardGenChart) {
    dashboardGenChart.destroy();
  }

  dashboardGenChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Generated (kWh)',
          data: genData,
          backgroundColor: '#10b981',
          borderColor: '#059669',
          borderWidth: 1,
          borderRadius: 6,
          maxBarThickness: 45
        },
        {
          label: 'Renewable Consumed (kWh)',
          data: conData,
          backgroundColor: '#0284c7',
          borderColor: '#0369a1',
          borderWidth: 1,
          borderRadius: 6,
          maxBarThickness: 45
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            font: { family: 'inherit', size: 12, weight: '600' },
            padding: 16
          }
        },
        tooltip: {
          padding: 10,
          boxPadding: 4,
          callbacks: {
            label: function (ctx) {
              return `${ctx.dataset.label}: ${ctx.raw.toFixed(1)} kWh`;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: 'Energy (kWh)' },
          grid: { color: 'rgba(150, 150, 150, 0.1)' }
        },
        x: {
          grid: { display: false }
        }
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('dashboard-period-select')) {
    loadDashboard();
  }
});
