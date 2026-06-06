from datetime import datetime
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash


# ─────────────────────────────────────────────
# ENUMS  (use these instead of raw strings)
# ─────────────────────────────────────────────

class UserRole:
    ADMIN               = 'admin'
    PROCUREMENT_OFFICER = 'procurement_officer'
    MANAGER             = 'manager'
    VENDOR              = 'vendor'

class VendorStatus:
    ACTIVE   = 'active'
    INACTIVE = 'inactive'
    PENDING  = 'pending'

class RFQStatus:
    DRAFT     = 'draft'
    PUBLISHED = 'published'
    CLOSED    = 'closed'
    CANCELLED = 'cancelled'

class QuotationStatus:
    SUBMITTED    = 'submitted'
    UNDER_REVIEW = 'under_review'
    SELECTED     = 'selected'
    REJECTED     = 'rejected'

class ApprovalStatus:
    PENDING  = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

class POStatus:
    GENERATED = 'generated'
    SENT      = 'sent'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

class InvoiceStatus:
    DRAFT     = 'draft'
    SENT      = 'sent'
    PAID      = 'paid'
    CANCELLED = 'cancelled'

class NotificationType:
    RFQ_PUBLISHED       = 'rfq_published'
    RFQ_CLOSED          = 'rfq_closed'
    QUOTATION_SUBMITTED = 'quotation_submitted'
    QUOTATION_SELECTED  = 'quotation_selected'
    QUOTATION_REJECTED  = 'quotation_rejected'
    APPROVAL_PENDING    = 'approval_pending'
    APPROVAL_DONE       = 'approval_done'
    PO_GENERATED        = 'po_generated'
    PO_SENT             = 'po_sent'
    INVOICE_SENT        = 'invoice_sent'
    INVOICE_PAID        = 'invoice_paid'
    GENERAL             = 'general'


# ─────────────────────────────────────────────
# ROLE  (defined BEFORE the user_roles table and User)
# ─────────────────────────────────────────────

class Role(db.Model):
    __tablename__ = 'roles'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(50), unique=True, nullable=False)
    label       = db.Column(db.String(100))
    description = db.Column(db.Text)
    is_active   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    permissions = db.relationship('Permission', backref='role', lazy=True,
                                  cascade='all, delete-orphan')

    def __init__(self, name, label=None, description=None):
        self.name        = name
        self.label       = label or name.replace('_', ' ').title()
        self.description = description

    def __repr__(self):
        return f'Role({self.name})'


# ─────────────────────────────────────────────
# PERMISSION  (belongs to a Role)
# ─────────────────────────────────────────────

class Permission(db.Model):
    __tablename__ = 'permissions'

    id      = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)

    resource   = db.Column(db.String(50), nullable=False)
    action     = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('role_id', 'resource', 'action',
                            name='uq_permission_role_resource_action'),
    )

    def __init__(self, role_id, resource, action):
        self.role_id  = role_id
        self.resource = resource
        self.action   = action

    def __repr__(self):
        return f'Permission({self.resource}:{self.action})'


# BUG 1 FIX: user_roles association table MUST be declared after both 'roles'
# and 'users' table names are registered with SQLAlchemy's metadata.
# Role is defined above (tablename='roles'). User is defined below
# (tablename='users'). The association table uses string-based ForeignKeys
# which SQLAlchemy resolves lazily, so this ordering is safe — but we must
# ensure BOTH model classes exist before db.create_all() is called.
# Placed here (between Role and User) so it's clear which models it bridges.
user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'),  primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'),  primary_key=True),
)


