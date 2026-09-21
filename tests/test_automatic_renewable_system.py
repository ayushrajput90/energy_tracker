import pytest
from datetime import date
from backend.app import create_app
from backend.config import Config
from backend.extensions import db
from backend.models.user import User
from backend.models.user_settings import UserSettings
from backend.models.renewable_source import RenewableSource, SourceCapacityHistory
from backend.models.generation_override import DailyGenerationOverride
from backend.models.storage_transaction import RenewableStorageTransaction
from backend.models.energy_record import EnergyRecord
from backend.services.calculations import (
    calculate_surplus,
    calculate_storage_balance,
    calculate_total_energy_consumed,
    calculate_renewable_percentage,
    calculate_co2_avoided,
    calculate_cost_savings
)
from backend.services.aggregation import calculate_user_storage_balance, get_daily_generation_telemetry

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_SECRET_KEY = 'test-jwt-secret-key-that-is-sufficiently-long-for-hmac-sha256'

@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        user = User()
        user.full_name = 'Test Solar Engineer'
        user.email = 'engineer@renewable.org'
        user.set_password('CleanEnergyPass123!')
        db.session.add(user)
        db.session.commit()

        settings = UserSettings()
        settings.user_id = user.id
        settings.electricity_tariff = 9.0
        settings.currency_code = 'INR'
        settings.currency_symbol = '₹'
        settings.co2_emission_factor = 0.82
        db.session.add(settings)
        db.session.commit()

        with app.test_client() as test_client:
            # Login to get JWT
            res = test_client.post('/api/auth/login', json={
                'email': 'engineer@renewable.org',
                'password': 'CleanEnergyPass123!'
            })
            token = res.get_json()['access_token']
            test_client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {token}'
            test_client.user_id = user.id
            yield test_client

        db.session.remove()
        db.drop_all()


