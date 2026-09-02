from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models.energy_record import EnergyRecord
from backend.models.renewable_source import RenewableSource
from backend.models.user_settings import UserSettings
from backend.models.goal import Goal
from backend.models.activity import Activity
from backend.services.calculations import (
    calculate_record_metrics,
    aggregate_record_list
)
from backend.services.aggregation import (
    parse_date_range,
    get_filtered_records_query,
    aggregate_by_source,
    calculate_user_storage_balance,
    get_daily_generation_telemetry
)
from backend.services.insights import generate_insights

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

@dashboard_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    user_id = int(get_jwt_identity())
    settings = UserSettings.query.filter_by(user_id=user_id).first()
    emission_factor = settings.co2_emission_factor if settings else 0.82
    tariff = settings.electricity_tariff if settings else 0.15
    curr_code = settings.currency_code if settings and settings.currency_code else 'INR'
    curr_sym = settings.currency_symbol if settings and settings.currency_symbol else '₹'

    today = date.today()
    start_this_month = today.replace(day=1)

    # Period filter
    period_param = request.args.get('period', request.args.get('time_filter', 'all'))
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    start_date, end_date = parse_date_range(period_param, start_date_str, end_date_str)

    all_records = EnergyRecord.query.filter_by(user_id=user_id).all()
    
    # Filtered records for selected period
    if start_date or end_date:
        period_records = get_filtered_records_query(user_id, start_date=start_date, end_date=end_date).all()
    else:
        period_records = all_records

    # Lifetime / All-time overall aggregation
    overall_agg = aggregate_record_list(all_records, emission_factor, tariff)

    # Selected period aggregation
    period_agg = aggregate_record_list(period_records, emission_factor, tariff)

    # Today's records
    today_records = [r for r in all_records if r.date == today]
    today_agg = aggregate_record_list(today_records, emission_factor, tariff)

    # This month's records
    month_records = [r for r in all_records if r.date >= start_this_month]
    month_agg = aggregate_record_list(month_records, emission_factor, tariff)

    # Source breakdown for period
    sources_data = aggregate_by_source(period_records, emission_factor, tariff)

    # Renewable sources configuration info
    configured_sources = RenewableSource.query.filter_by(user_id=user_id).all()
    active_sources = [s for s in configured_sources if s.active]
    total_capacity = sum(s.installed_capacity_kw for s in active_sources)
    total_expected_daily = sum(s.expected_daily_generation_kwh for s in active_sources)

    # Storage & Telemetry for Today
    storage_balance = calculate_user_storage_balance(user_id)
    today_telemetry = get_daily_generation_telemetry(user_id, today)

    # Active Goals progress summary
    active_goals = Goal.query.filter_by(user_id=user_id, status='Active').all()
    goals_summary = []
    for g in active_goals:
        goal_records = [r for r in all_records if g.start_date <= r.date <= g.end_date]
        g_agg = aggregate_record_list(goal_records, emission_factor, tariff)
        
        current_val = 0.0
        if g.goal_type == 'Energy Generation':
            current_val = g_agg['total_generated_kwh']
        elif g.goal_type == 'Renewable Consumption':
            current_val = g_agg['total_renewable_consumed_kwh']
        elif g.goal_type == 'Renewable Percentage':
            current_val = g_agg['renewable_percentage']
        elif g.goal_type == 'CO2 Reduction/Avoidance':
            current_val = g_agg['estimated_co2_avoided_kg']
        elif g.goal_type == 'Grid Electricity Displacement':
            current_val = g_agg['estimated_grid_displaced_kwh']
        elif g.goal_type == 'Cost Savings':
            current_val = g_agg['estimated_cost_savings']

        completion = min(round((current_val / g.target_value * 100.0) if g.target_value > 0 else 0.0, 1), 100.0)
        goals_summary.append({
            'id': g.id,
            'goal_type': g.goal_type,
            'target_value': g.target_value,
            'current_value': round(current_val, 2),
            'completion_percentage': completion,
            'end_date': g.end_date.isoformat(),
            'description': g.description or g.goal_type
        })

    return jsonify({
        'overall': overall_agg,
        'period_summary': period_agg,
        'today': today_agg,
        'this_month': month_agg,
        'selected_period': period_param or 'all',
        'sources_summary': list(sources_data.values()),
        'active_goals': goals_summary,
        'active_goals_count': len(active_goals),
        'storage': {
            'available_kwh': round(storage_balance, 4),
            'today_storage_used_kwh': round(today_agg.get('total_storage_used_kwh', 0.0), 4),
            'today_surplus_kwh': round(today_agg.get('total_surplus_kwh', 0.0), 4)
        },
        'telemetry_today': today_telemetry,
        'system': {
            'installed_capacity_kw': round(total_capacity, 2),
            'expected_daily_generation_kwh': round(total_expected_daily, 2),
            'active_sources_count': len(active_sources),
            'total_sources_count': len(configured_sources),
            'currency_code': curr_code,
            'currency_symbol': curr_sym,
            'tariff': tariff,
            'emission_factor': emission_factor
        }
    }), 200


@dashboard_bp.route('/recent', methods=['GET'])
@jwt_required()
def get_dashboard_recent():
    user_id = int(get_jwt_identity())
    settings = UserSettings.query.filter_by(user_id=user_id).first()
    emission_factor = settings.co2_emission_factor if settings else 0.82
    tariff = settings.electricity_tariff if settings else 0.15

    # Recent 5 energy records
    recent_records = EnergyRecord.query.filter_by(user_id=user_id)\
        .order_by(EnergyRecord.date.desc(), EnergyRecord.id.desc())\
        .limit(5).all()
    records_data = [calculate_record_metrics(r, emission_factor, tariff) for r in recent_records]

    # Recent 5 activities
    recent_activities = Activity.query.filter_by(user_id=user_id)\
        .order_by(Activity.timestamp.desc())\
        .limit(5).all()
    activities_data = [a.to_dict() for a in recent_activities]

    # Top 3 Insights
    insights = generate_insights(user_id, emission_factor, tariff)[:3]

    return jsonify({
        'recent_records': records_data,
        'recent_activities': activities_data,
        'top_insights': insights
    }), 200
