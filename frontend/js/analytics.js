/**
 * Advanced Visual Analytics & Chart.js Visualizations
 */
let trendChart = null;
let renVsGridChart = null;
let sourceDonutChart = null;
let co2SavingsChart = null;

async function loadAnalytics() {
  const source = document.getElementById('analytics-source-filter')?.value || '';
  const timeFilter = document.getElementById('analytics-time-filter')?.value || 'this_year';
  const startDate = document.getElementById('analytics-start-date')?.value || '';
  const endDate = document.getElementById('analytics-end-date')?.value || '';

  const params = {
    source: source,
    time_filter: timeFilter
  };
  if (timeFilter === 'custom') {
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
  }

  try {
    const data = await API.get('/analytics/overview', params);
    renderAnalyticsStats(data.summary || {}, data.currency_symbol || CONFIG.getCurrencySymbol());
    renderAnalyticsCharts(data);
  } catch (err) {
    console.error('Failed to load analytics data:', err);
    UI.showToast('Could not load analytics charts.', 'error');
  }
}

function renderAnalyticsStats(summary, currSym) {
  const sym = currSym || CONFIG.getCurrencySymbol();
  
  const elGen = document.getElementById('analytics-stat-gen');
  if (elGen) elGen.textContent = `${(summary.total_generated_kwh || 0).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} kWh`;

  const elRen = document.getElementById('analytics-stat-ren');
  if (elRen) elRen.textContent = `${(summary.total_renewable_consumed_kwh || 0).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} kWh`;

  const elPct = document.getElementById('analytics-stat-pct');
  if (elPct) elPct.textContent = `${summary.renewable_percentage || 0}%`;

  const elCo2 = document.getElementById('analytics-stat-co2');
  if (elCo2) elCo2.textContent = `${(summary.estimated_co2_avoided_kg || 0).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} kg`;

  const elSavings = document.getElementById('analytics-stat-savings');
  if (elSavings) elSavings.textContent = `${sym}${(summary.estimated_cost_savings || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function renderAnalyticsCharts(data) {
  const series = data.daily_series || [];
  const dates = series.map(s => s.date);
  const genValues = series.map(s => s.total_generated_kwh);
  const renConValues = series.map(s => s.total_renewable_consumed_kwh);
  const gridConValues = series.map(s => s.total_grid_consumed_kwh);
  const co2Values = series.map(s => s.estimated_co2_avoided_kg);
  const savingsValues = series.map(s => s.estimated_cost_savings);
  const sym = data.currency_symbol || CONFIG.getCurrencySymbol();

  // 1. Generation & Consumption Trend (Line Chart)
  const ctxTrend = document.getElementById('analyticsTrendChart');
  if (ctxTrend) {
    if (trendChart) trendChart.destroy();
    trendChart = new Chart(ctxTrend, {
      type: 'line',
      data: {
        labels: dates.length ? dates : ['No Data in Selected Period'],
        datasets: [
          {
            label: 'Renewable Generated (kWh)',
            data: dates.length ? genValues : [0],
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.12)',
            fill: true,
            tension: 0.35,
            borderWidth: 2
          },
          {
            label: 'Renewable Consumed (kWh)',
            data: dates.length ? renConValues : [0],
            borderColor: '#0284c7',
            backgroundColor: 'transparent',
            borderDash: [5, 5],
            tension: 0.35,
            borderWidth: 2
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

  // 2. Renewable vs Grid Consumption (Stacked Bar)
  const ctxGrid = document.getElementById('analyticsRenVsGridChart');
  if (ctxGrid) {
    if (renVsGridChart) renVsGridChart.destroy();
    renVsGridChart = new Chart(ctxGrid, {
      type: 'bar',
      data: {
        labels: dates.length ? dates : ['No Data in Selected Period'],
        datasets: [
          {
            label: 'Renewable Consumed',
            data: dates.length ? renConValues : [0],
            backgroundColor: '#10b981',
            borderRadius: 4
          },
          {
            label: 'Grid Electricity Consumed',
            data: dates.length ? gridConValues : [0],
            backgroundColor: '#ef4444',
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'top' } },
        scales: {
          x: { stacked: true, grid: { display: false } },
          y: { stacked: true, beginAtZero: true, grid: { color: 'rgba(150, 150, 150, 0.1)' } }
        }
      }
    });
  }

  // 3. Source Contribution Breakdown
  const sourcesData = data.sources_data || {};
  const srcLabels = Object.keys(sourcesData);
  const srcGen = srcLabels.map(k => sourcesData[k].total_generated_kwh);
  const srcColors = srcLabels.map(k => CONFIG.SOURCE_COLORS[k] || '#8b5cf6');

  const ctxSource = document.getElementById('analyticsSourceDonutChart');
  if (ctxSource) {
    if (sourceDonutChart) sourceDonutChart.destroy();
    const hasGen = srcGen.some(v => v > 0);
    sourceDonutChart = new Chart(ctxSource, {
      type: 'doughnut',
      data: {
        labels: hasGen ? srcLabels : ['No Generation in Selected Range'],
        datasets: [{
          data: hasGen ? srcGen : [1],
          backgroundColor: hasGen ? srcColors : ['#cbd5e1'],
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'right' } }
      }
    });
  }

  // 4. CO2 Avoided & Financial Savings Trend
  const ctxCo2 = document.getElementById('analyticsCo2SavingsChart');
  if (ctxCo2) {
    if (co2SavingsChart) co2SavingsChart.destroy();
    co2SavingsChart = new Chart(ctxCo2, {
      type: 'line',
      data: {
        labels: dates.length ? dates : ['No Data in Selected Period'],
        datasets: [
          {
            label: 'CO2 Avoided (kg)',
            data: dates.length ? co2Values : [0],
            borderColor: '#059669',
            backgroundColor: 'rgba(5, 150, 105, 0.08)',
            yAxisID: 'y',
            tension: 0.35
          },
          {
            label: `Cost Savings (${sym})`,
            data: dates.length ? savingsValues : [0],
            borderColor: '#f59e0b',
            backgroundColor: 'rgba(245, 158, 11, 0.08)',
            yAxisID: 'y1',
            tension: 0.35
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'top' } },
        scales: {
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: { display: true, text: 'CO2 Avoided (kg)' },
            grid: { color: 'rgba(150, 150, 150, 0.1)' }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            title: { display: true, text: `Savings (${sym})` },
            grid: { drawOnChartArea: false }
          },
          x: { grid: { display: false } }
        }
      }
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('analyticsTrendChart')) {
    loadAnalytics();

    document.getElementById('analytics-source-filter')?.addEventListener('change', loadAnalytics);
    document.getElementById('analytics-time-filter')?.addEventListener('change', (e) => {
      const customDates = document.getElementById('analytics-custom-date-fields');
      if (customDates) {
        customDates.style.display = e.target.value === 'custom' ? 'flex' : 'none';
      }
      loadAnalytics();
    });
    document.getElementById('analytics-start-date')?.addEventListener('change', loadAnalytics);
    document.getElementById('analytics-end-date')?.addEventListener('change', loadAnalytics);
  }
});
