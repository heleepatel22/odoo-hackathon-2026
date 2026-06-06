from flask import Blueprint, request, jsonify
from models import Vendor, VendorCategory
from extensions import db
from flask_jwt_extended import jwt_required

vendor_bp = Blueprint('vendor', __name__)

@vendor_bp.route('/', methods=['GET'])
@jwt_required()
def get_vendors():
    vendors = Vendor.query.all()
    result = []
    for v in vendors:
        result.append({
            "id": v.id,
            "company_name": v.company_name,
            "contact_name": v.contact_name,
            "email": v.email,
            "phone": v.phone,
            "status": v.status,
            "rating": v.rating,
            "category": v.category.name if v.category else None
        })
    return jsonify(result), 200

@vendor_bp.route('/', methods=['POST'])
@jwt_required()
def create_vendor():
    data = request.get_json()
    new_vendor = Vendor(
        company_name=data.get('company_name'),
        email=data.get('email'),
        contact_name=data.get('contact_name'),
        phone=data.get('phone'),
        address=data.get('address'),
        gst_number=data.get('gst_number')
    )
    if 'status' in data:
        new_vendor.status = data['status']
    db.session.add(new_vendor)
    db.session.commit()
    return jsonify({"message": "Vendor created successfully", "id": new_vendor.id}), 201

@vendor_bp.route('/<int:vendor_id>', methods=['DELETE'])
@jwt_required()
def delete_vendor(vendor_id):
    v = Vendor.query.get(vendor_id)
    if not v:
        return jsonify({"error": "Vendor not found"}), 404
    db.session.delete(v)
    db.session.commit()
    return jsonify({"message": "Vendor deleted"}), 200
