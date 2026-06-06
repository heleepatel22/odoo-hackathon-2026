from flask import Flask, request, jsonify
from extensions import db
from config import Config
from flask_jwt_extended import JWTManager, create_access_token
from models import User, Role
from flask_cors import CORS


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    db.init_app(app)

    # Import all models so db.create_all() knows about every table
    from models import (
        Role, Permission,           # Role/Permission FIRST — User FK depends on them
        User,
        VendorCategory, Vendor,
        RFQ, RFQItem,
        Quotation, QuotationItem,
        Approval,
        PurchaseOrder,
        Invoice,
        Notification,
        ActivityLog,
    )
    app.config["JWT_SECRET_KEY"] = "vendorbridge-jwt-secret"

    JWTManager(app)
    with app.app_context():
        db.create_all()
        _seed_default_roles()
        print('✅ All tables created.')

    return app

  


def _seed_default_roles():
    """Insert the four default roles + their permissions if they don't exist yet.

    BUG 5 FIX: the original version called db.session.flush() after adding the
    Role but before adding its Permissions, which is correct.  However it did NOT
    wrap anything in a try/except, so a crash halfway through (e.g. duplicate
    constraint on a second run) would leave the session dirty.  We now wrap the
    whole block in try/except and rollback on error.
    """
    from models import Role, Permission
    from extensions import db

    defaults = [
        {
            'name': 'admin',
            'label': 'Administrator',
            'description': 'Full access to all resources.',
            'permissions': [
                ('users',           'create'), ('users',           'read'),
                ('users',           'update'), ('users',           'delete'),
                ('vendors',         'create'), ('vendors',         'read'),
                ('vendors',         'update'), ('vendors',         'delete'),
                ('rfqs',            'create'), ('rfqs',            'read'),
                ('rfqs',            'update'), ('rfqs',            'delete'),
                ('quotations',      'create'), ('quotations',      'read'),
                ('quotations',      'update'), ('quotations',      'delete'),
                ('approvals',       'create'), ('approvals',       'read'),
                ('approvals',       'update'),
                ('purchase_orders', 'create'), ('purchase_orders', 'read'),
                ('purchase_orders', 'update'),
                ('invoices',        'create'), ('invoices',        'read'),
                ('invoices',        'update'),
                ('notifications',   'read'),
                ('activity_logs',   'read'),
            ],
        },
        {
            'name': 'procurement_officer',
            'label': 'Procurement Officer',
            'description': 'Creates and manages RFQs and quotations.',
            'permissions': [
                ('vendors',       'read'),
                ('rfqs',          'create'), ('rfqs',     'read'),
                ('rfqs',          'update'), ('rfqs',     'delete'),
                ('quotations',    'read'),   ('quotations', 'update'),
                ('notifications', 'read'),
            ],
        },
        {
            'name': 'manager',
            'label': 'Manager',
            'description': 'Reviews and approves quotations.',
            'permissions': [
                ('rfqs',            'read'),
                ('quotations',      'read'),
                ('approvals',       'create'), ('approvals', 'read'), ('approvals', 'update'),
                ('purchase_orders', 'read'),
                ('invoices',        'read'),
                ('notifications',   'read'),
            ],
        },
        {
            'name': 'vendor',
            'label': 'Vendor',
            'description': 'Submits quotations against published RFQs.',
            'permissions': [
                ('rfqs',          'read'),
                ('quotations',    'create'), ('quotations', 'read'), ('quotations', 'update'),
                ('notifications', 'read'),
            ],
        },
    ]

    try:
        for role_data in defaults:
            role = Role.query.filter_by(name=role_data['name']).first()
            if not role:
                role = Role(
                    name=role_data['name'],
                    label=role_data['label'],
                    description=role_data['description'],
                )
                db.session.add(role)
                db.session.flush()   # get role.id before adding permissions

                for resource, action in role_data['permissions']:
                    db.session.add(
                        Permission(role_id=role.id, resource=resource, action=action)
                    )

        db.session.commit()
        print('✅ Default roles seeded.')

    except Exception as e:
        db.session.rollback()
        print(f'⚠️  Role seeding failed (already seeded or error): {e}')


# BUG 6 FIX: create_app() was called at module level unconditionally.
# This means every `from app import something` (e.g. in tests or CLI tools)
# triggers a full app + DB creation.  Guarding with __name__ check is correct
# for scripts, but for a proper Flask app the app factory pattern means you
# should NOT call create_app() at module level — use `flask run` or a WSGI
# entry point instead.  Kept here only for `python app.py` convenience.
app = create_app()

@app.route('/')
def home():
    return "VendorBridge Running"

@app.route('/api/auth/register', methods=['POST'])
def register():

    data = request.get_json()

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role_name = data.get('role', 'procurement_officer')

    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        return jsonify({
            "message": "Email already exists"
        }), 400

    user = User(
        name=name,
        email=email,
        password=password,
        role=role_name
    )

    role = Role.query.filter_by(name=role_name).first()

    if role:
        user.roles.append(role)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "User registered successfully"
    }), 201


@app.route('/api/auth/login', methods=['POST'])
def login():

    data = request.get_json()

    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({
            "message": "Invalid email or password"
        }), 401

    if not user.check_password(password):
        return jsonify({
            "message": "Invalid email or password"
        }), 401

    token = create_access_token(identity=str(user.id))

    return jsonify({
        "success": True,
        "token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
    }), 200

@app.route('/api/profile', methods=['GET'])
@jwt_required()
def profile():

        user_id = get_jwt_identity()

        user = User.query.get(user_id)

        return jsonify({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        })

print(app.url_map)

if __name__ == '__main__':
    app.run(debug=True)




