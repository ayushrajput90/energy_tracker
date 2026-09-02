/**
 * Application Settings & Preferences Manager
 */

const CURRENCY_MAP = {
  'INR': { symbol: '₹', defaultTariff: 9.0 },
  'USD': { symbol: '$', defaultTariff: 0.12 },
  'EUR': { symbol: '€', defaultTariff: 0.20 },
  'GBP': { symbol: '£', defaultTariff: 0.18 }
};

async function loadAppSettings() {
  try {
    const data = await API.get('/settings');
    const s = data.settings || {};

    const elCode = document.getElementById('setting-currency-code');
    const curCode = s.currency_code || CONFIG.DEFAULT_CURRENCY_CODE;
    if (elCode) elCode.value = curCode;

    const sym = (CURRENCY_MAP[curCode] || {}).symbol || s.currency_symbol || '₹';
    const label = document.getElementById('setting-tariff-currency-label');
    if (label) label.textContent = sym;

    const elTariff = document.getElementById('setting-tariff');
    if (elTariff) elTariff.value = s.electricity_tariff !== undefined ? s.electricity_tariff : (CURRENCY_MAP[curCode]?.defaultTariff || 9.0);

    const elFactor = document.getElementById('setting-factor');
    if (elFactor) elFactor.value = s.co2_emission_factor || CONFIG.DEFAULT_GRID_EMISSION_FACTOR;

    const elTheme = document.getElementById('setting-theme');
    if (elTheme) elTheme.value = s.theme || localStorage.getItem('app_theme') || 'light';

    const elNotif = document.getElementById('setting-notifications');
    if (elNotif) elNotif.checked = s.notification_preferences !== false;

    const elUnit = document.getElementById('setting-unit');
    if (elUnit) elUnit.value = s.unit_preference || 'kWh';

    const elDemoStatus = document.getElementById('demo-mode-status-text');
    if (elDemoStatus) {
      elDemoStatus.textContent = CONFIG.DEMO_MODE ? 'Demo Mode Active (Client-Side Simulation)' : 'Live Connected Mode (Flask REST API)';
    }
  } catch (err) {
    console.error('Failed to load settings:', err);
    UI.showToast('Could not load application settings.', 'error');
  }
}

function handleCurrencyChange() {
  const code = document.getElementById('setting-currency-code').value;
  const info = CURRENCY_MAP[code] || { symbol: '₹', defaultTariff: 9.0 };
  const label = document.getElementById('setting-tariff-currency-label');
  if (label) label.textContent = info.symbol;

  const tariffInput = document.getElementById('setting-tariff');
  // If user switches currency and tariff is empty or 0, suggest standard tariff
  if (tariffInput && (!tariffInput.value || parseFloat(tariffInput.value) === 0)) {
    tariffInput.value = info.defaultTariff;
  }
}

async function handleSaveSettings(event) {
  event.preventDefault();
  const code = document.getElementById('setting-currency-code').value;
  const info = CURRENCY_MAP[code] || { symbol: '₹' };

  const payload = {
    currency_code: code,
    currency_symbol: info.symbol,
    electricity_tariff: parseFloat(document.getElementById('setting-tariff').value),
    co2_emission_factor: parseFloat(document.getElementById('setting-factor').value),
    theme: document.getElementById('setting-theme').value,
    notification_preferences: document.getElementById('setting-notifications').checked,
    unit_preference: document.getElementById('setting-unit').value
  };

  try {
    const res = await API.put('/settings', payload);
    localStorage.setItem('user_settings', JSON.stringify(res.settings));
    if (payload.theme) {
      document.documentElement.setAttribute('data-theme', payload.theme);
      localStorage.setItem('app_theme', payload.theme);
    }
    UI.showToast('Application preferences saved successfully!', 'success');
  } catch (err) {
    UI.showToast(err.message || 'Failed to update preferences.', 'error');
  }
}

function toggleDemoModeFromSettings() {
  CONFIG.setDemoMode(!CONFIG.DEMO_MODE);
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('settings-form')) {
    loadAppSettings();
  }
});
