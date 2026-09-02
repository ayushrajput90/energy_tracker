/**
 * Add Energy Data Portal: Source Configuration, Daily Generation, Manual Overrides & Storage Tracking
 */

let userSources = [];
let currentStorageBalance = 0.0;
let currentAutoGeneration = 15.0;
let currentFinalGeneration = 15.0;

const CURRENCY_INFO = {
  'INR': { symbol: '₹', defaultTariff: 9.0 },
  'USD': { symbol: '$', defaultTariff: 0.12 },
  'EUR': { symbol: '€', defaultTariff: 0.20 },
  'GBP': { symbol: '£', defaultTariff: 0.18 }
};

async function initAddEnergyPage() {
  const dateInput = document.getElementById('record-date');
  const effFromInput = document.getElementById('cfg-effective-from');
  const todayStr = new Date().toISOString().split('T')[0];

  if (dateInput && !dateInput.value) dateInput.value = todayStr;
  if (effFromInput && !effFromInput.value) effFromInput.value = todayStr;

  // Initialize currency selector and tariff
  const curCode = CONFIG.getCurrencyCode() || 'INR';
  const curSelect = document.getElementById('record-currency-code');
  if (curSelect) curSelect.value = curCode;

  updateCurrencyLabels(curCode);

  const tariffInput = document.getElementById('record-tariff');
  if (tariffInput && !tariffInput.value) {
    tariffInput.value = CONFIG.getTariff();
  }

  // Load configured sources and storage balance from backend
  await Promise.all([
    loadConfiguredSources(),
    loadStorageBalance()
  ]);

  // Bind live calculation listeners to all inputs
  ['record-actual-gen', 'record-ren-con', 'record-storage-used', 'record-grid-con', 'record-tariff'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', updateLivePreview);
      el.addEventListener('change', updateLivePreview);
    }
  });

  await handleDateOrSourceChange();
}

function handleCurrencySelectionChange() {
  const code = document.getElementById('record-currency-code')?.value || 'INR';
  updateCurrencyLabels(code);

  const tariffInput = document.getElementById('record-tariff');
  const info = CURRENCY_INFO[code] || { symbol: '₹', defaultTariff: 9.0 };
  if (tariffInput && (!tariffInput.value || parseFloat(tariffInput.value) === 0)) {
    tariffInput.value = info.defaultTariff;
  }

  updateLivePreview();
}

function updateCurrencyLabels(currencyCode) {
  const info = CURRENCY_INFO[currencyCode] || { symbol: '₹', defaultTariff: 9.0 };
  document.querySelectorAll('.currency-sym-label').forEach(el => {
    el.textContent = info.symbol;
  });
}

async function loadConfiguredSources() {
  try {
    const res = await API.get('/sources');
    userSources = res.sources || [];
    renderConfiguredSourcesList();
  } catch (err) {
    console.error('Failed to load configured sources:', err);
  }
}

async function loadStorageBalance() {
  try {
    const res = await API.get('/storage');
    currentStorageBalance = parseFloat(res.available_storage_kwh || 0);
    
    const prevEl = document.getElementById('prev-storage-bal');
    if (prevEl) prevEl.textContent = `${currentStorageBalance.toFixed(1)} kWh`;

    const badgeAvail = document.getElementById('badge-avail-storage');
    if (badgeAvail) badgeAvail.textContent = `Available: ${currentStorageBalance.toFixed(1)} kWh`;
  } catch (err) {
    console.error('Failed to load storage:', err);
  }
}

