from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models.energy_record import EnergyRecord, RENEWABLE_SOURCES
from backend.models.user_settings import UserSettings
from backend.services.calculations import (
    calculate_record_metrics,
    aggregate_record_list,
    calculate_renewable_percentage,
    calculate_co2_avoided,
    calculate_cost_savings
)
from backend.services.aggregation import (
    parse_date_range,
    get_filtered_records_query,
    aggregate_by_source,
    aggregate_by_date
)
from backend.services.insights import generate_insights

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')

@analytics_bp.route('/overview', methods=['GET'])
@jwt_required()
def get_analytics_overview():
    user_id = int(get_jwt_identity())
    source = request.args.get('source')
    time_filter = request.args.get('time_filter', 'this_year')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    start_date, end_date = parse_date_range(time_filter, start_date_str, end_date_str)
    query = get_filtered_records_query(user_id, source=source, start_date=start_date, end_date=end_date)
    records = query.order_by(EnergyRecord.date.asc()).all()

    settings = UserSettings.query.filter_by(user_id=user_id).first()
    emission_factor = settings.co2_emission_factor if settings else 0.82
    tariff = settings.electricity_tariff if settings else 9.0
    currency_symbol = settings.currency_symbol if settings else '₹'

    # Overall Summary of filtered records
    summary = aggregate_record_list(records, emission_factor, tariff)

    # Time series (daily aggregation)
    daily_series = aggregate_by_date(records, emission_factor)

    # Source breakdown
    sources_data = aggregate_by_source(records, emission_factor, tariff)

    return jsonify({
        'summary': summary,
        'daily_series': daily_series,
        'sources_data': sources_data,
        'sources_list': list(sources_data.values()),
        'currency_symbol': currency_symbol
    }), 200


@analytics_bp.route('/sources', methods=['GET'])
@jwt_required()
def get_source_comparison():
    user_id = int(get_jwt_identity())
    source = request.args.get('source')
    time_filter = request.args.get('time_filter')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    start_date, end_date = parse_date_range(time_filter, start_date_str, end_date_str)
    query = get_filtered_records_query(user_id, source=source, start_date=start_date, end_date=end_date)
    records = query.order_by(EnergyRecord.date.asc()).all()

    settings = UserSettings.query.filter_by(user_id=user_id).first()
    emission_factor = settings.co2_emission_factor if settings else 0.82
    tariff = settings.electricity_tariff if settings else 9.0
    currency_symbol = settings.currency_symbol if settings else '₹'

    sources_data = aggregate_by_source(records, emission_factor, tariff)

    # Filter source list if specific source requested
    filtered_sources_list = [s for s in RENEWABLE_SOURCES if (not source or source.lower() in ['all', 'all sources'] or s.lower() == source.lower())]

    labels = []
    generated_data = []
    consumed_data = []
    co2_data = []
    savings_data = []

    for src in filtered_sources_list:
        info = sources_data.get(src, {})
        labels.append(src)
        generated_data.append(info.get('total_generated_kwh', 0.0))
        consumed_data.append(info.get('total_renewable_consumed_kwh', 0.0))
        co2_data.append(info.get('estimated_co2_avoided_kg', 0.0))
        savings_data.append(info.get('estimated_cost_savings', 0.0))

    return jsonify({
        'sources_data': sources_data,
        'table_data': [sources_data[s] for s in filtered_sources_list if s in sources_data],
        'currency_symbol': currency_symbol,
        'chart': {
            'labels': labels,
            'generated': generated_data,
            'consumed': consumed_data,
            'co2_avoided': co2_data,
            'savings': savings_data
        }
    }), 200


