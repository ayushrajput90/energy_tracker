"""
Aggregation Service for Renewable Energy Usage Tracker.
Performs non-destructive aggregation over independent EnergyRecord rows,
renewable source configurations, capacity history, daily overrides, and storage transactions.
"""
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from collections import defaultdict
from backend.models.energy_record import EnergyRecord, RENEWABLE_SOURCES
from backend.models.renewable_source import RenewableSource, SourceCapacityHistory
from backend.models.generation_override import DailyGenerationOverride
from backend.models.storage_transaction import RenewableStorageTransaction
from backend.services.calculations import (
    calculate_total_energy_consumed,
    calculate_renewable_percentage,
    calculate_co2_avoided,
    calculate_grid_displacement,
    calculate_cost_savings,
    calculate_surplus,
    calculate_storage_balance,
    aggregate_record_list
)

def parse_date_range(time_filter: str = None, start_date_str: str = None, end_date_str: str = None) -> Tuple[Optional[date], Optional[date]]:
    """
    Parses dynamic time filters (today, yesterday, this_week/weekly, this_month/monthly, this_year/yearly, custom)
    into concrete start_date and end_date objects.
    """
    today = date.today()
    start_date = None
    end_date = None

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            return start_date, end_date
        except ValueError:
            pass
    elif start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = start_date
            return start_date, end_date
        except ValueError:
            pass

    tf = (time_filter or '').lower().strip()
    if tf == 'today':
        start_date = today
        end_date = today
    elif tf == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = today - timedelta(days=1)
    elif tf in ['this_week', 'weekly', 'week']:
        # Start of week (Monday)
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif tf in ['this_month', 'monthly', 'month']:
        start_date = today.replace(day=1)
        end_date = today
    elif tf in ['this_year', 'yearly', 'year']:
        start_date = today.replace(month=1, day=1)
        end_date = today

    return start_date, end_date


def get_filtered_records_query(user_id: int, source: str = None, start_date: date = None, end_date: date = None):
    """
    Constructs an SQLAlchemy query for EnergyRecord filtered by user, source, and date range.
    Never alters data.
    """
    query = EnergyRecord.query.filter_by(user_id=user_id)

    if source and source.strip() and source.lower() not in ['all', 'all sources']:
        query = query.filter(EnergyRecord.renewable_source == source.strip())

    if start_date:
        query = query.filter(EnergyRecord.date >= start_date)
    if end_date:
        query = query.filter(EnergyRecord.date <= end_date)

    return query


def calculate_user_storage_balance(user_id: int, as_of_date: Optional[date] = None) -> float:
    """
    Calculates the user's available renewable storage balance as of a given date (or latest).
    Available balance = total SURPLUS transactions - total CONSUME transactions.
    """
    query = RenewableStorageTransaction.query.filter_by(user_id=user_id)
    if as_of_date:
        query = query.filter(RenewableStorageTransaction.date <= as_of_date)

    txs = query.all()
    surplus_total = sum(t.amount_kwh for t in txs if t.transaction_type == 'SURPLUS')
    consumed_total = sum(t.amount_kwh for t in txs if t.transaction_type == 'CONSUME')
    adjustment_total = sum(t.amount_kwh for t in txs if t.transaction_type == 'ADJUSTMENT')

    balance = surplus_total + adjustment_total - consumed_total
    return round(max(0.0, balance), 4)


def get_daily_generation_telemetry(user_id: int, target_date: date) -> Dict[str, Any]:
    """
    Calculates automatic and override generation for all configured active sources for target_date.
    """
    sources = RenewableSource.query.filter_by(user_id=user_id, active=True).all()
    overrides = {
        o.source_id: o
        for o in DailyGenerationOverride.query.filter_by(user_id=user_id, date=target_date).all()
    }

    source_breakdown = []
    total_auto = 0.0
    total_final = 0.0
    has_any_override = False

    for src in sources:
        # Check if source is effective on or before target_date
        config = src.get_effective_config_for_date(target_date)
        if not config:
            continue

        auto_kwh = float(config['expected_daily_generation_kwh'])
        total_auto += auto_kwh

        override = overrides.get(src.id)
        if override:
            has_any_override = True
            override_kwh = float(override.override_generation_kwh)
            final_kwh = override_kwh
            reason = override.reason
            is_ov = True
        else:
            override_kwh = None
            final_kwh = auto_kwh
            reason = None
            is_ov = False

        total_final += final_kwh

        source_breakdown.append({
            'source_id': src.id,
            'source_type': src.source_type,
            'capacity_kw': float(config['capacity_kw']),
            'automatic_generation_kwh': round(auto_kwh, 2),
            'override_generation_kwh': round(override_kwh, 2) if override_kwh is not None else None,
            'final_generation_kwh': round(final_kwh, 2),
            'is_override': is_ov,
            'reason': reason
        })

    return {
        'date': target_date.isoformat(),
        'total_automatic_generation_kwh': round(total_auto, 2),
        'total_final_generation_kwh': round(total_final, 2),
        'has_override': has_any_override,
        'sources': source_breakdown
    }


