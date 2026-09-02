import pytest
from datetime import date, timedelta
from backend.app import create_app
from backend.config import TestConfig
from backend.extensions import db
from backend.models.user import User
from backend.models.energy_record import EnergyRecord
from backend.models.renewable_source import RenewableSource
from backend.models.storage_transaction import RenewableStorageTransaction
from backend.models.user_settings import UserSettings
from flask_jwt_extended import create_access_token

@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

@pytest.fixture
def auth_header(client):
    with client.application.app_context():
        user = User(full_name="Test User", email="sync@example.com")
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()

        settings = UserSettings(
            user_id=user.id,
            electricity_tariff=0.15,
            co2_emission_factor=0.82,
            currency_code="USD",
            currency_symbol="$"
        )
        db.session.add(settings)
        db.session.commit()

        token = create_access_token(identity=str(user.id))
        return {'Authorization': f'Bearer {token}'}, user.id

def test_user_requested_flow_and_multipage_filter_sync(client, auth_header):
    headers, user_id = auth_header

    # Step 1: Add Solar Record: Date: 2026-08-20, Gen: 10 kWh, Consumed: 8 kWh, Grid: 2 kWh, Tariff: 0.15
    res1 = client.post('/api/energy', json={
        'date': '2026-08-20',
        'renewable_source': 'Solar',
        'energy_generated_kwh': 10.0,
        'renewable_energy_consumed_kwh': 8.0,
        'grid_energy_consumed_kwh': 2.0,
        'storage_used_kwh': 0.0,
        'electricity_tariff': 0.15,
        'notes': 'Test user exact scenario'
    }, headers=headers)
    assert res1.status_code == 201
    data1 = res1.get_json()['record']
    assert data1['surplus_kwh'] == 2.0
    assert data1['renewable_percentage'] == 80.0
    assert data1['co2_avoided_kg'] == round(8.0 * 0.82, 2)
    assert data1['estimated_savings'] == round(8.0 * 0.15, 2)

    # Verify Dashboard Stats
    dash_res = client.get('/api/dashboard/stats', headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.get_json()
    assert dash_data['overall']['total_generated_kwh'] == 10.0
    assert dash_data['overall']['total_renewable_consumed_kwh'] == 8.0
    assert dash_data['overall']['total_grid_consumed_kwh'] == 2.0
    assert dash_data['overall']['renewable_percentage'] == 80.0
    assert dash_data['storage']['available_kwh'] == 2.0

    # Verify Analytics Overview
    ana_res = client.get('/api/analytics/overview', headers=headers)
    assert ana_res.status_code == 200
    ana_data = ana_res.get_json()
    assert ana_data['summary']['total_generated_kwh'] == 10.0
    assert ana_data['summary']['total_renewable_consumed_kwh'] == 8.0
    assert ana_data['summary']['renewable_percentage'] == 80.0
    assert ana_data['summary']['estimated_co2_avoided_kg'] == round(8.0 * 0.82, 2)
    assert ana_data['summary']['estimated_cost_savings'] == round(8.0 * 0.15, 2)

    # Verify Sources Page Endpoint
    src_res = client.get('/api/analytics/sources', headers=headers)
    assert src_res.status_code == 200
    src_data = src_res.get_json()
    solar_info = src_data['sources_data']['Solar']
    assert solar_info['record_count'] == 1
    assert solar_info['total_generated_kwh'] == 10.0
    assert solar_info['total_renewable_consumed_kwh'] == 8.0
    assert solar_info['contribution_percentage'] == 100.0

    # Verify Environmental Page Endpoint
    env_res = client.get('/api/analytics/environmental', headers=headers)
    assert env_res.status_code == 200
    env_data = env_res.get_json()
    assert env_data['total_co2_avoided_kg'] == round(8.0 * 0.82, 2)
    assert env_data['renewable_percentage'] == 80.0

    # Verify Savings Page Endpoint
    sav_res = client.get('/api/analytics/savings', headers=headers)
    assert sav_res.status_code == 200
    sav_data = sav_res.get_json()
    assert sav_data['total_savings'] == round(8.0 * 0.15, 2)
    assert sav_data['renewable_consumed_kwh'] == 8.0

    # Step 2: Add Wind Record on a different date: Date: 2026-08-19, Gen: 20 kWh, Ren Consumed: 15 kWh, Grid: 5 kWh, Tariff: 0.15
    res2 = client.post('/api/energy', json={
        'date': '2026-08-19',
        'renewable_source': 'Wind',
        'energy_generated_kwh': 20.0,
        'renewable_energy_consumed_kwh': 15.0,
        'grid_energy_consumed_kwh': 5.0,
        'storage_used_kwh': 0.0,
        'electricity_tariff': 0.15,
        'notes': 'Second record for multi-source/multi-day testing'
    }, headers=headers)
    assert res2.status_code == 201

    # Step 3: Test Dynamic Filtering on Analytics Overview
    # Filter 1: Solar Only
    ana_solar = client.get('/api/analytics/overview?source=Solar', headers=headers)
    assert ana_solar.status_code == 200
    ana_solar_data = ana_solar.get_json()
    assert ana_solar_data['summary']['count'] == 1
    assert ana_solar_data['summary']['total_generated_kwh'] == 10.0
    assert ana_solar_data['summary']['total_renewable_consumed_kwh'] == 8.0

    # Filter 2: Wind Only
    ana_wind = client.get('/api/analytics/overview?source=Wind', headers=headers)
    assert ana_wind.status_code == 200
    ana_wind_data = ana_wind.get_json()
    assert ana_wind_data['summary']['count'] == 1
    assert ana_wind_data['summary']['total_generated_kwh'] == 20.0
    assert ana_wind_data['summary']['total_renewable_consumed_kwh'] == 15.0

    # Filter 3: Specific Single Day (2026-08-20)
    ana_day1 = client.get('/api/analytics/overview?start_date=2026-08-20&end_date=2026-08-20', headers=headers)
    assert ana_day1.status_code == 200
    assert ana_day1.get_json()['summary']['count'] == 1
    assert ana_day1.get_json()['summary']['total_generated_kwh'] == 10.0

    # Filter 4: Specific Single Day (2026-08-19)
    ana_day2 = client.get('/api/analytics/overview?start_date=2026-08-19&end_date=2026-08-19', headers=headers)
    assert ana_day2.status_code == 200
    assert ana_day2.get_json()['summary']['count'] == 1
    assert ana_day2.get_json()['summary']['total_generated_kwh'] == 20.0

    # Filter 5: Date Range spanning both (2026-08-19 to 2026-08-20)
    ana_all = client.get('/api/analytics/overview?start_date=2026-08-19&end_date=2026-08-20', headers=headers)
    assert ana_all.status_code == 200
    assert ana_all.get_json()['summary']['count'] == 2
    assert ana_all.get_json()['summary']['total_generated_kwh'] == 30.0
    assert ana_all.get_json()['summary']['total_renewable_consumed_kwh'] == 23.0
    assert ana_all.get_json()['summary']['total_grid_consumed_kwh'] == 7.0
    # Clean: 23, Total: 30 -> 23/30 * 100 = 76.67%
    assert ana_all.get_json()['summary']['renewable_percentage'] == 76.67
    assert ana_all.get_json()['summary']['estimated_co2_avoided_kg'] == round(23.0 * 0.82, 2)
    assert ana_all.get_json()['summary']['estimated_cost_savings'] == round(23.0 * 0.15, 2)

    # Step 4: Test Environmental Filter by Source
    env_solar = client.get('/api/analytics/environmental?source=Solar', headers=headers)
    assert env_solar.status_code == 200
    assert env_solar.get_json()['total_co2_avoided_kg'] == round(8.0 * 0.82, 2)

    env_wind = client.get('/api/analytics/environmental?source=Wind', headers=headers)
    assert env_wind.status_code == 200
    assert env_wind.get_json()['total_co2_avoided_kg'] == round(15.0 * 0.82, 2)

    # Step 5: Test Savings Filter by Source
    sav_solar = client.get('/api/analytics/savings?source=Solar', headers=headers)
    assert sav_solar.status_code == 200
    assert sav_solar.get_json()['total_savings'] == round(8.0 * 0.15, 2)

    sav_wind = client.get('/api/analytics/savings?source=Wind', headers=headers)
    assert sav_wind.status_code == 200
    assert sav_wind.get_json()['total_savings'] == round(15.0 * 0.15, 2)
