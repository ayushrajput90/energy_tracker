from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.extensions import db
from backend.models.renewable_source import RenewableSource, SourceCapacityHistory
from backend.models.energy_record import RENEWABLE_SOURCES
from backend.models.activity import Activity
from backend.utils.validators import validate_date, validate_numeric

sources_bp = Blueprint('sources', __name__, url_prefix='/api/sources')

@sources_bp.route('', methods=['GET'])
@jwt_required()
def list_sources():
    user_id = int(get_jwt_identity())
    sources = RenewableSource.query.filter_by(user_id=user_id).order_by(RenewableSource.id.asc()).all()
    
    total_capacity = sum(s.installed_capacity_kw for s in sources if s.active)
    total_expected_gen = sum(s.expected_daily_generation_kwh for s in sources if s.active)
    
    return jsonify({
        'sources': [s.to_dict() for s in sources],
        'total_installed_capacity_kw': round(total_capacity, 2),
        'total_expected_daily_generation_kwh': round(total_expected_gen, 2),
        'active_count': len([s for s in sources if s.active]),
        'total_count': len(sources)
    }), 200


@sources_bp.route('', methods=['POST'])
@jwt_required()
def create_source():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    source_type = data.get('source_type', '').strip()
    if not source_type:
        return jsonify({'error': 'Renewable source type is required.'}), 400
    if source_type not in RENEWABLE_SOURCES:
        return jsonify({'error': f"Invalid source type. Allowed: {', '.join(RENEWABLE_SOURCES)}"}), 400

    v_cap, cap_val, cap_err = validate_numeric(data.get('installed_capacity_kw', 0), 'Installed capacity')
    if not v_cap or cap_val < 0:
        return jsonify({'error': cap_err or 'Installed capacity must be a non-negative number.'}), 400

    v_gen, gen_val, gen_err = validate_numeric(data.get('expected_daily_generation_kwh', 0), 'Expected daily generation')
    if not v_gen or gen_val < 0:
        return jsonify({'error': gen_err or 'Expected daily generation must be a non-negative number.'}), 400

    effective_from_str = data.get('effective_from')
    if effective_from_str:
        valid_date, date_err = validate_date(effective_from_str)
        if not valid_date:
            return jsonify({'error': date_err}), 400
        eff_date = datetime.strptime(effective_from_str, '%Y-%m-%d').date()
    else:
        eff_date = date.today()

    active = bool(data.get('active', True))

    source = RenewableSource(
        user_id=user_id,
        source_type=source_type,
        installed_capacity_kw=cap_val,
        expected_daily_generation_kwh=gen_val,
        effective_from=eff_date,
        active=active
    )
    db.session.add(source)
    db.session.flush() # obtain source.id

    # Create initial capacity history record
    initial_history = SourceCapacityHistory(
        source_id=source.id,
        capacity_kw=cap_val,
        expected_daily_generation_kwh=gen_val,
        effective_from=eff_date,
        effective_to=None
    )
    db.session.add(initial_history)

    Activity.log(
        user_id=user_id,
        action_type='CONFIG_SOURCE',
        description=f"Configured {source_type} source: {cap_val:.1f} kW, expected {gen_val:.1f} kWh/day from {eff_date.isoformat()}"
    )
    db.session.commit()

    return jsonify({
        'message': f"{source_type} source configuration saved successfully.",
        'source': source.to_dict()
    }), 201


@sources_bp.route('/<int:source_id>', methods=['GET'])
@jwt_required()
def get_source(source_id: int):
    user_id = int(get_jwt_identity())
    source = RenewableSource.query.filter_by(id=source_id, user_id=user_id).first()
    if not source:
        return jsonify({'error': 'Source not found.'}), 404

    history = SourceCapacityHistory.query.filter_by(source_id=source.id)\
        .order_by(SourceCapacityHistory.effective_from.asc()).all()

    data = source.to_dict()
    data['history'] = [h.to_dict() for h in history]
    return jsonify({'source': data}), 200


