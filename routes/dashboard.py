from flask import Blueprint, jsonify
from models import RFQ, Quotation, PurchaseOrder, Invoice, User, Vendor
from flask_jwt_extended import jwt_required, get_jwt_identity

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_dashboard_summary():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if user and user.role == 'vendor':
        vendor = Vendor.query.filter_by(user_id=user.id).first()
        if vendor:
            active_rfqs = RFQ.query.filter_by(status='published').count()
            pending_approvals = Quotation.query.filter_by(vendor_id=vendor.id, status='pending').count()
            pos = PurchaseOrder.query.join(Quotation).filter(Quotation.vendor_id == vendor.id).all()
            overdue_invoices = Invoice.query.join(PurchaseOrder).join(Quotation).filter(Quotation.vendor_id == vendor.id, Invoice.status == 'overdue').count()
        else:
            active_rfqs = 0
            pending_approvals = 0
            pos = []
            overdue_invoices = 0
    else:
        active_rfqs = RFQ.query.filter_by(status='published').count()
        pending_approvals = Quotation.query.filter_by(status='pending').count()
        pos = PurchaseOrder.query.all()
        overdue_invoices = Invoice.query.filter_by(status='overdue').count()
    
    po_sum = sum(po.quotation.total_price for po in pos if po.quotation)

    recent_pos = []
    for po in pos[:3]: # last 3
        recent_pos.append({
            "po_number": po.po_number,
            "vendor_name": po.quotation.vendor.company_name if po.quotation and po.quotation.vendor else "N/A",
            "amount": po.quotation.total_price if po.quotation else 0,
            "status": po.status
        })

    return jsonify({
        "metrics": {
            "active_rfqs": active_rfqs,
            "pending_approvals": pending_approvals,
            "po_sum": po_sum,
            "overdue_invoices": overdue_invoices
        },
        "recent_pos": recent_pos
    }), 200