def aggregate_by_source(records: List[EnergyRecord], emission_factor: float = 0.82, default_tariff: float = 0.15) -> Dict[str, Any]:
    """
    Aggregates a list of independent records grouped by renewable source.
    """
    sources_data = {}
    for src in RENEWABLE_SOURCES:
        sources_data[src] = {
            'source': src,
            'record_count': 0,
            'total_generated_kwh': 0.0,
            'total_renewable_consumed_kwh': 0.0,
            'total_grid_consumed_kwh': 0.0,
            'total_storage_used_kwh': 0.0,
            'total_surplus_kwh': 0.0,
            'total_consumed_kwh': 0.0,
            'renewable_percentage': 0.0,
            'estimated_co2_avoided_kg': 0.0,
            'estimated_grid_displaced_kwh': 0.0,
            'estimated_cost_savings': 0.0,
            'contribution_percentage': 0.0 # % of total renewable generated
        }

    total_gen_all = 0.0

    for r in records:
        src = r.renewable_source
        if src not in sources_data:
            sources_data[src] = {
                'source': src,
                'record_count': 0,
                'total_generated_kwh': 0.0,
                'total_renewable_consumed_kwh': 0.0,
                'total_grid_consumed_kwh': 0.0,
                'total_storage_used_kwh': 0.0,
                'total_surplus_kwh': 0.0,
                'total_consumed_kwh': 0.0,
                'renewable_percentage': 0.0,
                'estimated_co2_avoided_kg': 0.0,
                'estimated_grid_displaced_kwh': 0.0,
                'estimated_cost_savings': 0.0,
                'contribution_percentage': 0.0
            }

        s = sources_data[src]
        s['record_count'] += 1
        gen = float(r.energy_generated_kwh or 0.0)
        ren_con = float(r.renewable_energy_consumed_kwh or 0.0)
        grid_con = float(r.grid_energy_consumed_kwh or 0.0)
        storage_used = float(r.storage_used_kwh or 0.0)
        tariff = float(r.electricity_tariff or default_tariff)

        s['total_generated_kwh'] += gen
        s['total_renewable_consumed_kwh'] += ren_con
        s['total_grid_consumed_kwh'] += grid_con
        s['total_storage_used_kwh'] += storage_used
        s['total_surplus_kwh'] += float(r.surplus_kwh or calculate_surplus(gen, ren_con))
        s['estimated_cost_savings'] += (ren_con + storage_used) * tariff
        total_gen_all += gen

    for src, s in sources_data.items():
        s['total_generated_kwh'] = round(s['total_generated_kwh'], 4)
        s['total_renewable_consumed_kwh'] = round(s['total_renewable_consumed_kwh'], 4)
        s['total_grid_consumed_kwh'] = round(s['total_grid_consumed_kwh'], 4)
        s['total_storage_used_kwh'] = round(s['total_storage_used_kwh'], 4)
        s['total_surplus_kwh'] = round(s['total_surplus_kwh'], 4)
        
        clean_used = s['total_renewable_consumed_kwh'] + s['total_storage_used_kwh']
        tot_con = clean_used + s['total_grid_consumed_kwh']
        s['total_consumed_kwh'] = round(tot_con, 4)
        s['renewable_percentage'] = calculate_renewable_percentage(clean_used, tot_con)
        s['estimated_co2_avoided_kg'] = calculate_co2_avoided(clean_used, emission_factor)
        s['estimated_grid_displaced_kwh'] = calculate_grid_displacement(clean_used)
        s['estimated_cost_savings'] = round(s['estimated_cost_savings'], 4)
        
        if total_gen_all > 0:
            s['contribution_percentage'] = round((s['total_generated_kwh'] / total_gen_all) * 100.0, 2)
        else:
            s['contribution_percentage'] = 0.0

    return sources_data


def aggregate_by_date(records: List[EnergyRecord], emission_factor: float = 0.82) -> List[Dict[str, Any]]:
    """
    Groups records by their ISO date string and calculates daily metrics.
    """
    date_map = defaultdict(list)
    for r in records:
        d_str = r.date.isoformat() if isinstance(r.date, (date, datetime)) else str(r.date)
        date_map[d_str].append(r)

    results = []
    # Sort by date ascending
    for d_str in sorted(date_map.keys()):
        daily_records = date_map[d_str]
        agg = aggregate_record_list(daily_records, emission_factor=emission_factor)
        agg['date'] = d_str
        results.append(agg)

    return results


def aggregate_records_by_time_period(
    records: List[EnergyRecord],
    period: str = 'daily',
    emission_factor: float = 0.82,
    default_tariff: float = 0.15
) -> List[Dict[str, Any]]:
    """
    Aggregates records by daily, weekly, monthly, or yearly buckets.
    """
    bucket_map = defaultdict(list)
    period = period.lower().strip()

    for r in records:
        r_date = r.date if isinstance(r.date, date) else datetime.strptime(str(r.date), '%Y-%m-%d').date()
        if period == 'weekly':
            # Monday of the week
            start_of_week = r_date - timedelta(days=r_date.weekday())
            key = f"Week of {start_of_week.strftime('%d %b %Y')}"
            sort_key = start_of_week
        elif period == 'monthly':
            key = r_date.strftime('%b %Y')
            sort_key = r_date.replace(day=1)
        elif period == 'yearly':
            key = str(r_date.year)
            sort_key = date(r_date.year, 1, 1)
        else: # daily
            key = r_date.isoformat()
            sort_key = r_date

        bucket_map[(sort_key, key)].append(r)

    results = []
    for (sort_key, label) in sorted(bucket_map.keys()):
        group_records = bucket_map[(sort_key, label)]
        agg = aggregate_record_list(group_records, emission_factor=emission_factor, default_tariff=default_tariff)
        agg['period_label'] = label
        agg['start_date'] = sort_key.isoformat()
        results.append(agg)

    return results
