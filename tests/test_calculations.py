"""
Unit tests for centralized calculation services.
"""
import pytest
from backend.services.calculations import (
    calculate_total_energy_consumed,
    calculate_renewable_percentage,
    calculate_co2_avoided,
    calculate_grid_displacement,
    calculate_cost_savings,
    aggregate_record_list
)

def test_total_energy_consumed():
    assert calculate_total_energy_consumed(10.0, 5.0) == 15.0
    assert calculate_total_energy_consumed(0, 0) == 0.0
    assert calculate_total_energy_consumed(12.3456, 7.8910) == 20.2366

def test_renewable_percentage():
    # 10 consumed out of 20 total = 50%
    assert calculate_renewable_percentage(10.0, 20.0) == 50.0
    # 0 total consumption = safe 0% without division error
    assert calculate_renewable_percentage(0, 0) == 0.0
    # 100% renewable
    assert calculate_renewable_percentage(15.0, 15.0) == 100.0
    # Caps at 100%
    assert calculate_renewable_percentage(30.0, 20.0) == 100.0

def test_co2_avoided():
    # 100 kWh * 0.82 kg/kWh = 82 kg CO2
    assert calculate_co2_avoided(100.0, 0.82) == 82.0
    # Custom emission factor
    assert calculate_co2_avoided(50.0, 0.5) == 25.0

def test_grid_displacement():
    assert calculate_grid_displacement(45.5) == 45.5

def test_cost_savings():
    # 100 kWh * $0.15/kWh = $15.00
    assert calculate_cost_savings(100.0, 0.15) == 15.00
    assert calculate_cost_savings(200.0, 0.20) == 40.00

def test_aggregate_record_list():
    sample_records = [
        {'energy_generated_kwh': 10.0, 'renewable_energy_consumed_kwh': 8.0, 'grid_energy_consumed_kwh': 2.0, 'electricity_tariff': 0.15},
        {'energy_generated_kwh': 5.0, 'renewable_energy_consumed_kwh': 4.0, 'grid_energy_consumed_kwh': 1.0, 'electricity_tariff': 0.15},
    ]
    agg = aggregate_record_list(sample_records, emission_factor=0.82, default_tariff=0.15)
    assert agg['count'] == 2
    assert agg['total_generated_kwh'] == 15.0
    assert agg['total_renewable_consumed_kwh'] == 12.0
    assert agg['total_grid_consumed_kwh'] == 3.0
    assert agg['total_consumed_kwh'] == 15.0
    assert agg['renewable_percentage'] == 80.0 # (12/15)*100
    assert agg['estimated_co2_avoided_kg'] == round(12.0 * 0.82, 4)
    assert agg['estimated_grid_displaced_kwh'] == 12.0
    assert agg['estimated_cost_savings'] == round(12.0 * 0.15, 4)
