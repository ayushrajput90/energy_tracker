/**
 * Standalone Sample Data for DEMO_MODE
 * Stores sample data in localStorage to enable realistic offline interactive demos.
 */

const DEMO_SEED_DATA = {
  user: {
    id: 1,
    full_name: 'Dr. Sarah Green',
    email: 'sarah.green@ecouniversity.edu',
    created_at: '2026-08-01T08:00:00Z'
  },
  settings: {
    id: 1,
    user_id: 1,
    electricity_tariff: 9.0, // ₹9/kWh (INR) or configurable
    currency_code: 'INR',
    currency_symbol: '₹',
    co2_emission_factor: 0.82,
    theme: 'light',
    notification_preferences: true,
    unit_preference: 'kWh'
  },
  // Configured Renewable Sources
  sources: [
    {
      id: 1,
      user_id: 1,
      source_type: 'Solar',
      installed_capacity_kw: 5.0,
      expected_daily_generation_kwh: 15.0,
      effective_from: '2026-08-01',
      active: true,
      created_at: '2026-08-01T08:00:00Z',
      updated_at: '2026-08-01T08:00:00Z'
    },
    {
      id: 2,
      user_id: 1,
      source_type: 'Wind',
      installed_capacity_kw: 3.0,
      expected_daily_generation_kwh: 10.0,
      effective_from: '2026-08-01',
      active: true,
      created_at: '2026-08-01T08:00:00Z',
      updated_at: '2026-08-01T08:00:00Z'
    },
    {
      id: 3,
      user_id: 1,
      source_type: 'Hydro',
      installed_capacity_kw: 2.0,
      expected_daily_generation_kwh: 8.0,
      effective_from: '2026-08-01',
      active: true,
      created_at: '2026-08-01T08:00:00Z',
      updated_at: '2026-08-01T08:00:00Z'
    }
  ],
  // Source Capacity History
  capacity_history: [
    {
      id: 1,
      source_id: 1,
      capacity_kw: 5.0,
      expected_daily_generation_kwh: 15.0,
      effective_from: '2026-08-01',
      effective_to: null,
      created_at: '2026-08-01T08:00:00Z'
    },
    {
      id: 2,
      source_id: 2,
      capacity_kw: 3.0,
      expected_daily_generation_kwh: 10.0,
      effective_from: '2026-08-01',
      effective_to: null,
      created_at: '2026-08-01T08:00:00Z'
    },
    {
      id: 3,
      source_id: 3,
      capacity_kw: 2.0,
      expected_daily_generation_kwh: 8.0,
      effective_from: '2026-08-01',
      effective_to: null,
      created_at: '2026-08-01T08:00:00Z'
    }
  ],
  // Daily Generation Overrides
  overrides: [
    {
      id: 1,
      user_id: 1,
      source_id: 1,
      date: '2026-08-20',
      automatic_generation_kwh: 15.0,
      override_generation_kwh: 6.0,
      reason: 'Heavy rain & overcast skies',
      created_at: '2026-08-20T08:00:00Z'
    }
  ],
  // Energy Storage Ledger Transactions
  storage_transactions: [
    { id: 1, user_id: 1, date: '2026-08-18', transaction_type: 'SURPLUS', amount_kwh: 5.0, notes: 'Surplus energy stored from Solar generation', created_at: '2026-08-18T18:00:00Z' },
    { id: 2, user_id: 1, date: '2026-08-19', transaction_type: 'SURPLUS', amount_kwh: 8.0, notes: 'Surplus energy stored from Wind generation', created_at: '2026-08-19T18:00:00Z' }
  ],
  // Energy records preserving individual row independence
  records: [
    // 18 August Test Scenario (6 separate records!)
    { id: 1, user_id: 1, date: '2026-08-18', renewable_source: 'Solar', energy_generated_kwh: 10.0, renewable_energy_consumed_kwh: 8.0, grid_energy_consumed_kwh: 2.0, storage_used_kwh: 0.0, surplus_kwh: 2.0, storage_balance_kwh: 2.0, is_override: false, electricity_tariff: 9.0, notes: 'Rooftop Array 1 (Morning)' },
    { id: 2, user_id: 1, date: '2026-08-18', renewable_source: 'Solar', energy_generated_kwh: 5.0, renewable_energy_consumed_kwh: 4.0, grid_energy_consumed_kwh: 1.0, storage_used_kwh: 0.0, surplus_kwh: 1.0, storage_balance_kwh: 3.0, is_override: false, electricity_tariff: 9.0, notes: 'Bifacial Ground Mount' },
    { id: 3, user_id: 1, date: '2026-08-18', renewable_source: 'Wind', energy_generated_kwh: 10.0, renewable_energy_consumed_kwh: 8.0, grid_energy_consumed_kwh: 2.0, storage_used_kwh: 0.0, surplus_kwh: 2.0, storage_balance_kwh: 5.0, is_override: false, electricity_tariff: 9.0, notes: 'Micro Turbine North' },
    { id: 4, user_id: 1, date: '2026-08-18', renewable_source: 'Biomass', energy_generated_kwh: 10.0, renewable_energy_consumed_kwh: 7.0, grid_energy_consumed_kwh: 3.0, storage_used_kwh: 0.0, surplus_kwh: 3.0, storage_balance_kwh: 8.0, is_override: false, electricity_tariff: 9.0, notes: 'Pellet Gasifier System' },
    { id: 5, user_id: 1, date: '2026-08-18', renewable_source: 'Hydro', energy_generated_kwh: 10.0, renewable_energy_consumed_kwh: 9.0, grid_energy_consumed_kwh: 1.0, storage_used_kwh: 0.0, surplus_kwh: 1.0, storage_balance_kwh: 9.0, is_override: false, electricity_tariff: 9.0, notes: 'Microhydro Stream Turbine' },
    { id: 6, user_id: 1, date: '2026-08-18', renewable_source: 'Geothermal', energy_generated_kwh: 10.0, renewable_energy_consumed_kwh: 10.0, grid_energy_consumed_kwh: 0.0, storage_used_kwh: 0.0, surplus_kwh: 0.0, storage_balance_kwh: 9.0, is_override: false, electricity_tariff: 9.0, notes: 'Closed Loop Heat Pump' },
    
    // 19 August Records
    { id: 7, user_id: 1, date: '2026-08-19', renewable_source: 'Solar', energy_generated_kwh: 20.0, renewable_energy_consumed_kwh: 15.0, grid_energy_consumed_kwh: 5.0, storage_used_kwh: 0.0, surplus_kwh: 5.0, storage_balance_kwh: 14.0, is_override: false, electricity_tariff: 9.0, notes: 'Full Sunshine Output' },
    { id: 8, user_id: 1, date: '2026-08-19', renewable_source: 'Wind', energy_generated_kwh: 15.0, renewable_energy_consumed_kwh: 12.0, grid_energy_consumed_kwh: 3.0, storage_used_kwh: 0.0, surplus_kwh: 3.0, storage_balance_kwh: 17.0, is_override: false, electricity_tariff: 9.0, notes: 'Windy Evening Gusts' },

    // 20 August Record (With Manual Weather Override)
    { id: 9, user_id: 1, date: '2026-08-20', renewable_source: 'Solar', energy_generated_kwh: 6.0, renewable_energy_consumed_kwh: 5.0, grid_energy_consumed_kwh: 0.0, storage_used_kwh: 2.0, surplus_kwh: 1.0, storage_balance_kwh: 16.0, is_override: true, override_generation_kwh: 6.0, automatic_generation_kwh: 15.0, electricity_tariff: 9.0, notes: 'Heavy rain override & consumed 2 kWh from battery storage' }
  ],
  goals: [
    {
      id: 1,
      user_id: 1,
      goal_type: 'Energy Generation',
      target_value: 200.0,
      start_date: '2026-08-01',
      end_date: '2026-08-31',
      description: 'August 200 kWh Clean Generation Milestone',
      status: 'Active'
    },
    {
      id: 2,
      user_id: 1,
      goal_type: 'Renewable Percentage',
      target_value: 80.0,
      start_date: '2026-08-01',
      end_date: '2026-08-31',
      description: 'Achieve 80% Clean Grid Independence',
      status: 'Active'
    },
    {
      id: 3,
      user_id: 1,
      goal_type: 'Cost Savings',
      target_value: 1500.0,
      start_date: '2026-08-01',
      end_date: '2026-08-31',
      description: 'Save ₹1,500 on Monthly Electricity Bills',
      status: 'Active'
    }
  ],
  activities: [
    { id: 1, user_id: 1, action_type: 'LOGIN', description: 'User signed into Renewable Energy Usage Tracker', timestamp: new Date().toISOString() },
    { id: 2, user_id: 1, action_type: 'CONFIG_SOURCE', description: 'Configured Solar (5 kW, 15 kWh/day) and Wind (3 kW, 10 kWh/day)', timestamp: new Date(Date.now() - 3600000).toISOString() },
    { id: 3, user_id: 1, action_type: 'GENERATION_OVERRIDE', description: 'Applied weather override for Solar on 2026-08-20: 6.0 kWh (Heavy rain)', timestamp: new Date(Date.now() - 7200000).toISOString() },
    { id: 4, user_id: 1, action_type: 'ADD_RECORD', description: 'Recorded 2026-08-20 consumption with 1.0 kWh surplus added to storage', timestamp: new Date(Date.now() - 10800000).toISOString() }
  ]
};

