from flask import Blueprint, request, jsonify
from models import Approval, ApprovalStatus, Quotation
from extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity

approval_bp = Blueprint('approval', __name__)

@approval_bp.route('/', methods=['GET'])
@jwt_required()
def get_approvals():
    approvals = Approval.query.all()
    result = []
    for a in approvals:
        result.append({
            "id": a.id,
            "quotation_id": a.quotation_id,
            "vendor_name": a.quotation.vendor.company_name if a.quotation and a.quotation.vendor else "N/A",
            "approver_id": a.approver_id,
            "approver_name": a.approver.name if a.approver else "N/A",
            "status": a.status,
            "remarks": a.remarks
        })
    return jsonify(result), 200

@approval_bp.route('/count', methods=['GET'])
@jwt_required()
def get_approvals_count():
    count = Approval.query.filter_by(status=ApprovalStatus.PENDING).count()
    return jsonify({"count": count}), 200

@approval_bp.route('/<int:approval_id>', methods=['PUT'])
@jwt_required()
def update_approval(approval_id):
    data = request.get_json()
    approval = Approval.query.get(approval_id)
    if not approval:
        return jsonify({"error": "Approval not found"}), 404
        
    approval.status = data.get('status', approval.status)
    approval.remarks = data.get('remarks', approval.remarks)
    
    # If approved, update quotation status
    if approval.status == ApprovalStatus.APPROVED:
        approval.quotation.status = 'selected'
    elif approval.status == ApprovalStatus.REJECTED:
        approval.quotation.status = 'rejected'
        
    db.session.commit()
    return jsonify({"message": "Approval updated"}), 200

@approval_bp.route('/', methods=['POST'])
@jwt_required()
def create_approval():
    data = request.get_json()
    user_id = get_jwt_identity()
    status = data.get('status', ApprovalStatus.PENDING)
    
    new_app = Approval(
        quotation_id=data.get('quotation_id'),
        approver_id=user_id
    )
    new_app.status = status
    new_app.remarks = data.get('comments', '')
    db.session.add(new_app)
    db.session.commit()
    
    # If immediately approved, update quotation and generate PO + Invoice
    if status == ApprovalStatus.APPROVED:
        from models import PurchaseOrder, Invoice
        new_app.quotation.status = 'selected'
        
        po = PurchaseOrder(quotation_id=new_app.quotation_id)
        db.session.add(po)
        db.session.commit()
        
        # Auto generate invoice
        inv = Invoice(
            purchase_order_id=po.id,
            subtotal=new_app.quotation.total_price,
            tax_rate=18.0
        )
        db.session.add(inv)
        db.session.commit()
        
    return jsonify({"message": "Approval request processed", "id": new_app.id}), 201
