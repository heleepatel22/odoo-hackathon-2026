from flask import Blueprint, request, jsonify
from models import Invoice, InvoiceStatus, PurchaseOrder, Quotation, User, Vendor
from extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity

invoice_bp = Blueprint('invoice', __name__)

@invoice_bp.route('/', methods=['GET'])
@jwt_required()
def get_invoices():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if user and user.role == 'vendor':
        vendor = Vendor.query.filter_by(user_id=user.id).first()
        if vendor:
            invoices = Invoice.query.join(PurchaseOrder).join(Quotation).filter(Quotation.vendor_id == vendor.id).all()
        else:
            invoices = []
    else:
        invoices = Invoice.query.all()
        
    result = []
    for i in invoices:
        result.append({
            "id": i.id,
            "invoice_number": i.invoice_number,
            "po_number": i.purchase_order.po_number if i.purchase_order else "N/A",
            "vendor_name": i.purchase_order.quotation.vendor.company_name if i.purchase_order and i.purchase_order.quotation and i.purchase_order.quotation.vendor else "N/A",
            "subtotal": i.subtotal,
            "tax_amount": i.tax_amount,
            "total_amount": i.total_amount,
            "status": i.status,
            "issued_at": i.issued_at.strftime("%Y-%m-%d") if i.issued_at else "N/A"
        })
    return jsonify(result), 200

@invoice_bp.route('/', methods=['POST'])
@jwt_required()
def create_invoice():
    data = request.get_json()
    new_inv = Invoice(
        purchase_order_id=data.get('purchase_order_id'),
        subtotal=data.get('subtotal', 0),
        tax_rate=data.get('tax_rate', 18.0),
        notes=data.get('notes')
    )
    db.session.add(new_inv)
    db.session.commit()
    return jsonify({"message": "Invoice generated", "invoice_number": new_inv.invoice_number, "id": new_inv.id}), 201

@invoice_bp.route('/<int:invoice_id>/pay', methods=['POST'])
@jwt_required()
def pay_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.status = InvoiceStatus.PAID
    db.session.commit()
    return jsonify({"message": "Invoice marked as paid"}), 200

@invoice_bp.route('/<int:invoice_id>/email', methods=['POST'])
@jwt_required()
def email_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    po = invoice.purchase_order
    vendor = po.quotation.vendor if (po and po.quotation) else None
    
    if not vendor or not vendor.email:
        return jsonify({"error": "Vendor email not found"}), 400
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    reply_email = user.email if user else None
        
    from utils import send_email
    subject = f"Invoice {invoice.invoice_number} from VendorBridge"
    body = f"<h2>New Invoice</h2><p>Please find the details for invoice {invoice.invoice_number} amounting to ₹{invoice.total_amount}.</p>"
    
    success = send_email(vendor.email, subject, body, reply_to=reply_email)
    if success:
        return jsonify({"message": "Invoice emailed successfully"}), 200
    return jsonify({"error": "Failed to send email"}), 500
