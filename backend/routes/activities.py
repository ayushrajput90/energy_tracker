from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models.activity import Activity

activities_bp = Blueprint('activities', __name__, url_prefix='/api/activities')

@activities_bp.route('', methods=['GET'])
@jwt_required()
def list_activities():
    user_id = int(get_jwt_identity())
    limit = request.args.get('limit', default=20, type=int)
    page = request.args.get('page', default=1, type=int)

    query = Activity.query.filter_by(user_id=user_id).order_by(Activity.timestamp.desc())
    total_count = query.count()

    activities = query.offset((page - 1) * limit).limit(limit).all()

    return jsonify({
        'activities': [a.to_dict() for a in activities],
        'total': total_count,
        'page': page,
        'limit': limit
    }), 200
