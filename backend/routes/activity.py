from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import ActivityLog, User

activity_bp = Blueprint('activity', __name__)

@activity_bp.route('/', methods=['GET'])
@jwt_required()
def get_activity():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    query = ActivityLog.query
    if user and user.role == 'vendor':
        query = query.filter_by(user_id=user.id)
        
    # Fetch top 50 recent activity logs
    logs = query.order_by(ActivityLog.timestamp.desc()).limit(50).all()
    
    res = []
    for log in logs:
        res.append({
            "id": log.id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "timestamp": log.timestamp.isoformat(),
            "user": log.user.name if log.user else "System"
        })
        
    return jsonify(res), 200
