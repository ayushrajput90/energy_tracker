from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.extensions import db
from backend.models.user import User
from backend.models.user_settings import UserSettings
from backend.models.activity import Activity
from backend.utils.validators import validate_numeric, validate_password

settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')

@settings_bp.route('', methods=['GET'])
@jwt_required()
def get_settings():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    settings = user.settings
    if not settings:
        settings = UserSettings(user_id=user_id)
        db.session.add(settings)
        db.session.commit()

    return jsonify({
        'user': user.to_dict(),
        'settings': settings.to_dict()
    }), 200


@settings_bp.route('', methods=['PUT'])
@jwt_required()
def update_settings():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    settings = UserSettings.query.filter_by(user_id=user_id).first()
    if not settings:
        settings = UserSettings(user_id=user_id)
        db.session.add(settings)

    if 'electricity_tariff' in data:
        v, val, err = validate_numeric(data['electricity_tariff'], 'Electricity tariff')
        if not v or val < 0:
            return jsonify({'error': 'Electricity tariff must be a non-negative number.'}), 400
        settings.electricity_tariff = val

    if 'co2_emission_factor' in data:
        v, val, err = validate_numeric(data['co2_emission_factor'], 'CO2 emission factor')
        if not v or val < 0:
            return jsonify({'error': 'CO2 emission factor must be a non-negative number.'}), 400
        settings.co2_emission_factor = val

    if 'theme' in data and data['theme'] in ['light', 'dark']:
        settings.theme = data['theme']

    CURRENCY_SYMBOLS = {
        'INR': '₹',
        'USD': '$',
        'EUR': '€',
        'GBP': '£'
    }

    if 'currency_code' in data:
        code = str(data['currency_code']).upper().strip()
        if code in CURRENCY_SYMBOLS:
            settings.currency_code = code
            if 'currency_symbol' not in data:
                settings.currency_symbol = CURRENCY_SYMBOLS[code]

    if 'currency_symbol' in data:
        settings.currency_symbol = str(data['currency_symbol'])[:10]

    if 'notification_preferences' in data:
        settings.notification_preferences = bool(data['notification_preferences'])

    if 'unit_preference' in data:
        settings.unit_preference = str(data['unit_preference'])[:10]

    Activity.log(user_id=user_id, action_type='SETTINGS_CHANGED', description='Updated application preferences')
    db.session.commit()

    return jsonify({
        'message': 'Settings updated successfully',
        'settings': settings.to_dict()
    }), 200


@settings_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json() or {}

    if 'full_name' in data and data['full_name'].strip():
        user.full_name = data['full_name'].strip()

    if 'new_password' in data and data['new_password']:
        curr_pass = data.get('current_password', '')
        if not user.check_password(curr_pass):
            return jsonify({'error': 'Current password does not match.'}), 400

        v_pass, p_err = validate_password(data['new_password'])
        if not v_pass:
            return jsonify({'error': p_err}), 400

        user.set_password(data['new_password'])

    Activity.log(user_id=user_id, action_type='PROFILE_UPDATED', description='Profile details updated')
    db.session.commit()

    return jsonify({
        'message': 'Profile updated successfully',
        'user': user.to_dict()
    }), 200