function renderConfiguredSourcesList() {
  const container = document.getElementById('configured-sources-container');
  const badge = document.getElementById('active-sources-badge');
  if (!container) return;

  const activeSources = userSources.filter(s => s.active);
  if (badge) badge.textContent = `${activeSources.length} Active Sources`;

  if (!userSources.length) {
    container.innerHTML = `
      <div style="background-color: var(--bg-surface-subtle); padding: 1rem; border-radius: var(--radius-md); text-align: center; color: var(--text-muted); font-size: 0.8125rem;">
        No renewable sources configured yet. Add your installed sources above to automate daily tracking.
      </div>
    `;
    return;
  }

  container.innerHTML = userSources.map(src => {
    const badgeClass = `badge-${src.source_type.toLowerCase().replace(' ', '-')}`;
    return `
      <div style="display: flex; align-items: center; justify-content: space-between; background-color: var(--bg-surface-subtle); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 0.75rem 1rem; flex-wrap: wrap; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
          <span class="badge ${badgeClass}">${src.source_type}</span>
          <div>
            <div style="font-size: 0.875rem; font-weight: 600; color: var(--text-main);">
              ${src.installed_capacity_kw} kW &bull; <strong class="text-primary">${src.expected_daily_generation_kwh} kWh/day</strong>
            </div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">
              Effective from ${src.effective_from} &bull; ${src.active ? '<span style="color: #10b981; font-weight: 600;">Active</span>' : '<span style="color: #ef4444; font-weight: 600;">Inactive</span>'}
            </div>
          </div>
        </div>
        <div style="display: flex; gap: 0.5rem;">
          <button type="button" class="btn btn-secondary btn-sm" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;" onclick="openEditSourceModal(${src.id})">
            Edit
          </button>
          <button type="button" class="btn btn-secondary btn-sm" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;" onclick="viewSourceHistory(${src.id}, '${src.source_type}')">
            View History
          </button>
          <button type="button" class="btn btn-sm ${src.active ? 'btn-outline' : 'btn-primary'}" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;" onclick="toggleSourceActive(${src.id}, ${!src.active})">
            ${src.active ? 'Deactivate' : 'Activate'}
          </button>
        </div>
      </div>
    `;
  }).join('');
}

async function handleSaveSourceConfig(event) {
  if (event) event.preventDefault();

  const type = document.getElementById('cfg-source-type').value;
  const capacity = parseFloat(document.getElementById('cfg-capacity').value);
  const expGen = parseFloat(document.getElementById('cfg-expected-gen').value);
  const effFrom = document.getElementById('cfg-effective-from').value;

  if (isNaN(capacity) || capacity < 0) {
    UI.showToast('Please enter a valid installed capacity (kW).', 'warning');
    return;
  }
  if (isNaN(expGen) || expGen < 0) {
    UI.showToast('Please enter expected daily generation (kWh/day).', 'warning');
    return;
  }

  const payload = {
    source_type: type,
    installed_capacity_kw: capacity,
    expected_daily_generation_kwh: expGen,
    effective_from: effFrom,
    active: true
  };

  try {
    const btn = document.getElementById('btn-save-source-cfg');
    if (btn) btn.disabled = true;

    await API.post('/sources', payload);
    UI.showToast(`Saved ${type} configuration (${expGen} kWh/day)!`, 'success');
    resetSourceConfigForm();
    await loadConfiguredSources();
    await handleDateOrSourceChange();
  } catch (err) {
    UI.showToast(err.message || 'Failed to save source configuration.', 'error');
  } finally {
    const btn = document.getElementById('btn-save-source-cfg');
    if (btn) btn.disabled = false;
  }
}

function resetSourceConfigForm() {
  document.getElementById('cfg-capacity').value = '';
  document.getElementById('cfg-expected-gen').value = '';
  document.getElementById('cfg-effective-from').value = new Date().toISOString().split('T')[0];
  document.getElementById('cfg-source-type').focus();
}

async function handleDateOrSourceChange() {
  const dateVal = document.getElementById('record-date')?.value || new Date().toISOString().split('T')[0];
  const sourceVal = document.getElementById('record-source')?.value || 'Solar';

  // Look for matching source
  const src = userSources.find(s => s.source_type === sourceVal && s.active);
  let autoGen = 15.0;
  let capVal = 5.0;

  if (src) {
    autoGen = parseFloat(src.expected_daily_generation_kwh || 0);
    capVal = parseFloat(src.installed_capacity_kw || 0);
  } else {
    autoGen = sourceVal === 'Solar' ? 15.0 : 10.0;
    capVal = sourceVal === 'Solar' ? 5.0 : 3.0;
  }

  currentAutoGeneration = autoGen;

  const dispAuto = document.getElementById('display-auto-gen');
  if (dispAuto) dispAuto.textContent = autoGen.toFixed(1);

  const noteEl = document.getElementById('auto-gen-source-note');
  if (noteEl) {
    noteEl.textContent = `Calculated from configured ${sourceVal} (${capVal.toFixed(1)} kW capacity active on ${dateVal})`;
  }

  // Check if override is already recorded on backend for this date/source
  try {
    const telemetry = await API.get('/generation', { date: dateVal });
    const srcTele = (telemetry.sources || []).find(s => s.source_type === sourceVal);
    if (srcTele && srcTele.is_override) {
      document.getElementById('chk-enable-override').checked = true;
      document.getElementById('record-actual-gen').value = srcTele.override_generation_kwh;
      document.getElementById('record-override-reason').value = srcTele.reason || '';
      currentFinalGeneration = parseFloat(srcTele.override_generation_kwh);
    } else {
      document.getElementById('chk-enable-override').checked = false;
      document.getElementById('record-actual-gen').value = autoGen;
      currentFinalGeneration = autoGen;
    }
  } catch (e) {
    currentFinalGeneration = autoGen;
  }

  toggleOverrideFields();
  updateLivePreview();
}

