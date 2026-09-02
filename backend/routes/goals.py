from datetime import datetime, date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.extensions import db
from backend.models.goal import Goal, GOAL_TYPES, GOAL_STATUSES
from backend.models.energy_record import EnergyRecord
from backend.models.user_settings import UserSettings
from backend.models.activity import Activity
from backend.services.calculations import aggregate_record_list
from backend.utils.validators import validate_date, validate_numeric

goals_bp = Blueprint('goals', __name__, url_prefix='/api/goals')

def compute_goal_progress(goal: Goal, user_id: int) -> dict:
    settings = UserSettings.query.filter_by(user_id=user_id).first()
    emission_factor = settings.co2_emission_factor if settings else 0.82
    tariff = settings.electricity_tariff if settings else 0.15

    # Fetch records within goal time window
    records = EnergyRecord.query.filter(
        EnergyRecord.user_id == user_id,
        EnergyRecord.date >= goal.start_date,
        EnergyRecord.date <= goal.end_date
    ).all()

    agg = aggregate_record_list(records, emission_factor, tariff)

    current_val = 0.0
    unit = 'kWh'

    if goal.goal_type == 'Energy Generation':
        current_val = agg['total_generated_kwh']
        unit = 'kWh'
    elif goal.goal_type == 'Renewable Consumption':
        current_val = agg['total_renewable_consumed_kwh']
        unit = 'kWh'
    elif goal.goal_type == 'Renewable Percentage':
        current_val = agg['renewable_percentage']
        unit = '%'
    elif goal.goal_type == 'CO2 Reduction/Avoidance':
        current_val = agg['estimated_co2_avoided_kg']
        unit = 'kg CO2'
    elif goal.goal_type == 'Grid Electricity Displacement':
        current_val = agg['estimated_grid_displaced_kwh']
        unit = 'kWh'
    elif goal.goal_type == 'Cost Savings':
        current_val = agg['estimated_cost_savings']
        unit = '$'

    completion_pct = round((current_val / goal.target_value * 100.0) if goal.target_value > 0 else 0.0, 1)
    remaining_val = max(0.0, round(goal.target_value - current_val, 2))

    # Auto status computation if still Active
    status = goal.status
    today = date.today()
    if status == 'Active':
        if completion_pct >= 100.0:
            status = 'Completed'
        elif today > goal.end_date:
            status = 'Expired'

    return {
        'id': goal.id,
        'user_id': goal.user_id,
        'goal_type': goal.goal_type,
        'target_value': round(goal.target_value, 2),
        'current_value': round(current_val, 2),
        'remaining_value': remaining_val,
        'completion_percentage': min(completion_pct, 100.0),
        'unit': unit,
        'start_date': goal.start_date.isoformat(),
        'end_date': goal.end_date.isoformat(),
        'description': goal.description or '',
        'status': status,
        'created_at': goal.created_at.isoformat() if goal.created_at else None
    }


@goals_bp.route('', methods=['GET'])
@jwt_required()
def list_goals():
    user_id = int(get_jwt_identity())
    goals = Goal.query.filter_by(user_id=user_id).order_by(Goal.end_date.asc(), Goal.id.desc()).all()
    data = [compute_goal_progress(g, user_id) for g in goals]
    return jsonify({'goals': data}), 200


@goals_bp.route('', methods=['POST'])
@jwt_required()
def create_goal():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    goal_type = data.get('goal_type', '').strip()
    if goal_type not in GOAL_TYPES:
        return jsonify({'error': f'Invalid goal type. Must be one of {GOAL_TYPES}'}), 400

    v_target, target_val, target_err = validate_numeric(data.get('target_value'), 'Target value')
    if not v_target or target_val <= 0:
        return jsonify({'error': 'Target value must be greater than zero.'}), 400

    v_sdate, s_err = validate_date(data.get('start_date'))
    if not v_sdate:
        return jsonify({'error': f'Start date error: {s_err}'}), 400

    v_edate, e_err = validate_date(data.get('end_date'))
    if not v_edate:
        return jsonify({'error': f'End date error: {e_err}'}), 400

    start_date = datetime.strptime(data['start_date'], "%Y-%m-%d").date()
    end_date = datetime.strptime(data['end_date'], "%Y-%m-%d").date()

    if end_date < start_date:
        return jsonify({'error': 'End date cannot be earlier than start date.'}), 400

    goal = Goal(
        user_id=user_id,
        goal_type=goal_type,
        target_value=target_val,
        start_date=start_date,
        end_date=end_date,
        description=data.get('description', '').strip(),
        status=data.get('status', 'Active')
    )
    db.session.add(goal)

    Activity.log(
        user_id=user_id,
        action_type='CREATE_GOAL',
        description=f'Created new goal: {goal_type} ({target_val})'
    )
    db.session.commit()

    return jsonify({
        'message': 'Goal created successfully',
        'goal': compute_goal_progress(goal, user_id)
    }), 201


@goals_bp.route('/<int:goal_id>', methods=['GET'])
@jwt_required()
def get_goal(goal_id: int):
    user_id = int(get_jwt_identity())
    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()
    if not goal:
        return jsonify({'error': 'Goal not found'}), 404
    return jsonify({'goal': compute_goal_progress(goal, user_id)}), 200


@goals_bp.route('/<int:goal_id>', methods=['PUT'])
@jwt_required()
def update_goal(goal_id: int):
    user_id = int(get_jwt_identity())
    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()
    if not goal:
        return jsonify({'error': 'Goal not found'}), 404

    data = request.get_json() or {}

    if 'goal_type' in data and data['goal_type'] in GOAL_TYPES:
        goal.goal_type = data['goal_type']

    if 'target_value' in data:
        v_target, target_val, target_err = validate_numeric(data['target_value'], 'Target value')
        if not v_target or target_val <= 0:
            return jsonify({'error': 'Target value must be greater than zero.'}), 400
        goal.target_value = target_val

    if 'start_date' in data:
        v_sdate, s_err = validate_date(data['start_date'])
        if not v_sdate:
            return jsonify({'error': s_err}), 400
        goal.start_date = datetime.strptime(data['start_date'], "%Y-%m-%d").date()

    if 'end_date' in data:
        v_edate, e_err = validate_date(data['end_date'])
        if not v_edate:
            return jsonify({'error': e_err}), 400
        goal.end_date = datetime.strptime(data['end_date'], "%Y-%m-%d").date()

    if goal.end_date < goal.start_date:
        return jsonify({'error': 'End date cannot be earlier than start date.'}), 400

    if 'description' in data:
        goal.description = data['description'].strip()

    if 'status' in data and data['status'] in GOAL_STATUSES:
        goal.status = data['status']

    Activity.log(
        user_id=user_id,
        action_type='UPDATE_GOAL',
        description=f'Updated goal #{goal.id}: {goal.goal_type}'
    )
    db.session.commit()

    return jsonify({
        'message': 'Goal updated successfully',
        'goal': compute_goal_progress(goal, user_id)
    }), 200


@goals_bp.route('/<int:goal_id>', methods=['DELETE'])
@jwt_required()
def delete_goal(goal_id: int):
    user_id = int(get_jwt_identity())
    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()
    if not goal:
        return jsonify({'error': 'Goal not found'}), 404

    gtype = goal.goal_type
    db.session.delete(goal)
    Activity.log(
        user_id=user_id,
        action_type='DELETE_GOAL',
        description=f'Deleted goal: {gtype}'
    )
    db.session.commit()

    return jsonify({'message': 'Goal deleted successfully'}), 200
