from flask import Blueprint, request, jsonify
from models import PurchaseOrder, POStatus, Quotation, User, Vendor
from extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity

po_bp = Blueprint('purchase_order', __name__)

@po_bp.route('/', methods=['GET'])
@jwt_required()
def get_pos():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if user and user.role == 'vendor':
        vendor = Vendor.query.filter_by(user_id=user.id).first()
        if vendor:
            pos = PurchaseOrder.query.join(Quotation).filter(Quotation.vendor_id == vendor.id).all()
        else:
            pos = []
    else:
        pos = PurchaseOrder.query.all()
        
    result = []
    for p in pos:
        result.append({
            "id": p.id,
            "po_number": p.po_number,
            "quotation_id": p.quotation_id,
            "vendor_name": p.quotation.vendor.company_name if p.quotation and p.quotation.vendor else "N/A",
            "total_amount": p.quotation.total_price if p.quotation else 0,
            "status": p.status,
            "issued_at": p.issued_at.strftime("%Y-%m-%d") if p.issued_at else "N/A"
        })
    return jsonify(result), 200

@po_bp.route('/', methods=['POST'])
@jwt_required()
def create_po():
    data = request.get_json()
    new_po = PurchaseOrder(
        quotation_id=data.get('quotation_id')
    )
    db.session.add(new_po)
    db.session.commit()
    return jsonify({"message": "PO generated", "po_number": new_po.po_number, "id": new_po.id}), 201