function toggleOverrideFields() {
  const chk = document.getElementById('chk-enable-override');
  const box = document.getElementById('override-fields-box');
  const actualInput = document.getElementById('record-actual-gen');

  const isOverride = chk && chk.checked;
  if (box) box.style.display = isOverride ? 'block' : 'none';

  if (!isOverride && actualInput) {
    actualInput.value = currentAutoGeneration;
  }

  updateLivePreview();
}

function updateLivePreview() {
  const isOverride = document.getElementById('chk-enable-override')?.checked;
  const actualVal = parseFloat(document.getElementById('record-actual-gen')?.value);
  const renVal = parseFloat(document.getElementById('record-ren-con')?.value || 0);
  const storUsedVal = parseFloat(document.getElementById('record-storage-used')?.value || 0);
  const gridVal = parseFloat(document.getElementById('record-grid-con')?.value || 0);
  const tariffVal = parseFloat(document.getElementById('record-tariff')?.value || 9.0);
  const curCode = document.getElementById('record-currency-code')?.value || 'INR';
  const sym = (CURRENCY_INFO[curCode] || {}).symbol || '₹';

  const finalGen = isOverride && !isNaN(actualVal) ? actualVal : currentAutoGeneration;
  currentFinalGeneration = finalGen;

  // Comparison Box Update
  const lblAuto = document.getElementById('lbl-auto-val');
  const lblOv = document.getElementById('lbl-override-val');
  const lblFinal = document.getElementById('lbl-final-val');

  if (lblAuto) lblAuto.textContent = `${currentAutoGeneration.toFixed(1)} kWh`;
  if (lblOv) lblOv.textContent = isOverride ? `${finalGen.toFixed(1)} kWh` : 'None';
  if (lblFinal) lblFinal.textContent = `${finalGen.toFixed(1)} kWh`;

  // Live Storage & Surplus Calculations
  const surplusVal = Math.max(0, finalGen - renVal);
  const totalAvailable = currentStorageBalance + surplusVal;
  const remainingStorage = Math.max(0, totalAvailable - storUsedVal);

  // Update Section 5 Live Formula
  const fPrev = document.getElementById('calc-lbl-prev');
  const fGen = document.getElementById('calc-lbl-gen');
  const fRen = document.getElementById('calc-lbl-ren');
  const fSurp = document.getElementById('calc-lbl-surplus');
  const fRem = document.getElementById('lbl-rem-storage-calc');

  if (fPrev) fPrev.textContent = currentStorageBalance.toFixed(1);
  if (fGen) fGen.textContent = finalGen.toFixed(1);
  if (fRen) fRen.textContent = renVal.toFixed(1);
  if (fSurp) fSurp.textContent = surplusVal > 0 ? `+${surplusVal.toFixed(1)}` : '0.0';
  if (fRem) fRem.textContent = `${remainingStorage.toFixed(1)} kWh`;

  // Live Calculations Right Preview Card
  const totalCleanUsed = renVal + storUsedVal;
  const totalConsumed = totalCleanUsed + gridVal;
  const renPct = totalConsumed > 0 ? Math.min(Math.round((totalCleanUsed / totalConsumed) * 1000) / 10, 100) : 0;
  const co2Avoided = (totalCleanUsed * CONFIG.DEFAULT_GRID_EMISSION_FACTOR).toFixed(2);
  const costSavings = (totalCleanUsed * tariffVal).toFixed(2);

  const elPrevGen = document.getElementById('preview-gen-val');
  if (elPrevGen) elPrevGen.textContent = `${finalGen.toFixed(1)} kWh`;

  const elPrevRen = document.getElementById('preview-ren-con-val');
  if (elPrevRen) elPrevRen.textContent = `${renVal.toFixed(1)} kWh`;

  const elPrevSurp = document.getElementById('preview-surplus-val');
  if (elPrevSurp) elPrevSurp.textContent = surplusVal > 0 ? `+${surplusVal.toFixed(1)} kWh` : '0.0 kWh';

  const elPrevStorUsed = document.getElementById('preview-stor-used-val');
  if (elPrevStorUsed) elPrevStorUsed.textContent = `${storUsedVal.toFixed(1)} kWh`;

  const elPrevRemStor = document.getElementById('preview-rem-storage');
  if (elPrevRemStor) elPrevRemStor.textContent = `${remainingStorage.toFixed(1)} kWh`;

  const elTot = document.getElementById('preview-total-consumed');
  if (elTot) elTot.textContent = `${totalConsumed.toFixed(1)} kWh`;

  const elPct = document.getElementById('preview-ren-pct');
  if (elPct) elPct.textContent = `${renPct}%`;

  const elCo2 = document.getElementById('preview-co2');
  if (elCo2) elCo2.textContent = `${co2Avoided} kg CO2`;

  const elSav = document.getElementById('preview-savings');
  if (elSav) elSav.textContent = `${sym}${parseFloat(costSavings).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const elRate = document.getElementById('preview-rate-label');
  if (elRate) elRate.textContent = `${sym}${tariffVal.toFixed(2)}`;
}

async function handleSaveEnergyRecord(event, addAnother = false) {
  if (event) event.preventDefault();

  const dateVal = document.getElementById('record-date').value;
  const sourceVal = document.getElementById('record-source').value;
  const isOverride = document.getElementById('chk-enable-override').checked;
  const actualVal = parseFloat(document.getElementById('record-actual-gen').value);
  const reasonVal = document.getElementById('record-override-reason').value;
  const renVal = parseFloat(document.getElementById('record-ren-con').value);
  const storUsedVal = parseFloat(document.getElementById('record-storage-used').value || 0);
  const gridVal = parseFloat(document.getElementById('record-grid-con').value || 0);
  const tariffVal = parseFloat(document.getElementById('record-tariff').value || 9.0);
  const notesVal = document.getElementById('record-notes').value;

  if (!dateVal) {
    UI.showToast('Please select a valid date.', 'warning');
    return;
  }
  if (isNaN(renVal) || renVal < 0) {
    UI.showToast('Please enter renewable energy consumed (kWh).', 'warning');
    return;
  }

  const finalGen = isOverride && !isNaN(actualVal) ? actualVal : currentAutoGeneration;
  const surplusVal = Math.max(0, finalGen - renVal);
  const totalAvailableStorage = currentStorageBalance + surplusVal;

  if (storUsedVal > totalAvailableStorage) {
    UI.showToast(`Cannot dispatch ${storUsedVal.toFixed(1)} kWh. Available storage balance is ${totalAvailableStorage.toFixed(1)} kWh.`, 'error');
    return;
  }

  const matchedSrc = userSources.find(s => s.source_type === sourceVal && s.active);

  // If override enabled, sync override first
  if (isOverride && matchedSrc) {
    try {
      await API.post('/generation/overrides', {
        date: dateVal,
        source_id: matchedSrc.id,
        override_generation_kwh: finalGen,
        automatic_generation_kwh: currentAutoGeneration,
        reason: reasonVal || 'Manual weather override'
      });
    } catch (e) {
      console.warn('Override sync warning:', e);
    }
  }

  const payload = {
    date: dateVal,
    renewable_source: sourceVal,
    source_id: matchedSrc ? matchedSrc.id : null,
    energy_generated_kwh: finalGen,
    renewable_energy_consumed_kwh: renVal,
    storage_used_kwh: storUsedVal,
    grid_energy_consumed_kwh: isNaN(gridVal) ? 0 : gridVal,
    is_override: isOverride,
    automatic_generation_kwh: currentAutoGeneration,
    override_generation_kwh: isOverride ? finalGen : null,
    electricity_tariff: tariffVal,
    notes: notesVal
  };

  try {
    const saveBtn = document.getElementById('btn-save-record');
    const saveAnotherBtn = document.getElementById('btn-save-another');
    if (saveBtn) saveBtn.disabled = true;
    if (saveAnotherBtn) saveAnotherBtn.disabled = true;

    await API.post('/energy', payload);
    UI.showToast(`Saved ${sourceVal} record for ${dateVal} successfully!`, 'success');
    await loadStorageBalance();

    if (addAnother) {
      document.getElementById('record-ren-con').value = '';
      document.getElementById('record-storage-used').value = '0.0';
      document.getElementById('record-grid-con').value = '0.0';
      document.getElementById('record-notes').value = '';
      document.getElementById('record-source').focus();
      updateLivePreview();
    } else {
      setTimeout(() => {
        window.location.href = 'records.html';
      }, 500);
    }
  } catch (err) {
    UI.showToast(err.message || 'Failed to save energy record.', 'error');
  } finally {
    const saveBtn = document.getElementById('btn-save-record');
    const saveAnotherBtn = document.getElementById('btn-save-another');
    if (saveBtn) saveBtn.disabled = false;
    if (saveAnotherBtn) saveAnotherBtn.disabled = false;
  }
}

// Modal: Edit Source Configuration
function openEditSourceModal(sourceId) {
  const src = userSources.find(s => s.id === sourceId);
  if (!src) return;

  document.getElementById('edit-source-id').value = src.id;
  document.getElementById('edit-source-type').value = src.source_type;
  document.getElementById('edit-capacity').value = src.installed_capacity_kw;
  document.getElementById('edit-expected-gen').value = src.expected_daily_generation_kwh;
  document.getElementById('edit-effective-from').value = new Date().toISOString().split('T')[0];
  document.getElementById('edit-source-active').checked = src.active;

  UI.openModal('edit-source-modal');
}

async function handleSaveEditedSource(event) {
  if (event) event.preventDefault();

  const id = parseInt(document.getElementById('edit-source-id').value);
  const type = document.getElementById('edit-source-type').value;
  const cap = parseFloat(document.getElementById('edit-capacity').value);
  const expGen = parseFloat(document.getElementById('edit-expected-gen').value);
  const effFrom = document.getElementById('edit-effective-from').value;
  const active = document.getElementById('edit-source-active').checked;

  try {
    await API.put(`/sources/${id}`, {
      source_type: type,
      installed_capacity_kw: cap,
      expected_daily_generation_kwh: expGen,
      effective_from: effFrom,
      active: active
    });
    UI.closeModal('edit-source-modal');
    UI.showToast(`Updated ${type} source configuration with historical preservation!`, 'success');
    await loadConfiguredSources();
    await handleDateOrSourceChange();
  } catch (err) {
    UI.showToast(err.message || 'Failed to update source configuration.', 'error');
  }
}

async function toggleSourceActive(sourceId, newStatus) {
  try {
    await API.put(`/sources/${sourceId}`, { active: newStatus });
    UI.showToast(`Source ${newStatus ? 'activated' : 'deactivated'} successfully.`, 'info');
    await loadConfiguredSources();
    await handleDateOrSourceChange();
  } catch (err) {
    UI.showToast(err.message || 'Failed to update source status.', 'error');
  }
}

// Modal: View Source Capacity History
async function viewSourceHistory(sourceId, sourceName) {
  const nameSpan = document.getElementById('hist-source-name');
  if (nameSpan) nameSpan.textContent = sourceName;

  const tbody = document.getElementById('source-history-tbody');
  if (tbody) tbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">Loading history...</td></tr>`;

  UI.openModal('source-history-modal');

  try {
    const res = await API.get(`/sources/${sourceId}/history`);
    const list = res.history || [];
    if (!list.length) {
      tbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">No historical changes logged.</td></tr>`;
      return;
    }

    tbody.innerHTML = list.map(h => `
      <tr>
        <td><strong>${h.effective_from}</strong> &rarr; ${h.effective_to ? h.effective_to : 'Present (Ongoing)'}</td>
        <td><span class="font-semibold">${h.capacity_kw} kW</span></td>
        <td><strong class="text-primary">${h.expected_daily_generation_kwh} kWh/day</strong></td>
      </tr>
    `).join('');
  } catch (err) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="3" class="text-danger text-center">Failed to load history.</td></tr>`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('source-config-form')) {
    initAddEnergyPage();
  }
});