@sources_bp.route('/<int:source_id>', methods=['PUT'])
@jwt_required()
def update_source(source_id: int):
    user_id = int(get_jwt_identity())
    source = RenewableSource.query.filter_by(id=source_id, user_id=user_id).first()
    if not source:
        return jsonify({'error': 'Source not found.'}), 404

    data = request.get_json() or {}

    if 'source_type' in data and data['source_type'].strip():
        st = data['source_type'].strip()
        if st in RENEWABLE_SOURCES:
            source.source_type = st

    if 'active' in data:
        source.active = bool(data['active'])

    cap_changed = False
    gen_changed = False

    new_cap = source.installed_capacity_kw
    if 'installed_capacity_kw' in data:
        v_cap, cap_val, cap_err = validate_numeric(data['installed_capacity_kw'], 'Installed capacity')
        if not v_cap or cap_val < 0:
            return jsonify({'error': cap_err or 'Installed capacity must be non-negative.'}), 400
        if round(cap_val, 2) != round(source.installed_capacity_kw, 2):
            new_cap = cap_val
            cap_changed = True

    new_gen = source.expected_daily_generation_kwh
    if 'expected_daily_generation_kwh' in data:
        v_gen, gen_val, gen_err = validate_numeric(data['expected_daily_generation_kwh'], 'Expected daily generation')
        if not v_gen or gen_val < 0:
            return jsonify({'error': gen_err or 'Expected daily generation must be non-negative.'}), 400
        if round(gen_val, 2) != round(source.expected_daily_generation_kwh, 2):
            new_gen = gen_val
            gen_changed = True

    # If capacity or generation changed, preserve historical config by creating a new history record
    if cap_changed or gen_changed:
        effective_from_str = data.get('effective_from')
        if effective_from_str:
            valid_date, date_err = validate_date(effective_from_str)
            if not valid_date:
                return jsonify({'error': date_err}), 400
            eff_date = datetime.strptime(effective_from_str, '%Y-%m-%d').date()
        else:
            eff_date = date.today()

        # Update previous latest history record's effective_to to (eff_date - 1 day)
        prev_history = SourceCapacityHistory.query.filter_by(source_id=source.id, effective_to=None).first()
        if prev_history and prev_history.effective_from < eff_date:
            prev_history.effective_to = eff_date - timedelta(days=1)
        elif prev_history and prev_history.effective_from == eff_date:
            # Overwrite same day config
            prev_history.capacity_kw = new_cap
            prev_history.expected_daily_generation_kwh = new_gen
            source.installed_capacity_kw = new_cap
            source.expected_daily_generation_kwh = new_gen
            db.session.commit()
            return jsonify({'message': 'Source configuration updated.', 'source': source.to_dict()}), 200

        # Insert new history entry
        new_history = SourceCapacityHistory(
            source_id=source.id,
            capacity_kw=new_cap,
            expected_daily_generation_kwh=new_gen,
            effective_from=eff_date,
            effective_to=None
        )
        db.session.add(new_history)

        source.installed_capacity_kw = new_cap
        source.expected_daily_generation_kwh = new_gen

    Activity.log(
        user_id=user_id,
        action_type='UPDATE_SOURCE',
        description=f"Updated {source.source_type} source config: {source.installed_capacity_kw:.1f} kW, {source.expected_daily_generation_kwh:.1f} kWh/day"
    )
    db.session.commit()

    return jsonify({
        'message': 'Source configuration updated successfully.',
        'source': source.to_dict()
    }), 200


@sources_bp.route('/<int:source_id>', methods=['DELETE'])
@jwt_required()
def delete_source(source_id: int):
    user_id = int(get_jwt_identity())
    source = RenewableSource.query.filter_by(id=source_id, user_id=user_id).first()
    if not source:
        return jsonify({'error': 'Source not found.'}), 404

    src_type = source.source_type
    db.session.delete(source)
    Activity.log(
        user_id=user_id,
        action_type='DELETE_SOURCE',
        description=f"Deleted {src_type} source configuration"
    )
    db.session.commit()

    return jsonify({'message': f"{src_type} source configuration deleted successfully."}), 200


@sources_bp.route('/<int:source_id>/history', methods=['GET'])
@jwt_required()
def get_source_history(source_id: int):
    user_id = int(get_jwt_identity())
    source = RenewableSource.query.filter_by(id=source_id, user_id=user_id).first()
    if not source:
        return jsonify({'error': 'Source not found.'}), 404

    history = SourceCapacityHistory.query.filter_by(source_id=source.id)\
        .order_by(SourceCapacityHistory.effective_from.asc()).all()

    return jsonify({
        'source': source.to_dict(),
        'history': [h.to_dict() for h in history]
    }), 200
