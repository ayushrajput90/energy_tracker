/**
 * Environmental Impact & Carbon Emission Avoidance Analysis
 */
let environmentalChart = null;

async function loadEnvironmentalImpact() {
  const sourceFilter = document.getElementById('env-source-filter')?.value || '';
  const timeFilter = document.getElementById('env-time-filter')?.value || 'all';
  const startDate = document.getElementById('env-start-date')?.value || '';
  const endDate = document.getElementById('env-end-date')?.value || '';

  const params = {
    source: sourceFilter,
    time_filter: timeFilter
  };
  if (timeFilter === 'custom') {
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
  }

  try {
    const data = await API.get('/analytics/environmental', params);
    renderEnvironmentalKPIs(data);
    renderEquivalencies(data.equivalencies || {});
    renderMethodology(data.methodology || {});
    renderEnvironmentalChart(data.trend || []);
  } catch (err) {
    console.error('Failed to load environmental data:', err);
    UI.showToast('Could not load environmental impact data.', 'error');
  }
}

function renderEnvironmentalKPIs(data) {
  const elTot = document.getElementById('env-total-co2');
  if (elTot) elTot.textContent = `${(data.total_co2_avoided_kg || 0).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`;

  const elToday = document.getElementById('env-today-co2');
  if (elToday) elToday.textContent = `${(data.today_co2_avoided_kg || 0).toFixed(1)} kg`;

  const elMonth = document.getElementById('env-month-co2');
  if (elMonth) elMonth.textContent = `${(data.monthly_co2_avoided_kg || 0).toFixed(1)} kg`;

  const elYear = document.getElementById('env-year-co2');
  if (elYear) elYear.textContent = `${(data.yearly_co2_avoided_kg || 0).toFixed(1)} kg`;

  const elGrid = document.getElementById('env-grid-displaced');
  if (elGrid) elGrid.textContent = `${(data.estimated_grid_displaced_kwh || 0).toFixed(1)} kWh`;
}

function renderEquivalencies(eq) {
  const elTrees = document.getElementById('equiv-trees');
  if (elTrees) elTrees.textContent = eq.trees_planted_yearly || 0;

  const elMiles = document.getElementById('equiv-miles');
  if (elMiles) elMiles.textContent = (eq.car_miles_displaced || 0).toLocaleString();

  const elCoal = document.getElementById('equiv-coal');
  if (elCoal) elCoal.textContent = `${(eq.coal_burn_avoided_lbs || 0).toLocaleString()} lbs`;
}

function renderMethodology(meth) {
  const elFormula = document.getElementById('meth-formula');
  if (elFormula) elFormula.textContent = meth.formula || '';

  const elFactor = document.getElementById('meth-factor');
  if (elFactor) elFactor.textContent = meth.factor_used || '';

  const elDesc = document.getElementById('meth-desc');
  if (elDesc) elDesc.textContent = meth.description || '';
}

function renderEnvironmentalChart(trend) {
  const ctx = document.getElementById('environmentalTrendChart');
  if (!ctx) return;

  const labels = trend.map(t => t.date);
  const values = trend.map(t => t.estimated_co2_avoided_kg);

  if (environmentalChart) environmentalChart.destroy();
  environmentalChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels.length ? labels : ['No Data in Selected Period'],
      datasets: [{
        label: 'Estimated CO2 Avoided (kg)',
        data: labels.length ? values : [0],
        borderColor: '#059669',
        backgroundColor: 'rgba(5, 150, 105, 0.12)',
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
  if (document.getElementById('env-total-co2')) {
    loadEnvironmentalImpact();

    document.getElementById('env-source-filter')?.addEventListener('change', loadEnvironmentalImpact);
    document.getElementById('env-time-filter')?.addEventListener('change', (e) => {
      const customDates = document.getElementById('env-custom-date-fields');
      if (customDates) {
        customDates.style.display = e.target.value === 'custom' ? 'flex' : 'none';
      }
      loadEnvironmentalImpact();
    });
    document.getElementById('env-start-date')?.addEventListener('change', loadEnvironmentalImpact);
    document.getElementById('env-end-date')?.addEventListener('change', loadEnvironmentalImpact);
  }
});