# -------------------------------------------------------------
# 1. Source creation (Solar, Wind, Hydro, Biomass, Geothermal, Other)
# -------------------------------------------------------------
def test_01_source_creation_all_types(client):
    sources = ['Solar', 'Wind', 'Hydro', 'Biomass', 'Geothermal', 'Other Renewable']
    for idx, src_type in enumerate(sources, start=1):
        res = client.post('/api/sources', json={
            'source_type': src_type,
            'installed_capacity_kw': float(idx * 2),
            'expected_daily_generation_kwh': float(idx * 5),
            'effective_from': '2026-08-01'
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data['source']['source_type'] == src_type
        assert data['source']['installed_capacity_kw'] == float(idx * 2)

    # Verify listing
    res_list = client.get('/api/sources')
    assert res_list.status_code == 200
    assert len(res_list.get_json()['sources']) == 6


# -------------------------------------------------------------
# 2. Capacity tracking
# -------------------------------------------------------------
def test_02_capacity_tracking(client):
    res = client.post('/api/sources', json={
        'source_type': 'Solar',
        'installed_capacity_kw': 5.0,
        'expected_daily_generation_kwh': 15.0,
        'effective_from': '2026-08-01'
    })
    src_id = res.get_json()['source']['id']

    # Update capacity to 8 kW
    res_up = client.put(f'/api/sources/{src_id}', json={
        'installed_capacity_kw': 8.0,
        'expected_daily_generation_kwh': 24.0,
        'effective_from': '2026-08-15'
    })
    assert res_up.status_code == 200
    assert res_up.get_json()['source']['installed_capacity_kw'] == 8.0


# -------------------------------------------------------------
# 3. Expected generation calculation
# -------------------------------------------------------------
def test_03_expected_generation_calculation(client):
    client.post('/api/sources', json={
        'source_type': 'Solar',
        'installed_capacity_kw': 5.0,
        'expected_daily_generation_kwh': 15.0,
        'effective_from': '2026-08-01'
    })
    client.post('/api/sources', json={
        'source_type': 'Wind',
        'installed_capacity_kw': 3.0,
        'expected_daily_generation_kwh': 10.0,
        'effective_from': '2026-08-01'
    })

    res = client.get('/api/sources')
    data = res.get_json()
    assert data['total_expected_daily_generation_kwh'] == 25.0
    assert data['total_installed_capacity_kw'] == 8.0


# -------------------------------------------------------------
# 4. Date-effective changes & 5. Historical data preservation
# -------------------------------------------------------------
def test_04_05_date_effective_and_historical_preservation(client):
    res = client.post('/api/sources', json={
        'source_type': 'Solar',
        'installed_capacity_kw': 5.0,
        'expected_daily_generation_kwh': 15.0,
        'effective_from': '2026-08-01'
    })
    src_id = res.get_json()['source']['id']

    # Change on 2026-08-20: Solar upgraded to 10 kW / 30 kWh/day
    client.put(f'/api/sources/{src_id}', json={
        'installed_capacity_kw': 10.0,
        'expected_daily_generation_kwh': 30.0,
        'effective_from': '2026-08-20'
    })

    # Telemetry for Aug 10 (before upgrade) -> should yield 15.0 kWh
    t_past = client.get('/api/generation?date=2026-08-10').get_json()
    assert t_past['total_automatic_generation_kwh'] == 15.0

    # Telemetry for Aug 22 (after upgrade) -> should yield 30.0 kWh
    t_future = client.get('/api/generation?date=2026-08-22').get_json()
    assert t_future['total_automatic_generation_kwh'] == 30.0

    # Check history log endpoint
    hist_res = client.get(f'/api/sources/{src_id}/history')
    assert len(hist_res.get_json()['history']) == 2


# -------------------------------------------------------------
# 6. Daily override creation & 7. Reason recording
# -------------------------------------------------------------
def test_06_07_daily_override_and_reason(client):
    res_src = client.post('/api/sources', json={
        'source_type': 'Solar',
        'installed_capacity_kw': 5.0,
        'expected_daily_generation_kwh': 15.0,
        'effective_from': '2026-08-01'
    })
    src_id = res_src.get_json()['source']['id']

    res_ov = client.post('/api/generation/overrides', json={
        'date': '2026-08-20',
        'source_id': src_id,
        'override_generation_kwh': 6.0,
        'reason': 'Heavy monsoon downpour'
    })
    assert res_ov.status_code == 201
    ov_data = res_ov.get_json()['override']
    assert ov_data['override_generation_kwh'] == 6.0
    assert ov_data['reason'] == 'Heavy monsoon downpour'
    assert ov_data['automatic_generation_kwh'] == 15.0


# -------------------------------------------------------------
# 8. Override editing
# -------------------------------------------------------------
def test_08_override_editing(client):
    res_src = client.post('/api/sources', json={
        'source_type': 'Solar',
        'installed_capacity_kw': 5.0,
        'expected_daily_generation_kwh': 15.0,
        'effective_from': '2026-08-01'
    })
    src_id = res_src.get_json()['source']['id']

    res_ov = client.post('/api/generation/overrides', json={
        'date': '2026-08-20',
        'source_id': src_id,
        'override_generation_kwh': 6.0,
        'reason': 'Heavy monsoon downpour'
    })
    ov_id = res_ov.get_json()['override']['id']

    # Edit override to 8.0 kWh
    res_edit = client.put(f'/api/generation/overrides/{ov_id}', json={
        'override_generation_kwh': 8.0,
        'reason': 'Afternoon sun broke through'
    })
    assert res_edit.status_code == 200
    assert res_edit.get_json()['override']['override_generation_kwh'] == 8.0


# -------------------------------------------------------------
# 9. Override deletion & 10. Automatic generation restoration
# -------------------------------------------------------------
def test_09_10_override_deletion_and_restoration(client):
    res_src = client.post('/api/sources', json={
        'source_type': 'Solar',
        'installed_capacity_kw': 5.0,
        'expected_daily_generation_kwh': 15.0,
        'effective_from': '2026-08-01'
    })
    src_id = res_src.get_json()['source']['id']

    res_ov = client.post('/api/generation/overrides', json={
        'date': '2026-08-20',
        'source_id': src_id,
        'override_generation_kwh': 6.0,
        'reason': 'Heavy monsoon downpour'
    })
    ov_id = res_ov.get_json()['override']['id']

    # Telemetry should reflect override (6.0 kWh)
    t_before = client.get('/api/generation?date=2026-08-20').get_json()
    assert t_before['total_final_generation_kwh'] == 6.0
    assert t_before['has_override'] is True

    # Delete override
    del_res = client.delete(f'/api/generation/overrides/{ov_id}')
    assert del_res.status_code == 200

    # Telemetry should now automatically restore to 15.0 kWh
    t_after = client.get('/api/generation?date=2026-08-20').get_json()
    assert t_after['total_final_generation_kwh'] == 15.0
    assert t_after['has_override'] is False


# -------------------------------------------------------------
# 11. Multi-source daily combined view & 12. Source-wise view
# -------------------------------------------------------------
def test_11_12_multisource_combined_and_sourcewise_views(client):
    client.post('/api/sources', json={'source_type': 'Solar', 'installed_capacity_kw': 5.0, 'expected_daily_generation_kwh': 15.0, 'effective_from': '2026-08-01'})
    client.post('/api/sources', json={'source_type': 'Wind', 'installed_capacity_kw': 3.0, 'expected_daily_generation_kwh': 10.0, 'effective_from': '2026-08-01'})

    res = client.get('/api/generation?date=2026-08-18')
    assert res.status_code == 200
    data = res.get_json()

    # Combined view
    assert data['total_automatic_generation_kwh'] == 25.0
    assert data['total_final_generation_kwh'] == 25.0

    # Source-wise view
    assert len(data['sources']) == 2
    sources_dict = {s['source_type']: s['final_generation_kwh'] for s in data['sources']}
    assert sources_dict['Solar'] == 15.0
    assert sources_dict['Wind'] == 10.0


# -------------------------------------------------------------
# 13-16. Day, Week, Month, Year Aggregations
# -------------------------------------------------------------
def test_13_to_16_period_aggregations(client):
    # Add records for multiple days
    client.post('/api/energy', json={'date': '2026-08-18', 'renewable_source': 'Solar', 'energy_generated_kwh': 15.0, 'renewable_energy_consumed_kwh': 10.0, 'grid_energy_consumed_kwh': 2.0})
    client.post('/api/energy', json={'date': '2026-08-19', 'renewable_source': 'Wind', 'energy_generated_kwh': 10.0, 'renewable_energy_consumed_kwh': 8.0, 'grid_energy_consumed_kwh': 2.0})

    # Daily aggregation
    res_d = client.get('/api/generation/daily')
    assert res_d.status_code == 200
    assert res_d.get_json()['summary']['total_generated_kwh'] == 25.0

    # Weekly aggregation
    res_w = client.get('/api/generation/weekly')
    assert res_w.status_code == 200

    # Monthly aggregation
    res_m = client.get('/api/generation/monthly')
    assert res_m.status_code == 200

    # Yearly aggregation
    res_y = client.get('/api/generation/yearly')
    assert res_y.status_code == 200


# -------------------------------------------------------------
# 17. Surplus calculation & 18. Storage addition
# -------------------------------------------------------------
def test_17_18_surplus_and_storage_addition(client):
    # Gen 15, Consumed 10 -> Surplus = 5 kWh
    res = client.post('/api/energy', json={
        'date': '2026-08-18',
        'renewable_source': 'Solar',
        'energy_generated_kwh': 15.0,
        'renewable_energy_consumed_kwh': 10.0,
        'grid_energy_consumed_kwh': 0.0
    })
    assert res.status_code == 201
    rec = res.get_json()['record']
    assert rec['surplus_kwh'] == 5.0

    # Storage ledger should now show 5.0 kWh available
    stor_res = client.get('/api/storage')
    assert stor_res.status_code == 200
    assert stor_res.get_json()['available_storage_kwh'] == 5.0


# -------------------------------------------------------------
# 19. Storage consumption & 20. Storage ledger persistence
# -------------------------------------------------------------
def test_19_20_storage_consumption_and_persistence(client):
    # First create surplus of 10 kWh
    client.post('/api/energy', json={
        'date': '2026-08-18',
        'renewable_source': 'Solar',
        'energy_generated_kwh': 20.0,
        'renewable_energy_consumed_kwh': 10.0,
        'grid_energy_consumed_kwh': 0.0
    })
    
    # Check balance = 10 kWh
    assert client.get('/api/storage').get_json()['available_storage_kwh'] == 10.0

    # Consume 4 kWh from battery storage
    res_con = client.post('/api/storage/consume', json={
        'date': '2026-08-19',
        'amount_kwh': 4.0,
        'notes': 'Night EV charging'
    })
    assert res_con.status_code == 201
    assert res_con.get_json()['remaining_storage_kwh'] == 6.0

    # Verify transactions ledger
    tx_res = client.get('/api/storage/transactions')
    assert len(tx_res.get_json()['transactions']) >= 2
    assert tx_res.get_json()['available_balance_kwh'] == 6.0


# -------------------------------------------------------------
# 21. Negative storage prevention
# -------------------------------------------------------------
def test_21_negative_storage_prevention(client):
    # Current storage is 0
    res = client.post('/api/storage/consume', json={
        'date': '2026-08-20',
        'amount_kwh': 10.0,
        'notes': 'Attempting overdraw'
    })
    assert res.status_code == 400
    assert 'Cannot consume' in res.get_json()['error']


# -------------------------------------------------------------
# 22. Grid electricity tariff configuration
# -------------------------------------------------------------
def test_22_tariff_configuration(client):
    # Update tariff to ₹12.50
    res = client.put('/api/settings', json={
        'electricity_tariff': 12.50
    })
    assert res.status_code == 200
    assert res.get_json()['settings']['electricity_tariff'] == 12.50

    # Record saved should use new tariff calculation
    res_rec = client.post('/api/energy', json={
        'date': '2026-08-20',
        'renewable_source': 'Solar',
        'energy_generated_kwh': 10.0,
        'renewable_energy_consumed_kwh': 10.0,
        'grid_energy_consumed_kwh': 0.0
    })
    assert res_rec.status_code == 201
    assert res_rec.get_json()['record']['estimated_savings'] == 125.0  # 10 kWh * 12.50 = 125.0


# -------------------------------------------------------------
# 23. Multi-currency support (INR, USD, EUR, GBP)
# -------------------------------------------------------------
def test_23_multicurrency_support(client):
    currencies = [
        ('INR', '₹'),
        ('USD', '$'),
        ('EUR', '€'),
        ('GBP', '£')
    ]
    for code, sym in currencies:
        res = client.put('/api/settings', json={
            'currency_code': code,
            'currency_symbol': sym
        })
        assert res.status_code == 200
        settings = res.get_json()['settings']
        assert settings['currency_code'] == code
        assert settings['currency_symbol'] == sym