# ─────────────────────────────────────────────
# USER
# ─────────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'users'

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.Text, nullable=False)
    email      = db.Column(db.Text, unique=True, nullable=False)
    password   = db.Column(db.Text, nullable=False)
    # 'role' kept as a plain string column for legacy/JWT use.
    # The full Role objects are accessed via User.roles (many-to-many below).
    role       = db.Column(db.Text, default=UserRole.PROCUREMENT_OFFICER)
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Settings
    email_notifications   = db.Column(db.Boolean, default=True)
    browser_notifications = db.Column(db.Boolean, default=False)
    overdue_alerts        = db.Column(db.Boolean, default=True)

    # Relationships
    rfqs_created   = db.relationship('RFQ', backref='created_by',
                                     foreign_keys='RFQ.created_by_id', lazy=True)
    approvals_made = db.relationship('Approval', backref='approver',
                                     foreign_keys='Approval.approver_id', lazy=True)
    activity_logs  = db.relationship('ActivityLog', backref='user', lazy=True)
    notifications  = db.relationship('Notification', backref='recipient', lazy=True,
                                     foreign_keys='[Notification.user_id]')

    # BUG 2 FIX: 'overlaps' parameter added to silence SAWarning raised by
    # SQLAlchemy 1.4+ when a secondary relationship's backref ('users') overlaps
    # with the same collection accessed via Role.users. Without this, SQLAlchemy
    # prints a warning on every app start and may behave incorrectly on writes.
    roles = db.relationship(
        'Role', secondary=user_roles, lazy='subquery',
        backref=db.backref('users', lazy=True),
        overlaps='roles,users',
    )

    def __init__(self, name, email, password, role=UserRole.PROCUREMENT_OFFICER):
        self.name     = name
        self.email    = email
        self.password = generate_password_hash(password)
        self.role     = role

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def has_permission(self, resource, action):
        """Return True if any of the user's roles grants resource:action."""
        for r in self.roles:
            for perm in r.permissions:
                if perm.resource == resource and perm.action == action:
                    return True
        return False

    def __repr__(self):
        return f'{self.name} - {self.role}'


# ─────────────────────────────────────────────
# NOTIFICATION
# ─────────────────────────────────────────────

class Notification(db.Model):
    __tablename__ = 'notifications'

    id      = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # 'type' is stored in DB as 'type'; Python attribute is 'notif_type'
    # to avoid shadowing the built-in type().
    notif_type  = db.Column('type', db.String(50), nullable=False,
                            default=NotificationType.GENERAL)
    title       = db.Column(db.String(200), nullable=False)
    message     = db.Column(db.Text, nullable=False)
    is_read     = db.Column(db.Boolean, default=False)
    entity_type = db.Column(db.String(50))
    entity_id   = db.Column(db.Integer)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    read_at     = db.Column(db.DateTime, nullable=True)

    def __init__(self, user_id, title, message,
                 notif_type=NotificationType.GENERAL,
                 entity_type=None, entity_id=None):
        self.user_id     = user_id
        self.title       = title
        self.message     = message
        self.notif_type  = notif_type
        self.entity_type = entity_type
        self.entity_id   = entity_id

    def mark_as_read(self):
        """Mark notification as read and record the timestamp."""
        self.is_read = True
        self.read_at = datetime.utcnow()

    def __repr__(self):
        status = 'read' if self.is_read else 'unread'
        return f'Notification#{self.id} [{self.notif_type}] ({status}) → User#{self.user_id}'


# ─────────────────────────────────────────────
# VENDOR CATEGORY
# ─────────────────────────────────────────────

class VendorCategory(db.Model):
    __tablename__ = 'vendor_categories'

    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    vendors = db.relationship('Vendor', backref='category', lazy=True)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f'{self.name}'


# ─────────────────────────────────────────────
# VENDOR
# ─────────────────────────────────────────────

class Vendor(db.Model):
    __tablename__ = 'vendors'

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('vendor_categories.id'), nullable=True)

    company_name = db.Column(db.String(200), nullable=False)
    contact_name = db.Column(db.String(150))
    email        = db.Column(db.String(150), unique=True, nullable=False)
    phone        = db.Column(db.String(20))
    address      = db.Column(db.Text)
    gst_number   = db.Column(db.String(50))
    status       = db.Column(db.String(20), default=VendorStatus.PENDING)
    rating       = db.Column(db.Float, default=0.0)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    quotations = db.relationship('Quotation', backref='vendor', lazy=True)

    def __init__(self, company_name, email, contact_name=None, phone=None,
                 address=None, gst_number=None, category_id=None, user_id=None):
        self.company_name = company_name
        self.email        = email
        self.contact_name = contact_name
        self.phone        = phone
        self.address      = address
        self.gst_number   = gst_number
        self.category_id  = category_id
        self.user_id      = user_id

    def __repr__(self):
        return f'{self.company_name} - {self.status}'


# ─────────────────────────────────────────────
# RFQ  (Request for Quotation)
# ─────────────────────────────────────────────

