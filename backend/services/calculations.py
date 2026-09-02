"""
Centralized Calculation Engine for Renewable Energy Usage Tracker
Implements formulas for energy consumption, renewable percentage,
estimated CO2 avoidance, grid displacement, estimated financial savings,
renewable surplus, and storage balance calculations.
"""
from typing import Optional, Dict, Any, List

def calculate_total_energy_consumed(renewable_consumed_kwh: float, grid_consumed_kwh: float, storage_used_kwh: float = 0.0) -> float:
    """
    Total Electricity Consumed = Renewable Energy Consumed + Grid Energy Consumed (+ Storage Used if tracked separately)
    """
    renewable = float(renewable_consumed_kwh or 0.0)
    grid = float(grid_consumed_kwh or 0.0)
    storage = float(storage_used_kwh or 0.0)
    return round(renewable + grid + storage, 4)


def calculate_renewable_percentage(renewable_consumed_kwh: float, total_consumed_kwh: float) -> float:
    """
    Renewable Energy Percentage = (Total Renewable Energy Consumed / Total Electricity Consumed) * 100
    Safely handles division by zero.
    """
    total = float(total_consumed_kwh or 0.0)
    renewable = float(renewable_consumed_kwh or 0.0)
    if total <= 0.0:
        return 0.0
    percentage = (renewable / total) * 100.0
    return round(min(percentage, 100.0), 2)


def calculate_surplus(generation_kwh: float, renewable_consumed_kwh: float) -> float:
    """
    Surplus = Renewable Generation - Renewable Consumed
    Never returns negative surplus.
    """
    gen = float(generation_kwh or 0.0)
    consumed = float(renewable_consumed_kwh or 0.0)
    return round(max(0.0, gen - consumed), 4)


def calculate_storage_balance(previous_storage: float, surplus: float, storage_used: float) -> float:
    """
    Storage Ending Balance = Previous Storage + Today's Surplus - Storage Used
    Never allows storage to become negative.
    """
    prev = float(previous_storage or 0.0)
    surp = float(surplus or 0.0)
    used = float(storage_used or 0.0)
    return round(max(0.0, prev + surp - used), 4)


def calculate_co2_avoided(renewable_consumed_kwh: float, emission_factor: float = 0.82) -> float:
    """
    Estimated CO2 Avoided = Renewable Energy Consumed * Grid Emission Factor
    Units: Energy in kWh, Emission Factor in kg CO2/kWh, Result in kg CO2.
    """
    renewable = float(renewable_consumed_kwh or 0.0)
    factor = float(emission_factor if emission_factor is not None else 0.82)
    return round(renewable * factor, 4)


def calculate_grid_displacement(renewable_consumed_kwh: float) -> float:
    """
    Estimated Grid Electricity Displaced = Renewable Energy Consumed (kWh)
    """
    return round(float(renewable_consumed_kwh or 0.0), 4)


def calculate_cost_savings(renewable_consumed_kwh: float, tariff: float = 0.15) -> float:
    """
    Estimated Cost Savings = Renewable Energy Consumed * Electricity Tariff
    Units: Configured user currency (e.g., ₹, $, €, £)
    """
    renewable = float(renewable_consumed_kwh or 0.0)
    rate = float(tariff if tariff is not None else 0.15)
    return round(renewable * rate, 4)


def calculate_record_metrics(record, emission_factor: float = 0.82, default_tariff: float = 0.15) -> dict:
    """
    Takes an EnergyRecord object or dict and computes all derived metrics.
    """
    if hasattr(record, 'to_dict'):
        data = record.to_dict()
    else:
        data = dict(record)

    gen = float(data.get('energy_generated_kwh', 0.0))
    ren_con = float(data.get('renewable_energy_consumed_kwh', 0.0))
    grid_con = float(data.get('grid_energy_consumed_kwh', 0.0))
    storage_used = float(data.get('storage_used_kwh', 0.0))
    tariff = float(data.get('electricity_tariff', default_tariff))
    
    # Check if total_energy_consumed_kwh was already recorded or compute it
    total_con = calculate_total_energy_consumed(ren_con, grid_con, storage_used)
    total_clean_used = ren_con + storage_used
    ren_pct = calculate_renewable_percentage(total_clean_used, total_con)
    surplus = calculate_surplus(gen, ren_con)
    co2 = calculate_co2_avoided(total_clean_used, emission_factor)
    grid_disp = calculate_grid_displacement(total_clean_used)
    savings = calculate_cost_savings(total_clean_used, tariff)

    data['total_energy_consumed_kwh'] = total_con
    data['renewable_percentage'] = ren_pct
    data['surplus_kwh'] = surplus
    data['co2_avoided_kg'] = co2
    data['grid_displaced_kwh'] = grid_disp
    data['estimated_savings'] = savings
    return data


def aggregate_record_list(records, emission_factor: float = 0.82, default_tariff: float = 0.15) -> dict:
    """
    Calculates aggregated metrics over an iterable of records.
    Never modifies individual records.
    """
    total_generated = 0.0
    total_renewable_consumed = 0.0
    total_grid_consumed = 0.0
    total_storage_used = 0.0
    total_surplus = 0.0
    total_cost_savings = 0.0

    record_count = 0
    for r in records:
        record_count += 1
        gen = float(getattr(r, 'energy_generated_kwh', 0.0) if hasattr(r, 'energy_generated_kwh') else r.get('energy_generated_kwh', 0.0))
        ren_con = float(getattr(r, 'renewable_energy_consumed_kwh', 0.0) if hasattr(r, 'renewable_energy_consumed_kwh') else r.get('renewable_energy_consumed_kwh', 0.0))
        grid_con = float(getattr(r, 'grid_energy_consumed_kwh', 0.0) if hasattr(r, 'grid_energy_consumed_kwh') else r.get('grid_energy_consumed_kwh', 0.0))
        storage_used = float(getattr(r, 'storage_used_kwh', 0.0) if hasattr(r, 'storage_used_kwh') else r.get('storage_used_kwh', 0.0))
        surplus = float(getattr(r, 'surplus_kwh', 0.0) if hasattr(r, 'surplus_kwh') else r.get('surplus_kwh', calculate_surplus(gen, ren_con)))
        tariff = float(getattr(r, 'electricity_tariff', default_tariff) if hasattr(r, 'electricity_tariff') else r.get('electricity_tariff', default_tariff))

        clean_utilized = ren_con + storage_used
        total_generated += gen
        total_renewable_consumed += ren_con
        total_grid_consumed += grid_con
        total_storage_used += storage_used
        total_surplus += surplus
        total_cost_savings += (clean_utilized * tariff)

    total_clean_used = total_renewable_consumed + total_storage_used
    total_consumed = total_renewable_consumed + total_grid_consumed + total_storage_used
    ren_pct = calculate_renewable_percentage(total_clean_used, total_consumed)
    co2_avoided = calculate_co2_avoided(total_clean_used, emission_factor)
    grid_displaced = calculate_grid_displacement(total_clean_used)

    return {
        'count': record_count,
        'total_generated_kwh': round(total_generated, 4),
        'total_renewable_consumed_kwh': round(total_renewable_consumed, 4),
        'total_grid_consumed_kwh': round(total_grid_consumed, 4),
        'total_storage_used_kwh': round(total_storage_used, 4),
        'total_surplus_kwh': round(total_surplus, 4),
        'total_consumed_kwh': round(total_consumed, 4),
        'renewable_percentage': ren_pct,
        'estimated_co2_avoided_kg': co2_avoided,
        'estimated_grid_displaced_kwh': grid_displaced,
        'estimated_cost_savings': round(total_cost_savings, 4)
    }
