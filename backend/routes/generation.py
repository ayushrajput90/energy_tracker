from datetime import datetime, date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.extensions import db
from backend.models.renewable_source import RenewableSource
from backend.models.generation_override import DailyGenerationOverride
from backend.models.energy_record import EnergyRecord
from backend.models.user_settings import UserSettings
from backend.models.activity import Activity
from backend.services.aggregation import (
    parse_date_range,
    get_filtered_records_query,
    get_daily_generation_telemetry,
    aggregate_records_by_time_period,
    aggregate_by_source
)
from backend.services.calculations import aggregate_record_list
from backend.utils.validators import validate_date, validate_numeric

generation_bp = Blueprint('generation', __name__, url_prefix='/api/generation')

@generation_bp.route('', methods=['GET'])
@jwt_required()
def get_generation_overview():
    user_id = int(get_jwt_identity())
    date_str = request.args.get('date')
    
    if date_str:
        valid_date, date_err = validate_date(date_str)
        if not valid_date:
            return jsonify({'error': date_err}), 400
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        target_date = date.today()

    telemetry = get_daily_generation_telemetry(user_id, target_date)
    return jsonify(telemetry), 200


@generation_bp.route('/daily', methods=['GET'])
@jwt_required()
def get_daily_generation():
    user_id = int(get_jwt_identity())
    time_filter = request.args.get('time_filter', 'this_month')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    start_date, end_date = parse_date_range(time_filter, start_date_str, end_date_str)
    records = get_filtered_records_query(user_id, start_date=start_date, end_date=end_date).order_by(EnergyRecord.date.asc()).all()

    settings = UserSettings.query.filter_by(user_id=user_id).first()
    emission_factor = settings.co2_emission_factor if settings else 0.82
    tariff = settings.electricity_tariff if settings else 0.15

    daily_list = aggregate_records_by_time_period(records, period='daily', emission_factor=emission_factor, default_tariff=tariff)
    summary = aggregate_record_list(records, emission_factor=emission_factor, default_tariff=tariff)

    return jsonify({
        'period': 'daily',
        'summary': summary,
        'data': daily_list
    }), 200


@generation_bp.route('/weekly', methods=['GET'])
@jwt_required()
def get_weekly_generation():
    user_id = int(get_jwt_identity())
    time_filter = request.args.get('time_filter', 'this_year')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    start_date, end_date = parse_date_range(time_filter, start_date_str, end_date_str)
    records = get_filtered_records_query(user_id, start_date=start_date, end_date=end_date).order_by(EnergyRecord.date.asc()).all()

    settings = UserSettings.query.filter_by(user_id=user_id).first()
    emission_factor = settings.co2_emission_factor if settings else 0.82
    tariff = settings.electricity_tariff if settings else 0.15

    weekly_list = aggregate_records_by_time_period(records, period='weekly', emission_factor=emission_factor, default_tariff=tariff)
    summary = aggregate_record_list(records, emission_factor=emission_factor, default_tariff=tariff)

    return jsonify({
        'period': 'weekly',
        'summary': summary,
        'data': weekly_list
    }), 200


@generation_bp.route('/monthly', methods=['GET'])
@jwt_required()
def get_monthly_generation():
    user_id = int(get_jwt_identity())
    time_filter = request.args.get('time_filter', 'this_year')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    start_date, end_date = parse_date_range(time_filter, start_date_str, end_date_str)
    records = get_filtered_records_query(user_id, start_date=start_date, end_date=end_date).order_by(EnergyRecord.date.asc()).all()

    settings = UserSettings.query.filter_by(user_id=user_id).first()
    emission_factor = settings.co2_emission_factor if settings else 0.82
    tariff = settings.electricity_tariff if settings else 0.15

    monthly_list = aggregate_records_by_time_period(records, period='monthly', emission_factor=emission_factor, default_tariff=tariff)
    summary = aggregate_record_list(records, emission_factor=emission_factor, default_tariff=tariff)

    return jsonify({
        'period': 'monthly',
        'summary': summary,
        'data': monthly_list
    }), 200


@generation_bp.route('/yearly', methods=['GET'])
@jwt_required()
def get_yearly_generation():
    user_id = int(get_jwt_identity())
    records = EnergyRecord.query.filter_by(user_id=user_id).order_by(EnergyRecord.date.asc()).all()

    settings = UserSettings.query.filter_by(user_id=user_id).first()
    emission_factor = settings.co2_emission_factor if settings else 0.82
    tariff = settings.electricity_tariff if settings else 0.15

    yearly_list = aggregate_records_by_time_period(records, period='yearly', emission_factor=emission_factor, default_tariff=tariff)
    summary = aggregate_record_list(records, emission_factor=emission_factor, default_tariff=tariff)

    return jsonify({
        'period': 'yearly',
        'summary': summary,
        'data': yearly_list
    }), 200