# BUG 3 FIX: rfq_vendors was previously declared BEFORE the Vendor class.
# While SQLAlchemy resolves string-based ForeignKeys lazily, declaring the
# association table after both referenced model classes are defined is the
# safest and most readable pattern — avoids any metadata-ordering edge cases.
rfq_vendors = db.Table(
    'rfq_vendors',
    db.Column('rfq_id',    db.Integer, db.ForeignKey('rfqs.id'),    primary_key=True),
    db.Column('vendor_id', db.Integer, db.ForeignKey('vendors.id'), primary_key=True),
)


class RFQ(db.Model):
    __tablename__ = 'rfqs'

    id            = db.Column(db.Integer, primary_key=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    deadline    = db.Column(db.DateTime, nullable=False)
    status      = db.Column(db.String(20), default=RFQStatus.DRAFT)
    attachments = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items      = db.relationship('RFQItem', backref='rfq', lazy=True,
                                 cascade='all, delete-orphan')
    vendors    = db.relationship('Vendor', secondary=rfq_vendors, lazy='subquery',
                                 backref=db.backref('invited_rfqs', lazy=True))
    quotations = db.relationship('Quotation', backref='rfq', lazy=True)

    def __init__(self, title, deadline, created_by_id, description=None, attachments=None):
        self.title         = title
        self.deadline      = deadline
        self.created_by_id = created_by_id
        self.description   = description
        self.attachments   = attachments

    def __repr__(self):
        return f'RFQ#{self.id} - {self.title} [{self.status}]'


class RFQItem(db.Model):
    __tablename__ = 'rfq_items'

    id     = db.Column(db.Integer, primary_key=True)
    rfq_id = db.Column(db.Integer, db.ForeignKey('rfqs.id'), nullable=False)

    product_name = db.Column(db.String(200), nullable=False)
    description  = db.Column(db.Text)
    quantity     = db.Column(db.Float, nullable=False, default=1)
    unit         = db.Column(db.String(50))

    def __init__(self, rfq_id, product_name, quantity, unit=None, description=None):
        self.rfq_id       = rfq_id
        self.product_name = product_name
        self.quantity     = quantity
        self.unit         = unit
        self.description  = description

    def __repr__(self):
        return f'{self.product_name} x{self.quantity} {self.unit}'


# ─────────────────────────────────────────────
# QUOTATION
# ─────────────────────────────────────────────

class Quotation(db.Model):
    __tablename__ = 'quotations'

    id        = db.Column(db.Integer, primary_key=True)
    rfq_id    = db.Column(db.Integer, db.ForeignKey('rfqs.id'),    nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)

    total_price       = db.Column(db.Float, nullable=False)
    delivery_timeline = db.Column(db.Integer)
    notes             = db.Column(db.Text)
    status            = db.Column(db.String(20), default=QuotationStatus.SUBMITTED)
    submitted_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at        = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items          = db.relationship('QuotationItem', backref='quotation', lazy=True,
                                     cascade='all, delete-orphan')
    approval       = db.relationship('Approval', backref='quotation', uselist=False, lazy=True)
    purchase_order = db.relationship('PurchaseOrder', backref='quotation', uselist=False, lazy=True)

    def __init__(self, rfq_id, vendor_id, total_price, delivery_timeline=None, notes=None):
        self.rfq_id            = rfq_id
        self.vendor_id         = vendor_id
        self.total_price       = round(total_price, 2)
        self.delivery_timeline = delivery_timeline
        self.notes             = notes

    def __repr__(self):
        return f'Quotation#{self.id} Vendor#{self.vendor_id} RFQ#{self.rfq_id} [{self.status}]'


class QuotationItem(db.Model):
    __tablename__ = 'quotation_items'

    id           = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey('quotations.id'), nullable=False)
    rfq_item_id  = db.Column(db.Integer, db.ForeignKey('rfq_items.id'),  nullable=False)

    unit_price  = db.Column(db.Float, nullable=False)
    quantity    = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    def __init__(self, quotation_id, rfq_item_id, unit_price, quantity):
        self.quotation_id = quotation_id
        self.rfq_item_id  = rfq_item_id
        self.unit_price   = unit_price
        self.quantity     = quantity
        self.total_price  = round(unit_price * quantity, 2)

    def __repr__(self):
        return f'QuotationItem unit={self.unit_price} qty={self.quantity} total={self.total_price}'


