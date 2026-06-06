from flask import Blueprint, request, jsonify
from models import RFQ, RFQItem, RFQStatus, User
from extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

rfq_bp = Blueprint('rfq', __name__)

@rfq_bp.route('/', methods=['GET'])
@jwt_required()
def get_rfqs():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if user and user.role == 'vendor':
        rfqs = RFQ.query.filter_by(status=RFQStatus.PUBLISHED).all()
    else:
        rfqs = RFQ.query.all()
        
    result = []
    for r in rfqs:
        result.append({
            "id": r.id,
            "title": r.title,
            "status": r.status,
            "deadline": r.deadline.strftime("%Y-%m-%d"),
            "items_count": len(r.items),
            "vendors_count": len(r.vendors)
        })
    return jsonify(result), 200

@rfq_bp.route('/', methods=['POST'])
@jwt_required()
def create_rfq():
    data = request.get_json()
    user_id = get_jwt_identity()

    deadline_str = data.get('deadline')
    deadline = datetime.strptime(deadline_str, "%Y-%m-%d") if deadline_str else datetime.utcnow()

    new_rfq = RFQ(
        title=data.get('title'),
        deadline=deadline,
        status=RFQStatus.PUBLISHED,
        created_by_id=user_id,
        description=data.get('description'),
        attachments=data.get('attachments')
    )
    db.session.add(new_rfq)
    db.session.commit()

    # Add items if provided
    items = data.get('items', [])
    for item in items:
        rfq_item = RFQItem(
            rfq_id=new_rfq.id,
            product_name=item.get('product_name'),
            quantity=item.get('quantity', 1),
            unit=item.get('unit'),
            description=item.get('description')
        )
        db.session.add(rfq_item)
    db.session.commit()

    return jsonify({"message": "RFQ created successfully", "id": new_rfq.id}), 201

@rfq_bp.route('/<int:rfq_id>', methods=['DELETE'])
@jwt_required()
def delete_rfq(rfq_id):
    r = RFQ.query.get(rfq_id)
    if not r:
        return jsonify({"error": "RFQ not found"}), 404
    db.session.delete(r)
    db.session.commit()
    return jsonify({"message": "RFQ deleted"}), 200