# ==============================================================
# DAILY GENERATION OVERRIDES CRUD
# ==============================================================

@generation_bp.route('/overrides', methods=['GET'])
@jwt_required()
def list_overrides():
    user_id = int(get_jwt_identity())
    date_str = request.args.get('date')
    source_id = request.args.get('source_id', type=int)

    query = DailyGenerationOverride.query.filter_by(user_id=user_id)
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter(DailyGenerationOverride.date == target_date)
        except ValueError:
            pass
    if source_id:
        query = query.filter(DailyGenerationOverride.source_id == source_id)

    overrides = query.order_by(DailyGenerationOverride.date.desc()).all()
    return jsonify({
        'overrides': [o.to_dict() for o in overrides],
        'total_count': len(overrides)
    }), 200


@generation_bp.route('/overrides', methods=['POST'])
@jwt_required()
def create_override():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    date_str = data.get('date')
    valid_date, date_err = validate_date(date_str)
    if not valid_date:
        return jsonify({'error': date_err}), 400
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()

    source_id = data.get('source_id')
    source_type = data.get('source_type', '').strip()

    source = None
    if source_id:
        source = RenewableSource.query.filter_by(id=int(source_id), user_id=user_id).first()
    elif source_type:
        source = RenewableSource.query.filter_by(source_type=source_type, user_id=user_id, active=True).first()

    if not source:
        return jsonify({'error': 'Configured renewable source not found for this user.'}), 404

    v_ov, override_val, ov_err = validate_numeric(data.get('override_generation_kwh', 0), 'Override generation')
    if not v_ov or override_val < 0:
        return jsonify({'error': ov_err or 'Override generation must be a non-negative number.'}), 400

    reason = (data.get('reason') or '').strip()

    # Get automatic expected value for that date
    config = source.get_effective_config_for_date(target_date)
    auto_val = float(config['expected_daily_generation_kwh']) if config else source.expected_daily_generation_kwh

    # Check if override already exists for this (user, source, date)
    existing = DailyGenerationOverride.query.filter_by(
        user_id=user_id,
        source_id=source.id,
        date=target_date
    ).first()

    if existing:
        existing.override_generation_kwh = override_val
        existing.automatic_generation_kwh = auto_val
        existing.reason = reason
        override_obj = existing
    else:
        override_obj = DailyGenerationOverride(
            user_id=user_id,
            source_id=source.id,
            date=target_date,
            automatic_generation_kwh=auto_val,
            override_generation_kwh=override_val,
            reason=reason
        )
        db.session.add(override_obj)

    Activity.log(
        user_id=user_id,
        action_type='GENERATION_OVERRIDE',
        description=f"Manual override for {source.source_type} on {date_str}: {override_val:.1f} kWh (Auto: {auto_val:.1f} kWh, Reason: {reason or 'None'})"
    )
    db.session.commit()

    return jsonify({
        'message': f"Override saved for {source.source_type} on {date_str}.",
        'override': override_obj.to_dict(),
        'breakdown': {
            'automatic_generation_kwh': round(auto_val, 2),
            'override_generation_kwh': round(override_val, 2),
            'final_generation_kwh': round(override_val, 2)
        }
    }), 201


@generation_bp.route('/overrides/<int:override_id>', methods=['PUT'])
@jwt_required()
def update_override(override_id: int):
    user_id = int(get_jwt_identity())
    override_obj = DailyGenerationOverride.query.filter_by(id=override_id, user_id=user_id).first()
    if not override_obj:
        return jsonify({'error': 'Override not found.'}), 404

    data = request.get_json() or {}

    if 'override_generation_kwh' in data:
        v, val, err = validate_numeric(data['override_generation_kwh'], 'Override generation')
        if not v or val < 0:
            return jsonify({'error': err or 'Override generation must be non-negative.'}), 400
        override_obj.override_generation_kwh = val

    if 'reason' in data:
        override_obj.reason = data['reason'].strip()

    db.session.commit()
    return jsonify({
        'message': 'Override updated successfully.',
        'override': override_obj.to_dict()
    }), 200


@generation_bp.route('/overrides/<int:override_id>', methods=['DELETE'])
@jwt_required()
def delete_override(override_id: int):
    user_id = int(get_jwt_identity())
    override_obj = DailyGenerationOverride.query.filter_by(id=override_id, user_id=user_id).first()
    if not override_obj:
        return jsonify({'error': 'Override not found.'}), 404

    src_name = override_obj.source.source_type if override_obj.source else 'Source'
    d_str = override_obj.date.isoformat()

    db.session.delete(override_obj)
    Activity.log(
        user_id=user_id,
        action_type='DELETE_OVERRIDE',
        description=f"Deleted manual override for {src_name} on {d_str} (reverted to automatic generation)"
    )
    db.session.commit()

    return jsonify({'message': f"Override removed for {src_name} on {d_str}. Automatic generation restored."}), 200