// Initialize Demo Data in localStorage if missing or reset
function initDemoStorage() {
  if (!localStorage.getItem('DEMO_RECORDS')) {
    localStorage.setItem('DEMO_RECORDS', JSON.stringify(DEMO_SEED_DATA.records));
  }
  if (!localStorage.getItem('DEMO_SOURCES')) {
    localStorage.setItem('DEMO_SOURCES', JSON.stringify(DEMO_SEED_DATA.sources));
  }
  if (!localStorage.getItem('DEMO_CAPACITY_HISTORY')) {
    localStorage.setItem('DEMO_CAPACITY_HISTORY', JSON.stringify(DEMO_SEED_DATA.capacity_history));
  }
  if (!localStorage.getItem('DEMO_OVERRIDES')) {
    localStorage.setItem('DEMO_OVERRIDES', JSON.stringify(DEMO_SEED_DATA.overrides));
  }
  if (!localStorage.getItem('DEMO_STORAGE_TXS')) {
    localStorage.setItem('DEMO_STORAGE_TXS', JSON.stringify(DEMO_SEED_DATA.storage_transactions));
  }
  if (!localStorage.getItem('DEMO_GOALS')) {
    localStorage.setItem('DEMO_GOALS', JSON.stringify(DEMO_SEED_DATA.goals));
  }
  if (!localStorage.getItem('DEMO_ACTIVITIES')) {
    localStorage.setItem('DEMO_ACTIVITIES', JSON.stringify(DEMO_SEED_DATA.activities));
  }
  if (!localStorage.getItem('DEMO_SETTINGS')) {
    localStorage.setItem('DEMO_SETTINGS', JSON.stringify(DEMO_SEED_DATA.settings));
  }
}

if (typeof window !== 'undefined') {
  window.DEMO_SEED_DATA = DEMO_SEED_DATA;
  window.initDemoStorage = initDemoStorage;
}
