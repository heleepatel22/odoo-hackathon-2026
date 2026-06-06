from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from extensions import db
from models import PurchaseOrder, Invoice, Vendor, RFQ, Quotation

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/', methods=['GET'])
@jwt_required()
def get_reports():
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    pos_query = PurchaseOrder.query
    rfq_query = RFQ.query.filter_by(status='active')

    if month and year:
        from sqlalchemy import extract
        pos_query = pos_query.filter(extract('month', PurchaseOrder.issued_at) == month, extract('year', PurchaseOrder.issued_at) == year)
        # Note: Depending on logic, RFQs might also be filtered by created_at. Let's do that.
        rfq_query = rfq_query.filter(extract('month', RFQ.created_at) == month, extract('year', RFQ.created_at) == year)
    
    pos = pos_query.all()
    total_spend = sum(po.quotation.total_price for po in pos if po.quotation)
    
    total_vendors = Vendor.query.count()
    active_rfqs = rfq_query.count()
    
    total_savings = 0
    
    categories_spend = {}
    for po in pos:
        if po.quotation and po.quotation.vendor and po.quotation.vendor.category:
            cat_name = po.quotation.vendor.category.name
            categories_spend[cat_name] = categories_spend.get(cat_name, 0) + po.quotation.total_price
            
    monthly_trend = [0] * 6
    if total_spend > 0:
        monthly_trend[-1] = total_spend

    return jsonify({
        "metrics": {
            "total_spend": total_spend,
            "total_vendors": total_vendors,
            "active_rfqs": active_rfqs,
            "total_savings": total_savings
        },
        "spend_by_category": categories_spend,
        "monthly_trend": monthly_trend
    }), 200
