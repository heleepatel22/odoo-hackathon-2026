from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User
from extensions import db

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/', methods=['GET'])
@jwt_required()
def get_settings():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    return jsonify({
        "email_notifications": user.email_notifications,
        "browser_notifications": user.browser_notifications,
        "overdue_alerts": user.overdue_alerts
    }), 200

@settings_bp.route('/', methods=['PUT'])
@jwt_required()
def update_settings():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.json
    if 'email_notifications' in data:
        user.email_notifications = data['email_notifications']
    if 'browser_notifications' in data:
        user.browser_notifications = data['browser_notifications']
    if 'overdue_alerts' in data:
        user.overdue_alerts = data['overdue_alerts']
        
    db.session.commit()
    return jsonify({"message": "Settings updated successfully"}), 200
