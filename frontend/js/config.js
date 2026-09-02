/**
 * Renewable Energy Usage Tracker - Global Configuration
 */
const CONFIG = {
  // If frontend is served directly by Flask on port 5000, use relative '/api', else use full URL
  API_BASE_URL: (window.location.port === '5000' || window.location.port === '') && window.location.hostname !== 'localhost' && window.location.protocol.startsWith('http')
    ? '/api'
    : 'http://127.0.0.1:5000/api',

  // DEMO MODE TOGGLE:
  // When true: uses sample data and frontend state simulation
  // When false: connects to live Flask REST API & MySQL
  DEMO_MODE: localStorage.getItem('DEMO_MODE') === 'true',

  DEFAULT_TARIFF: 9.0, // Tariff per kWh (Default 9 for INR, or configurable)
  DEFAULT_GRID_EMISSION_FACTOR: 0.82, // kg CO2/kWh
  DEFAULT_CURRENCY_CODE: 'INR',
  DEFAULT_CURRENCY_SYMBOL: '₹',

  SUPPORTED_CURRENCIES: [
    { code: 'INR', symbol: '₹', name: 'Indian Rupee (INR ₹)', defaultTariff: 9.0 },
    { code: 'USD', symbol: '$', name: 'US Dollar (USD $)', defaultTariff: 0.12 },
    { code: 'EUR', symbol: '€', name: 'Euro (EUR €)', defaultTariff: 0.20 },
    { code: 'GBP', symbol: '£', name: 'British Pound (GBP £)', defaultTariff: 0.18 }
  ],
  
  RENEWABLE_SOURCES: [
    'Solar',
    'Wind',
    'Hydro',
    'Biomass',
    'Geothermal',
    'Other Renewable'
  ],

  SOURCE_COLORS: {
    'Solar': '#f59e0b',
    'Wind': '#06b6d4',
    'Hydro': '#3b82f6',
    'Biomass': '#84cc16',
    'Geothermal': '#f97316',
    'Other Renewable': '#8b5cf6'
  },

  getCurrencySymbol() {
    try {
      const userSettings = JSON.parse(localStorage.getItem('user_settings') || '{}');
      return userSettings.currency_symbol || this.DEFAULT_CURRENCY_SYMBOL;
    } catch (e) {
      return this.DEFAULT_CURRENCY_SYMBOL;
    }
  },

  getCurrencyCode() {
    try {
      const userSettings = JSON.parse(localStorage.getItem('user_settings') || '{}');
      return userSettings.currency_code || this.DEFAULT_CURRENCY_CODE;
    } catch (e) {
      return this.DEFAULT_CURRENCY_CODE;
    }
  },

  getTariff() {
    try {
      const userSettings = JSON.parse(localStorage.getItem('user_settings') || '{}');
      if (userSettings.electricity_tariff !== undefined && userSettings.electricity_tariff !== null) {
        return parseFloat(userSettings.electricity_tariff);
      }
      return this.DEFAULT_TARIFF;
    } catch (e) {
      return this.DEFAULT_TARIFF;
    }
  },

  formatCurrency(value, customSymbol = null) {
    const sym = customSymbol || this.getCurrencySymbol();
    const num = parseFloat(value) || 0;
    return `${sym}${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  },

  setDemoMode(enabled) {
    localStorage.setItem('DEMO_MODE', enabled ? 'true' : 'false');
    this.DEMO_MODE = enabled;
    window.location.reload();
  }
};

if (typeof window !== 'undefined') {
  window.CONFIG = CONFIG;
}
