/**
 * Energy Records Management & CRUD Operations
 */
let currentRecordsPage = 1;
let currentRecordsLimit = 10;
let deleteTargetId = null;

async function loadEnergyRecords() {
  const sourceFilter = document.getElementById('filter-source')?.value || '';
  const timeFilter = document.getElementById('filter-time')?.value || '';
  const startDate = document.getElementById('filter-start-date')?.value || '';
  const endDate = document.getElementById('filter-end-date')?.value || '';
  const searchQuery = document.getElementById('filter-search')?.value || '';

  const params = {
    source: sourceFilter,
    time_filter: timeFilter,
    start_date: startDate,
    end_date: endDate,
    search: searchQuery,
    page: currentRecordsPage,
    limit: currentRecordsLimit
  };

  try {
    const data = await API.get('/energy', params);
    renderRecordsTable(data.records || []);
    renderRecordsSummary(data.summary || {});
    renderPagination(data.pagination);
  } catch (err) {
    console.error('Failed to load records:', err);
    UI.showToast('Could not load energy records.', 'error');
  }
}

function renderRecordsTable(records) {
  const tbody = document.getElementById('records-tbody');
  const currSym = CONFIG.getCurrencySymbol();
  if (!tbody) return;

  if (!records.length) {
    tbody.innerHTML = `<tr><td colspan="12" class="text-center text-muted" style="padding: 2.5rem;">No matching records found. Use the filters or click <strong>Add Energy Data</strong> to add records.</td></tr>`;
    return;
  }

  tbody.innerHTML = records.map(r => {
    const srcClass = `badge-${r.renewable_source.toLowerCase().replace(' ', '-')}`;
    const modeBadge = r.is_override
      ? '<span class="badge badge-warning" style="font-size: 0.7rem;">Override</span>'
      : '<span class="badge badge-neutral" style="font-size: 0.7rem;">Auto</span>';

    const surplusDisplay = r.surplus_kwh > 0 ? `<span class="text-primary font-bold">+${r.surplus_kwh.toFixed(1)}</span>` : '0.0';
    const storageUsedDisplay = r.storage_used_kwh > 0 ? `<span style="color: #0284c7;">${r.storage_used_kwh.toFixed(1)}</span>` : '0.0';

    return `
      <tr>
        <td><strong>#${r.id}</strong></td>
        <td>${r.date}</td>
        <td><span class="badge ${srcClass}">${r.renewable_source}</span></td>
        <td>${modeBadge}</td>
        <td><strong class="text-primary">${r.energy_generated_kwh.toFixed(1)} kWh</strong></td>
        <td>${r.renewable_energy_consumed_kwh.toFixed(1)} kWh</td>
        <td>${storageUsedDisplay}</td>
        <td>${surplusDisplay}</td>
        <td>${r.grid_energy_consumed_kwh.toFixed(1)} kWh</td>
        <td><span class="badge badge-success">${r.renewable_percentage}%</span></td>
        <td>${currSym}${(r.estimated_savings || 0).toFixed(2)}</td>
        <td>
          <div class="table-actions">
            <button class="btn btn-sm btn-secondary" onclick="viewRecordDetails(${r.id})" title="View Details">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
            </button>
            <button class="btn btn-sm btn-outline" onclick="openEditRecordModal(${r.id})" title="Edit Record">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
            </button>
            <button class="btn btn-sm btn-danger" onclick="confirmDeleteRecord(${r.id})" title="Delete Record">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function renderRecordsSummary(summary) {
  const currSym = CONFIG.getCurrencySymbol();
  const elCount = document.getElementById('summary-record-count');
  if (elCount) elCount.textContent = `${summary.count || 0} Records`;

  const elGen = document.getElementById('summary-total-gen');
  if (elGen) elGen.textContent = `${(summary.total_generated_kwh || 0).toFixed(1)} kWh`;

  const elRen = document.getElementById('summary-total-ren');
  if (elRen) elRen.textContent = `${(summary.total_renewable_consumed_kwh || 0).toFixed(1)} kWh`;

  const elSurp = document.getElementById('summary-total-surplus');
  if (elSurp) elSurp.textContent = `+${(summary.total_surplus_kwh || 0).toFixed(1)} kWh`;

  const elCo2 = document.getElementById('summary-total-co2');
  if (elCo2) elCo2.textContent = `${(summary.estimated_co2_avoided_kg || 0).toFixed(1)} kg`;

  const elSavings = document.getElementById('summary-total-savings');
  if (elSavings) elSavings.textContent = `${currSym}${(summary.estimated_cost_savings || 0).toFixed(2)}`;
}

function renderPagination(pagination) {
  const container = document.getElementById('records-pagination');
  if (!container || !pagination) return;

  const { page, total_pages, total_items } = pagination;
  if (total_pages <= 1) {
    container.innerHTML = `<div class="text-sm text-muted">Showing all ${total_items} records</div>`;
    return;
  }

  container.innerHTML = `
    <div class="text-sm text-muted">Page ${page} of ${total_pages} (${total_items} total records)</div>
    <div style="display: flex; gap: 0.5rem;">
      <button class="btn btn-sm btn-secondary" onclick="changeRecordsPage(${page - 1})" ${page <= 1 ? 'disabled' : ''}>Previous</button>
      <button class="btn btn-sm btn-secondary" onclick="changeRecordsPage(${page + 1})" ${page >= total_pages ? 'disabled' : ''}>Next</button>
    </div>
  `;
}

function changeRecordsPage(newPage) {
  currentRecordsPage = newPage;
  loadEnergyRecords();
}

async function viewRecordDetails(recordId) {
  try {
    const data = await API.get(`/energy/${recordId}`);
    const r = data.record;
    const currSym = CONFIG.getCurrencySymbol();
    
    document.getElementById('view-id').textContent = `#${r.id}`;
    document.getElementById('view-date').textContent = r.date;
    document.getElementById('view-source').textContent = r.renewable_source;
    document.getElementById('view-mode').textContent = r.is_override ? 'Manual Weather Override' : 'Automatic Generation';
    document.getElementById('view-gen').textContent = `${r.energy_generated_kwh} kWh`;
    document.getElementById('view-auto-gen').textContent = `${r.automatic_generation_kwh || r.energy_generated_kwh} kWh`;
    document.getElementById('view-override-gen').textContent = r.override_generation_kwh ? `${r.override_generation_kwh} kWh` : 'None';
    document.getElementById('view-ren-con').textContent = `${r.renewable_energy_consumed_kwh} kWh`;
    document.getElementById('view-stor-used').textContent = `${r.storage_used_kwh || 0} kWh`;
    document.getElementById('view-surplus').textContent = `+${(r.surplus_kwh || 0).toFixed(2)} kWh`;
    document.getElementById('view-storage-bal').textContent = `${(r.storage_balance_kwh || 0).toFixed(2)} kWh`;
    document.getElementById('view-grid-con').textContent = `${r.grid_energy_consumed_kwh} kWh`;
    document.getElementById('view-tot-con').textContent = `${r.total_energy_consumed_kwh} kWh`;
    document.getElementById('view-pct').textContent = `${r.renewable_percentage}%`;
    document.getElementById('view-tariff').textContent = `${currSym}${r.electricity_tariff}/kWh`;
    document.getElementById('view-co2').textContent = `${r.co2_avoided_kg} kg CO2`;
    document.getElementById('view-savings').textContent = `${currSym}${(r.estimated_savings || 0).toFixed(2)}`;
    document.getElementById('view-notes').textContent = r.notes || 'None';

    UI.openModal('view-record-modal');
  } catch (err) {
    UI.showToast(err.message || 'Could not fetch record details.', 'error');
  }
}

async function openEditRecordModal(recordId) {
  try {
    const data = await API.get(`/energy/${recordId}`);
    const r = data.record;

    document.getElementById('edit-record-id').value = r.id;
    document.getElementById('edit-date').value = r.date;
    document.getElementById('edit-source').value = r.renewable_source;
    document.getElementById('edit-gen').value = r.energy_generated_kwh;
    document.getElementById('edit-ren-con').value = r.renewable_energy_consumed_kwh;
    document.getElementById('edit-storage-used').value = r.storage_used_kwh || 0;
    document.getElementById('edit-grid-con').value = r.grid_energy_consumed_kwh;
    document.getElementById('edit-tariff').value = r.electricity_tariff;
    document.getElementById('edit-notes').value = r.notes || '';

    UI.openModal('edit-record-modal');
  } catch (err) {
    UI.showToast('Could not load record for editing.', 'error');
  }
}

async function saveEditedRecord(event) {
  event.preventDefault();
  const id = document.getElementById('edit-record-id').value;
  const payload = {
    date: document.getElementById('edit-date').value,
    renewable_source: document.getElementById('edit-source').value,
    energy_generated_kwh: parseFloat(document.getElementById('edit-gen').value),
    renewable_energy_consumed_kwh: parseFloat(document.getElementById('edit-ren-con').value),
    storage_used_kwh: parseFloat(document.getElementById('edit-storage-used').value || 0),
    grid_energy_consumed_kwh: parseFloat(document.getElementById('edit-grid-con').value),
    electricity_tariff: parseFloat(document.getElementById('edit-tariff').value),
    notes: document.getElementById('edit-notes').value
  };

  try {
    await API.put(`/energy/${id}`, payload);
    UI.showToast('Record updated successfully!', 'success');
    UI.closeModal('edit-record-modal');
    loadEnergyRecords();
  } catch (err) {
    UI.showToast(err.message || 'Failed to update record.', 'error');
  }
}

function confirmDeleteRecord(recordId) {
  deleteTargetId = recordId;
  UI.openModal('delete-confirm-modal');
}

async function executeDeleteRecord() {
  if (!deleteTargetId) return;
  try {
    await API.delete(`/energy/${deleteTargetId}`);
    UI.showToast('Record deleted successfully.', 'info');
    UI.closeModal('delete-confirm-modal');
    deleteTargetId = null;
    loadEnergyRecords();
  } catch (err) {
    UI.showToast(err.message || 'Failed to delete record.', 'error');
  }
}

async function exportRecordsCSV() {
  try {
    const currSym = CONFIG.getCurrencySymbol();
    if (CONFIG.DEMO_MODE) {
      // Standalone demo CSV generation
      const records = JSON.parse(localStorage.getItem('DEMO_RECORDS') || '[]');
      let csv = `Record ID,Date,Source,Mode,Generated (kWh),Renewable Consumed (kWh),Storage Used (kWh),Surplus (kWh),Grid Consumed (kWh),Total Consumed (kWh),Renewable (%),Tariff (${currSym}/kWh),Estimated Savings (${currSym}),Notes\n`;
      records.forEach(r => {
        const mode = r.is_override ? 'Manual Override' : 'Automatic';
        csv += `${r.id},${r.date},${r.renewable_source},${mode},${r.energy_generated_kwh},${r.renewable_energy_consumed_kwh},${r.storage_used_kwh || 0},${r.surplus_kwh || 0},${r.grid_energy_consumed_kwh},${r.total_energy_consumed_kwh || (r.renewable_energy_consumed_kwh + r.grid_energy_consumed_kwh)},${r.renewable_percentage || 0}%,${r.electricity_tariff},${currSym}${(r.estimated_savings || 0).toFixed(2)},"${r.notes || ''}"\n`;
      });
      const blob = new Blob([csv], { type: 'text/csv' });
      downloadBlob(blob, 'energy_records_demo.csv');
      UI.showToast('Demo CSV exported successfully!', 'success');
      return;
    }

    const blob = await API.request('/energy/export/csv', { method: 'GET' });
    downloadBlob(blob, `energy_records_${new Date().toISOString().split('T')[0]}.csv`);
    UI.showToast('Records exported to CSV successfully!', 'success');
  } catch (err) {
    UI.showToast('Failed to export CSV.', 'error');
  }
}

function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  a.remove();
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('records-tbody')) {
    loadEnergyRecords();

    // Event listeners for filters
    document.getElementById('filter-source')?.addEventListener('change', () => { currentRecordsPage = 1; loadEnergyRecords(); });
    document.getElementById('filter-time')?.addEventListener('change', (e) => {
      const customDates = document.getElementById('custom-date-range-fields');
      if (customDates) {
        customDates.style.display = e.target.value === 'custom' ? 'flex' : 'none';
      }
      currentRecordsPage = 1;
      loadEnergyRecords();
    });
    document.getElementById('filter-start-date')?.addEventListener('change', () => { currentRecordsPage = 1; loadEnergyRecords(); });
    document.getElementById('filter-end-date')?.addEventListener('change', () => { currentRecordsPage = 1; loadEnergyRecords(); });
    document.getElementById('filter-search')?.addEventListener('input', () => { currentRecordsPage = 1; loadEnergyRecords(); });
  }
});
