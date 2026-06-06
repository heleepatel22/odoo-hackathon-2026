from flask import Blueprint, request, jsonify
from models import Quotation, QuotationItem, QuotationStatus, RFQ, User, Vendor
from extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity

quotation_bp = Blueprint('quotation', __name__)

@quotation_bp.route('/', methods=['GET'])
@jwt_required()
def get_quotations():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if user and user.role == 'vendor':
        vendor = Vendor.query.filter_by(user_id=user.id).first()
        if vendor:
            quotations = Quotation.query.filter_by(vendor_id=vendor.id).all()
        else:
            quotations = []
    else:
        quotations = Quotation.query.all()
        
    result = []
    for q in quotations:
        result.append({
            "id": q.id,
            "rfq_id": q.rfq_id,
            "rfq_title": q.rfq.title if q.rfq else "N/A",
            "vendor_id": q.vendor_id,
            "vendor_name": q.vendor.company_name if q.vendor else "N/A",
            "total_price": q.total_price,
            "status": q.status,
            "submitted_at": q.submitted_at.strftime("%Y-%m-%d") if q.submitted_at else "N/A"
        })
    return jsonify(result), 200

@quotation_bp.route('/', methods=['POST'])
@jwt_required()
def submit_quotation():
    data = request.get_json()
    
    new_quotation = Quotation(
        rfq_id=data.get('rfq_id'),
        vendor_id=data.get('vendor_id'),
        total_price=data.get('total_price', 0),
        delivery_timeline=data.get('delivery_timeline'),
        notes=data.get('notes')
    )
    db.session.add(new_quotation)
    db.session.commit()

    items = data.get('items', [])
    for item in items:
        q_item = QuotationItem(
            quotation_id=new_quotation.id,
            rfq_item_id=item.get('rfq_item_id'),
            unit_price=item.get('unit_price', 0),
            quantity=item.get('quantity', 1)
        )
        db.session.add(q_item)
    db.session.commit()

    return jsonify({"message": "Quotation submitted successfully", "id": new_quotation.id}), 201

@quotation_bp.route('/compare', methods=['GET'])
@jwt_required()
def compare_quotations():
    rfq_id = request.args.get('rfq_id', type=int)
    
    if rfq_id:
        rfq = RFQ.query.get(rfq_id)
    else:
        # Find the latest RFQ that has at least one quotation
        # We can sort by ID descending
        rfqs = RFQ.query.order_by(RFQ.id.desc()).all()
        rfq = next((r for r in rfqs if len(r.quotations) > 0), None)
        
    if not rfq:
        return jsonify({"message": "No RFQ with quotations found"}), 404
        
    quots = []
    for q in rfq.quotations:
        quots.append({
            "id": q.id,
            "vendor_name": q.vendor.company_name if q.vendor else "Unknown",
            "vendor_rating": q.vendor.rating if q.vendor else 0,
            "total_price": q.total_price,
            "delivery_timeline": q.delivery_timeline or "N/A",
            "notes": q.notes or ""
        })
        
    # Sort quotations by total_price ascending (best price first)
    quots.sort(key=lambda x: x['total_price'])
    
    return jsonify({
        "rfq": {
            "id": rfq.id,
            "title": rfq.title,
            "quotations_count": len(quots)
        },
        "quotations": quots
    }), 200