@analytics_bp.route('/environmental', methods=['GET'])
@jwt_required()
def get_environmental_impact():
    user_id = int(get_jwt_identity())
    source = request.args.get('source')
    time_filter = request.args.get('time_filter')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    settings = UserSettings.query.filter_by(user_id=user_id).first()
    emission_factor = settings.co2_emission_factor if settings else 0.82
    tariff = settings.electricity_tariff if settings else 9.0

    today = date.today()
    start_this_month = today.replace(day=1)
    start_this_year = today.replace(month=1, day=1)

    start_date, end_date = parse_date_range(time_filter, start_date_str, end_date_str)
    query = get_filtered_records_query(user_id, source=source, start_date=start_date, end_date=end_date)
    filtered_records = query.order_by(EnergyRecord.date.asc()).all()

    all_user_records = EnergyRecord.query.filter_by(user_id=user_id)
    if source and source.lower() not in ['all', 'all sources']:
        all_user_records = all_user_records.filter(EnergyRecord.renewable_source == source)
    all_user_records = all_user_records.all()

    overall = aggregate_record_list(filtered_records, emission_factor, tariff)
    today_agg = aggregate_record_list([r for r in all_user_records if r.date == today], emission_factor, tariff)
    month_agg = aggregate_record_list([r for r in all_user_records if r.date >= start_this_month], emission_factor, tariff)
    year_agg = aggregate_record_list([r for r in all_user_records if r.date >= start_this_year], emission_factor, tariff)

    daily_trend = aggregate_by_date(filtered_records, emission_factor)

    total_co2 = overall['estimated_co2_avoided_kg']
    trees_equiv = round(total_co2 / 21.77, 1)
    car_miles_equiv = round(total_co2 * 2.5, 1)
    coal_lbs_equiv = round(total_co2 * 1.1, 1)

    return jsonify({
        'total_co2_avoided_kg': total_co2,
        'today_co2_avoided_kg': today_agg['estimated_co2_avoided_kg'],
        'monthly_co2_avoided_kg': month_agg['estimated_co2_avoided_kg'],
        'yearly_co2_avoided_kg': year_agg['estimated_co2_avoided_kg'],
        'renewable_percentage': overall['renewable_percentage'],
        'estimated_grid_displaced_kwh': overall['estimated_grid_displaced_kwh'],
        'emission_factor': emission_factor,
        'equivalencies': {
            'trees_planted_yearly': trees_equiv,
            'car_miles_displaced': car_miles_equiv,
            'coal_burn_avoided_lbs': coal_lbs_equiv
        },
        'methodology': {
            'formula': 'Estimated CO2 Avoided (kg) = Renewable Energy Consumed (kWh) × Grid Emission Factor (kg CO2/kWh)',
            'factor_used': f"{emission_factor} kg CO2/kWh",
            'description': 'Calculates the greenhouse gas emissions prevented by substituting fossil-fueled grid electricity with zero-emission on-site renewable generation.'
        },
        'trend': daily_trend
    }), 200


@analytics_bp.route('/savings', methods=['GET'])
@jwt_required()
def get_savings_analysis():
    user_id = int(get_jwt_identity())
    source = request.args.get('source')
    time_filter = request.args.get('time_filter')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    settings = UserSettings.query.filter_by(user_id=user_id).first()
    emission_factor = settings.co2_emission_factor if settings else 0.82
    tariff = settings.electricity_tariff if settings else 9.0
    currency_symbol = settings.currency_symbol if settings else '₹'

    today = date.today()
    start_this_month = today.replace(day=1)
    start_this_year = today.replace(month=1, day=1)

    start_date, end_date = parse_date_range(time_filter, start_date_str, end_date_str)
    query = get_filtered_records_query(user_id, source=source, start_date=start_date, end_date=end_date)
    filtered_records = query.order_by(EnergyRecord.date.asc()).all()

    all_user_records = EnergyRecord.query.filter_by(user_id=user_id)
    if source and source.lower() not in ['all', 'all sources']:
        all_user_records = all_user_records.filter(EnergyRecord.renewable_source == source)
    all_user_records = all_user_records.all()

    overall = aggregate_record_list(filtered_records, emission_factor, tariff)
    today_agg = aggregate_record_list([r for r in all_user_records if r.date == today], emission_factor, tariff)
    month_agg = aggregate_record_list([r for r in all_user_records if r.date >= start_this_month], emission_factor, tariff)
    year_agg = aggregate_record_list([r for r in all_user_records if r.date >= start_this_year], emission_factor, tariff)

    daily_trend = aggregate_by_date(filtered_records, emission_factor)

    return jsonify({
        'total_savings': overall['estimated_cost_savings'],
        'today_savings': today_agg['estimated_cost_savings'],
        'monthly_savings': month_agg['estimated_cost_savings'],
        'yearly_savings': year_agg['estimated_cost_savings'],
        'renewable_consumed_kwh': overall['total_renewable_consumed_kwh'],
        'grid_displaced_kwh': overall['estimated_grid_displaced_kwh'],
        'current_tariff': tariff,
        'currency_symbol': currency_symbol,
        'methodology': {
            'formula': f"Estimated Cost Savings = Renewable Energy Consumed (kWh) × Electricity Tariff ({currency_symbol}/kWh)",
            'tariff_used': f"{currency_symbol}{tariff:.4f}/kWh",
            'notes': 'Actual utility bill reductions can vary based on net metering policies, tier rates, and peak load surcharges.'
        },
        'trend': daily_trend
    }), 200


@analytics_bp.route('/insights', methods=['GET'])
@jwt_required()
def get_insights():
    user_id = int(get_jwt_identity())
    settings = UserSettings.query.filter_by(user_id=user_id).first()
    emission_factor = settings.co2_emission_factor if settings else 0.82
    tariff = settings.electricity_tariff if settings else 9.0

    insights = generate_insights(user_id, emission_factor, tariff)
    return jsonify({'insights': insights}), 200
