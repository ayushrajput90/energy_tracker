"""
Exact Acceptance Scenario Test (As specified in Sections 39 and 40)
Validates that multiple records for the same date and source are preserved
as completely independent database records and aggregations compute accurately.
"""
import pytest
from datetime import date
from backend.app import create_app
from backend.config import TestConfig
from backend.extensions import db
from backend.models.user import User
from backend.models.energy_record import EnergyRecord
from backend.models.user_settings import UserSettings
from backend.services.aggregation import (
    aggregate_by_source,
    aggregate_by_date,
    get_filtered_records_query
)
from backend.services.calculations import aggregate_record_list

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_exact_acceptance_scenario(app, client):
    with app.app_context():
        # 1. Register a test user
        res_reg = client.post('/api/auth/register', json={
            'full_name': 'Alex Green',
            'email': 'alex@example.com',
            'password': 'Password123!'
        })
        assert res_reg.status_code == 201, res_reg.get_json()
        token = res_reg.get_json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        # 2. Insert 6 records for 18 August
        # Solar -> 10 kWh
        # Solar -> 5 kWh
        # Wind -> 10 kWh
        # Biomass -> 10 kWh
        # Hydro -> 10 kWh
        # Geothermal -> 10 kWh
        aug_18_records = [
            {'date': '2026-08-18', 'renewable_source': 'Solar', 'energy_generated_kwh': 10.0, 'renewable_energy_consumed_kwh': 8.0, 'grid_energy_consumed_kwh': 2.0},
            {'date': '2026-08-18', 'renewable_source': 'Solar', 'energy_generated_kwh': 5.0, 'renewable_energy_consumed_kwh': 4.0, 'grid_energy_consumed_kwh': 1.0},
            {'date': '2026-08-18', 'renewable_source': 'Wind', 'energy_generated_kwh': 10.0, 'renewable_energy_consumed_kwh': 8.0, 'grid_energy_consumed_kwh': 2.0},
            {'date': '2026-08-18', 'renewable_source': 'Biomass', 'energy_generated_kwh': 10.0, 'renewable_energy_consumed_kwh': 7.0, 'grid_energy_consumed_kwh': 3.0},
            {'date': '2026-08-18', 'renewable_source': 'Hydro', 'energy_generated_kwh': 10.0, 'renewable_energy_consumed_kwh': 9.0, 'grid_energy_consumed_kwh': 1.0},
            {'date': '2026-08-18', 'renewable_source': 'Geothermal', 'energy_generated_kwh': 10.0, 'renewable_energy_consumed_kwh': 10.0, 'grid_energy_consumed_kwh': 0.0},
        ]

        for item in aug_18_records:
            res = client.post('/api/energy', json=item, headers=headers)
            assert res.status_code == 201, res.get_json()

        # 3. VERIFY DATABASE RECORDS = Exactly 6 separate records
        all_db_records = EnergyRecord.query.all()
        assert len(all_db_records) == 6, f"Expected 6 separate records, found {len(all_db_records)}"

        # 4. Verify Source Aggregations for 18 August
        sources_agg = aggregate_by_source(all_db_records)
        assert sources_agg['Solar']['total_generated_kwh'] == 15.0, "Solar total must be 10 + 5 = 15 kWh"
        assert sources_agg['Solar']['record_count'] == 2, "Solar must have 2 separate records"
        assert sources_agg['Wind']['total_generated_kwh'] == 10.0
        assert sources_agg['Biomass']['total_generated_kwh'] == 10.0
        assert sources_agg['Hydro']['total_generated_kwh'] == 10.0
        assert sources_agg['Geothermal']['total_generated_kwh'] == 10.0

        # 5. Verify ALL SOURCES Total for 18 August
        all_agg = aggregate_record_list(all_db_records)
        assert all_agg['total_generated_kwh'] == 55.0, "Total generated across all sources on 18 Aug must be 55 kWh"

        # 6. Verify Date Total for 18 August via API
        res_date_18 = client.get('/api/energy?start_date=2026-08-18&end_date=2026-08-18', headers=headers)
        assert res_date_18.status_code == 200
        data_18 = res_date_18.get_json()
        assert len(data_18['records']) == 6, "Must return all 6 individual records"
        assert data_18['summary']['total_generated_kwh'] == 55.0

        # 7. Add 19 August records:
        # Solar -> 20 kWh
        # Wind -> 15 kWh
        aug_19_records = [
            {'date': '2026-08-19', 'renewable_source': 'Solar', 'energy_generated_kwh': 20.0, 'renewable_energy_consumed_kwh': 15.0, 'grid_energy_consumed_kwh': 5.0},
            {'date': '2026-08-19', 'renewable_source': 'Wind', 'energy_generated_kwh': 15.0, 'renewable_energy_consumed_kwh': 12.0, 'grid_energy_consumed_kwh': 3.0},
        ]
        for item in aug_19_records:
            res = client.post('/api/energy', json=item, headers=headers)
            assert res.status_code == 201

        # 8. Verify total database records = 8
        all_8_records = EnergyRecord.query.all()
        assert len(all_8_records) == 8, f"Expected 8 total separate records, found {len(all_8_records)}"

        # 9. Verify 19 August Total = 35 kWh
        res_date_19 = client.get('/api/energy?start_date=2026-08-19&end_date=2026-08-19', headers=headers)
        assert res_date_19.get_json()['summary']['total_generated_kwh'] == 35.0

        # 10. Verify Combined 18-19 August Total = 55 + 35 = 90 kWh
        res_combined = client.get('/api/energy?start_date=2026-08-18&end_date=2026-08-19', headers=headers)
        assert res_combined.get_json()['summary']['total_generated_kwh'] == 90.0

        # 11. Verify Solar Filter across 18-19 August = 15 + 20 = 35 kWh
        res_solar = client.get('/api/energy?source=Solar', headers=headers)
        solar_data = res_solar.get_json()
        assert len(solar_data['records']) == 3, "Expected 3 individual Solar records"
        assert solar_data['summary']['total_generated_kwh'] == 35.0

        # 12. Verify Wind Filter across 18-19 August = 10 + 15 = 25 kWh
        res_wind = client.get('/api/energy?source=Wind', headers=headers)
        wind_data = res_wind.get_json()
        assert len(wind_data['records']) == 2, "Expected 2 individual Wind records"
        assert wind_data['summary']['total_generated_kwh'] == 25.0

        # 13. Verify All Sources Combined = 90 kWh
        res_all = client.get('/api/energy?source=All', headers=headers)
        all_data = res_all.get_json()
        assert len(all_data['records']) == 8
        assert all_data['summary']['total_generated_kwh'] == 90.0

        # 14. Verify that individual records still exist completely intact
        res_single = client.get(f"/api/energy/{all_db_records[0].id}", headers=headers)
        assert res_single.status_code == 200
        assert res_single.get_json()['record']['energy_generated_kwh'] == 10.0
