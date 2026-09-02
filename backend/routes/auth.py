from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from backend.extensions import db
from backend.models.user import User
from backend.models.user_settings import UserSettings
from backend.models.activity import Activity
from backend.utils.validators import validate_email, validate_password

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    full_name = data.get('full_name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not full_name:
        return jsonify({'error': 'Full name is required'}), 400

    if not validate_email(email):
        return jsonify({'error': 'A valid email address is required'}), 400

    valid_pass, pass_err = validate_password(password)
    if not valid_pass:
        return jsonify({'error': pass_err}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'An account with this email already exists'}), 409

    # Create User
    new_user = User(full_name=full_name, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.flush() # Populate new_user.id

    # Create Default Settings
    default_settings = UserSettings(user_id=new_user.id)
    db.session.add(default_settings)

    # Log Activity
    Activity.log(user_id=new_user.id, action_type='REGISTER', description='User account created successfully')
    db.session.commit()

    # Generate JWT Token (identity as string for jwt compatibility)
    access_token = create_access_token(identity=str(new_user.id))

    return jsonify({
        'message': 'Registration successful',
        'access_token': access_token,
        'user': new_user.to_dict(),
        'settings': default_settings.to_dict()
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    access_token = create_access_token(identity=str(user.id))
    
    # Ensure settings exist
    if not user.settings:
        settings = UserSettings(user_id=user.id)
        db.session.add(settings)
        db.session.commit()
    else:
        settings = user.settings

    Activity.log(user_id=user.id, action_type='LOGIN', description='User logged in')
    db.session.commit()

    return jsonify({
        'message': 'Login successful',
        'access_token': access_token,
        'user': user.to_dict(),
        'settings': settings.to_dict()
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'user': user.to_dict(),
        'settings': user.settings.to_dict() if user.settings else {}
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    user_id = int(get_jwt_identity())
    Activity.log(user_id=user_id, action_type='LOGOUT', description='User logged out')
    db.session.commit()
    return jsonify({'message': 'Logged out successfully'}), 200