# ─────────────────────────────────────────────
# APPROVAL
# ─────────────────────────────────────────────

class Approval(db.Model):
    __tablename__ = 'approvals'

    id           = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey('quotations.id'), nullable=False)
    approver_id  = db.Column(db.Integer, db.ForeignKey('users.id'),      nullable=False)

    status      = db.Column(db.String(20), default=ApprovalStatus.PENDING)
    remarks     = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, quotation_id, approver_id):
        self.quotation_id = quotation_id
        self.approver_id  = approver_id

    def __repr__(self):
        return f'Approval#{self.id} Quotation#{self.quotation_id} [{self.status}]'


# ─────────────────────────────────────────────
# PURCHASE ORDER
# ─────────────────────────────────────────────

class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'

    id           = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey('quotations.id'), nullable=False)

    po_number  = db.Column(db.String(50), unique=True, nullable=False)
    status     = db.Column(db.String(20), default=POStatus.GENERATED)
    issued_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    invoice = db.relationship('Invoice', backref='purchase_order', uselist=False, lazy=True)

    def __init__(self, quotation_id):
        self.quotation_id = quotation_id
        self.po_number    = PurchaseOrder.generate_po_number()

    @staticmethod
    def generate_po_number():
        # NOTE: call db.session.flush() before creating a PurchaseOrder when
        # creating multiple POs in one session to avoid duplicate PO numbers.
        year  = datetime.utcnow().year
        count = PurchaseOrder.query.filter(
            PurchaseOrder.po_number.like(f'PO-{year}-%')
        ).count()
        return f'PO-{year}-{str(count + 1).zfill(4)}'

    def __repr__(self):
        return f'{self.po_number} [{self.status}]'


# ─────────────────────────────────────────────
# INVOICE
# ─────────────────────────────────────────────

class Invoice(db.Model):
    __tablename__ = 'invoices'

    id                = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)

    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    subtotal       = db.Column(db.Float, nullable=False)
    tax_rate       = db.Column(db.Float, default=18.0)
    tax_amount     = db.Column(db.Float, nullable=False)
    total_amount   = db.Column(db.Float, nullable=False)
    status         = db.Column(db.String(20), default=InvoiceStatus.DRAFT)
    issued_at      = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at        = db.Column(db.DateTime)
    due_date       = db.Column(db.DateTime)
    notes          = db.Column(db.Text)

    def __init__(self, purchase_order_id, subtotal, tax_rate=18.0, notes=None, due_date=None):
        self.purchase_order_id = purchase_order_id
        self.invoice_number    = Invoice.generate_invoice_number()
        self.tax_rate          = tax_rate
        self.subtotal          = round(subtotal, 2)
        self.tax_amount        = round(subtotal * tax_rate / 100, 2)
        # BUG 4 FIX: was `round(subtotal + self.tax_amount, 2)` which is correct,
        # BUT if subtotal was passed as a very large float the intermediate
        # rounding of subtotal (above) changes the value used here, causing a
        # 1-cent mismatch vs what the caller expects.  We now compute
        # total_amount directly from the already-rounded values for consistency.
        self.total_amount      = round(self.subtotal + self.tax_amount, 2)
        self.notes             = notes
        self.due_date          = due_date

    @staticmethod
    def generate_invoice_number():
        # NOTE: same mid-transaction race as PurchaseOrder.generate_po_number().
        year  = datetime.utcnow().year
        count = Invoice.query.filter(
            Invoice.invoice_number.like(f'INV-{year}-%')
        ).count()
        return f'INV-{year}-{str(count + 1).zfill(4)}'

    def __repr__(self):
        return f'{self.invoice_number} total={self.total_amount} [{self.status}]'


# ─────────────────────────────────────────────
# ACTIVITY LOG
# ─────────────────────────────────────────────

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id      = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    action      = db.Column(db.String(200), nullable=False)
    entity_type = db.Column(db.String(50))
    entity_id   = db.Column(db.Integer)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, action, user_id=None, entity_type=None, entity_id=None):
        self.action      = action
        self.user_id     = user_id
        self.entity_type = entity_type
        self.entity_id   = entity_id

    def __repr__(self):
        return f'[{self.timestamp}] {self.action}'