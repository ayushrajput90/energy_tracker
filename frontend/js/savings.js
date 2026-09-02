/**
 * Electricity Cost Savings & Financial Analytics
 */
let savingsChart = null;

async function loadSavingsData() {
  const sourceFilter = document.getElementById('sav-source-filter')?.value || '';
  const timeFilter = document.getElementById('sav-time-filter')?.value || 'all';
  const startDate = document.getElementById('sav-start-date')?.value || '';
  const endDate = document.getElementById('sav-end-date')?.value || '';

  const params = {
    source: sourceFilter,
    time_filter: timeFilter
  };
  if (timeFilter === 'custom') {
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
  }

  try {
    const data = await API.get('/analytics/savings', params);
    const sym = data.currency_symbol || CONFIG.getCurrencySymbol();

    renderSavingsKPIs(data, sym);
    renderSavingsMethodology(data.methodology || {}, data.current_tariff || 9.0, sym);
    renderSavingsChart(data.trend || [], sym);
  } catch (err) {
    console.error('Failed to load savings data:', err);
    UI.showToast('Could not load savings analytics.', 'error');
  }
}

function renderSavingsKPIs(data, sym) {
  const elTot = document.getElementById('sav-total');
  if (elTot) elTot.textContent = `${sym}${(data.total_savings || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const elToday = document.getElementById('sav-today');
  if (elToday) elToday.textContent = `${sym}${(data.today_savings || 0).toFixed(2)}`;

  const elMonth = document.getElementById('sav-month');
  if (elMonth) elMonth.textContent = `${sym}${(data.monthly_savings || 0).toFixed(2)}`;

  const elYear = document.getElementById('sav-year');
  if (elYear) elYear.textContent = `${sym}${(data.yearly_savings || 0).toFixed(2)}`;

  const elRen = document.getElementById('sav-ren-consumed');
  if (elRen) elRen.textContent = `${(data.renewable_consumed_kwh || 0).toFixed(1)}`;

  const elBadge = document.getElementById('sav-tariff-badge');
  if (elBadge) elBadge.textContent = `${sym}${(data.current_tariff || 9.0).toFixed(2)}/kWh Tariff Rate`;
}

function renderSavingsMethodology(meth, tariff, sym) {
  const elFormula = document.getElementById('sav-formula');
  if (elFormula) elFormula.textContent = meth.formula || `Estimated Cost Savings = Renewable Energy Consumed (kWh) × Electricity Tariff (${sym}/kWh)`;

  const elRate = document.getElementById('sav-rate-used');
  if (elRate) elRate.textContent = `${sym}${parseFloat(tariff).toFixed(4)} / kWh`;

  const elNotes = document.getElementById('sav-notes');
  if (elNotes && meth.notes) elNotes.textContent = meth.notes;
}

function renderSavingsChart(trend, sym) {
  const ctx = document.getElementById('savingsTrendChart');
  if (!ctx) return;

  const labels = trend.map(t => t.date);
  let runningSavings = 0;
  const accumulatedValues = trend.map(t => {
    runningSavings += (t.estimated_cost_savings || 0);
    return Math.round(runningSavings * 100) / 100;
  });

  if (savingsChart) savingsChart.destroy();
  savingsChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels.length ? labels : ['No Data in Selected Period'],
      datasets: [{
        label: `Cumulative Savings (${sym})`,
        data: labels.length ? accumulatedValues : [0],
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245, 158, 11, 0.12)',
        fill: true,
        tension: 0.35,
        borderWidth: 2
      }]
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
  if (document.getElementById('sav-total')) {
    loadSavingsData();

    document.getElementById('sav-source-filter')?.addEventListener('change', loadSavingsData);
    document.getElementById('sav-time-filter')?.addEventListener('change', (e) => {
      const customDates = document.getElementById('sav-custom-date-fields');
      if (customDates) {
        customDates.style.display = e.target.value === 'custom' ? 'flex' : 'none';
      }
      loadSavingsData();
    });
    document.getElementById('sav-start-date')?.addEventListener('change', loadSavingsData);
    document.getElementById('sav-end-date')?.addEventListener('change', loadSavingsData);
  }
});
