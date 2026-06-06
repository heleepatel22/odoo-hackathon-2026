from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from extensions import db
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)
    JWTManager(app)
    db.init_app(app)
    
    from extensions import mail
    mail.init_app(app)

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

    # ── Register Blueprints (uncomment as you build routes) ──
    from routes.auth           import auth_bp
    from routes.vendor         import vendor_bp
    from routes.rfq            import rfq_bp
    from routes.quotation      import quotation_bp
    from routes.approval       import approval_bp
    from routes.purchase_order import po_bp
    from routes.invoice        import invoice_bp
    from routes.dashboard      import dashboard_bp
    from routes.settings       import settings_bp
    from routes.activity       import activity_bp
    from routes.reports        import reports_bp
    # from routes.notifications  import notifications_bp

    app.register_blueprint(auth_bp,           url_prefix='/api/auth')
    app.register_blueprint(vendor_bp,         url_prefix='/api/vendors')
    app.register_blueprint(rfq_bp,            url_prefix='/api/rfqs')
    app.register_blueprint(quotation_bp,      url_prefix='/api/quotations')
    app.register_blueprint(approval_bp,       url_prefix='/api/approvals')
    app.register_blueprint(po_bp,             url_prefix='/api/purchase-orders')
    app.register_blueprint(invoice_bp,        url_prefix='/api/invoices')
    app.register_blueprint(dashboard_bp,      url_prefix='/api/dashboard')
    app.register_blueprint(settings_bp,       url_prefix='/api/settings')
    app.register_blueprint(activity_bp,       url_prefix='/api/activity')
    app.register_blueprint(reports_bp,        url_prefix='/api/reports')
    # app.register_blueprint(notifications_bp,  url_prefix='/api/notifications')

    with app.app_context():
        db.create_all()
        _seed_default_roles()
        print('All tables created.')

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
        print('Default roles seeded.')

    except Exception as e:
        db.session.rollback()
        print(f'Role seeding failed (already seeded or error): {e}')


# BUG 6 FIX: create_app() was called at module level unconditionally.
# This means every `from app import something` (e.g. in tests or CLI tools)
# triggers a full app + DB creation.  Guarding with __name__ check is correct
# for scripts, but for a proper Flask app the app factory pattern means you
# should NOT call create_app() at module level — use `flask run` or a WSGI
# entry point instead.  Kept here only for `python app.py` convenience.
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)











# from flask import Flask
# from extensions import db
# from config import Config


# def create_app():
#     app = Flask(__name__)
#     app.config.from_object(Config)

#     db.init_app(app)

#     # FIX: import all models here so db.create_all() knows about every table
#     from models import (User, VendorCategory, Vendor, RFQ, RFQItem,
#                         Quotation, QuotationItem, Approval,
#                         PurchaseOrder, Invoice, ActivityLog)

#     # ── Register Blueprints (uncomment as you build routes) ──
#     # from routes.auth           import auth_bp
#     # from routes.vendor         import vendor_bp
#     # from routes.rfq            import rfq_bp
#     # from routes.quotation      import quotation_bp
#     # from routes.approval       import approval_bp
#     # from routes.purchase_order import po_bp
#     # from routes.invoice        import invoice_bp
#     # from routes.dashboard      import dashboard_bp

#     # app.register_blueprint(auth_bp,        url_prefix='/api/auth')
#     # app.register_blueprint(vendor_bp,      url_prefix='/api/vendors')
#     # app.register_blueprint(rfq_bp,         url_prefix='/api/rfqs')
#     # app.register_blueprint(quotation_bp,   url_prefix='/api/quotations')
#     # app.register_blueprint(approval_bp,    url_prefix='/api/approvals')
#     # app.register_blueprint(po_bp,          url_prefix='/api/purchase-orders')
#     # app.register_blueprint(invoice_bp,     url_prefix='/api/invoices')
#     # app.register_blueprint(dashboard_bp,   url_prefix='/api/dashboard')

#     with app.app_context():
#         db.create_all()
#         print('✅ All tables created.')

#     return app


# app = create_app()

# if __name__ == '__main__':
#     app.run(debug=True)


