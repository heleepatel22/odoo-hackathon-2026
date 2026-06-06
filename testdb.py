"""
testdb.py  —  VendorBridge full database test
Run with:  python testdb.py
Uses an in-memory SQLite DB so it never touches vendorbridge.sqlite.
Prints PASS / FAIL for every test.  Exits with code 1 if any test fails.
"""

import sys
from datetime import datetime, timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# ── Isolated in-memory app ──────────────────────────────────────────────────
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']        = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Point extensions.db at this test app
import extensions
extensions.db.init_app(app)
db = extensions.db

# Import every model (this also registers all tables)
from models import (
    Role, Permission,
    User, UserRole,
    VendorCategory, Vendor, VendorStatus,
    RFQ, RFQItem, RFQStatus,
    Quotation, QuotationItem, QuotationStatus,
    Approval, ApprovalStatus,
    PurchaseOrder, POStatus,
    Invoice, InvoiceStatus,
    Notification, NotificationType,
    ActivityLog,
)

# ── Test helpers ────────────────────────────────────────────────────────────
passed = 0
failed = 0

def check(label, condition, detail=''):
    global passed, failed
    if condition:
        print(f'  ✅  PASS  {label}')
        passed += 1
    else:
        print(f'  ❌  FAIL  {label}' + (f'  →  {detail}' if detail else ''))
        failed += 1

# ── Run all tests inside one app context ────────────────────────────────────
with app.app_context():
    db.create_all()

    # ════════════════════════════════════════════════════════════════════════
    print('\n── 1. ROLE & PERMISSION ──────────────────────────────────────────')
    # ════════════════════════════════════════════════════════════════════════

    role_admin = Role(name='admin', label='Administrator', description='Full access')
    db.session.add(role_admin)
    db.session.flush()

    perm = Permission(role_id=role_admin.id, resource='rfqs', action='create')
    db.session.add(perm)
    db.session.commit()

    r = Role.query.filter_by(name='admin').first()
    check('Role created and saved',            r is not None)
    check('Role label stored correctly',       r.label == 'Administrator')
    check('Role is_active defaults to True',   r.is_active is True)
    check('Role __repr__',                     repr(r) == 'Role(admin)')
    check('Permission linked to role',         len(r.permissions) == 1)
    check('Permission resource/action stored', r.permissions[0].resource == 'rfqs'
                                               and r.permissions[0].action == 'create')
    check('Permission __repr__',               repr(r.permissions[0]) == 'Permission(rfqs:create)')

    # Duplicate permission should raise (UniqueConstraint)
    dup = Permission(role_id=role_admin.id, resource='rfqs', action='create')
    db.session.add(dup)
    try:
        db.session.commit()
        check('Duplicate permission raises IntegrityError', False, 'No error raised')
    except Exception:
        db.session.rollback()
        check('Duplicate permission raises IntegrityError', True)

    # auto-label from name
    role_mgr = Role(name='procurement_officer')
    db.session.add(role_mgr)
    db.session.commit()
    check('Role label auto-generated from name',
          role_mgr.label == 'Procurement Officer')

    # Cascade delete: deleting role removes its permissions
    role_tmp = Role(name='temp_role')
    db.session.add(role_tmp)
    db.session.flush()
    db.session.add(Permission(role_id=role_tmp.id, resource='x', action='y'))
    db.session.commit()
    db.session.delete(role_tmp)
    db.session.commit()
    orphans = Permission.query.filter_by(resource='x').all()
    check('Cascade delete: Role deletion removes its Permissions', len(orphans) == 0)

    # ════════════════════════════════════════════════════════════════════════
    print('\n── 2. USER ───────────────────────────────────────────────────────')
    # ════════════════════════════════════════════════════════════════════════

    user_admin = User(name='Alice Admin', email='alice@vb.com', password='secret123',
                      role=UserRole.ADMIN)
    user_po    = User(name='Bob PO',      email='bob@vb.com',   password='pass456')
    user_mgr   = User(name='Carol Mgr',   email='carol@vb.com', password='pass789',
                      role=UserRole.MANAGER)
    db.session.add_all([user_admin, user_po, user_mgr])
    db.session.commit()

    u = User.query.filter_by(email='alice@vb.com').first()
    check('User created and saved',                 u is not None)
    check('Password hashed (not stored plaintext)', u.password != 'secret123')
    check('check_password correct password',        u.check_password('secret123'))
    check('check_password wrong password',          not u.check_password('wrong'))
    check('Default role is procurement_officer',
          user_po.role == UserRole.PROCUREMENT_OFFICER)
    check('is_active defaults to True',             u.is_active is True)
    check('User __repr__',                          'Alice Admin' in repr(u))

    # Duplicate email
    dup_user = User(name='Dup', email='alice@vb.com', password='x')
    db.session.add(dup_user)
    try:
        db.session.commit()
        check('Duplicate email raises IntegrityError', False, 'No error raised')
    except Exception:
        db.session.rollback()
        check('Duplicate email raises IntegrityError', True)

    # Many-to-many roles
    user_admin.roles.append(role_admin)
    db.session.commit()
    check('User assigned to Role via many-to-many', role_admin in user_admin.roles)

    # has_permission
    perm2 = Permission(role_id=role_admin.id, resource='vendors', action='delete')
    db.session.add(perm2)
    db.session.commit()
    check('has_permission returns True for granted permission',
          user_admin.has_permission('vendors', 'delete'))
    check('has_permission returns False for ungranted permission',
          not user_admin.has_permission('invoices', 'delete'))

    # ════════════════════════════════════════════════════════════════════════
    print('\n── 3. VENDOR CATEGORY & VENDOR ──────────────────────────────────')
    # ════════════════════════════════════════════════════════════════════════

    cat_it  = VendorCategory(name='IT Services')
    cat_raw = VendorCategory(name='Raw Materials')
    db.session.add_all([cat_it, cat_raw])
    db.session.commit()

    check('VendorCategory created',              cat_it.id is not None)
    check('VendorCategory __repr__',             repr(cat_it) == 'IT Services')

    # Duplicate category name
    dup_cat = VendorCategory(name='IT Services')
    db.session.add(dup_cat)
    try:
        db.session.commit()
        check('Duplicate VendorCategory name raises error', False, 'No error raised')
    except Exception:
        db.session.rollback()
        check('Duplicate VendorCategory name raises error', True)

    vendor_a = Vendor(company_name='TechCorp', email='tc@tc.com',
                      contact_name='Dave', phone='9999999999',
                      gst_number='GST123', category_id=cat_it.id,
                      user_id=user_admin.id)
    vendor_b = Vendor(company_name='RawCo', email='raw@rc.com',
                      category_id=cat_raw.id)
    db.session.add_all([vendor_a, vendor_b])
    db.session.commit()

    v = Vendor.query.filter_by(email='tc@tc.com').first()
    check('Vendor created and saved',              v is not None)
    check('Vendor status defaults to pending',     v.status == VendorStatus.PENDING)
    check('Vendor rating defaults to 0.0',         v.rating == 0.0)
    check('Vendor linked to category via backref', v.category.name == 'IT Services')
    check('Vendor __repr__ contains company name', 'TechCorp' in repr(v))

    # Duplicate vendor email
    dup_v = Vendor(company_name='X', email='tc@tc.com')
    db.session.add(dup_v)
    try:
        db.session.commit()
        check('Duplicate Vendor email raises IntegrityError', False, 'No error raised')
    except Exception:
        db.session.rollback()
        check('Duplicate Vendor email raises IntegrityError', True)

    # ════════════════════════════════════════════════════════════════════════
    print('\n── 4. RFQ & RFQ ITEMS ───────────────────────────────────────────')
    # ════════════════════════════════════════════════════════════════════════

    deadline = datetime.utcnow() + timedelta(days=7)
    rfq1 = RFQ(title='Office Supplies Q1', deadline=deadline,
               created_by_id=user_po.id, description='Quarterly office supplies')
    db.session.add(rfq1)
    db.session.flush()

    item1 = RFQItem(rfq_id=rfq1.id, product_name='A4 Paper',    quantity=100, unit='ream')
    item2 = RFQItem(rfq_id=rfq1.id, product_name='Ballpoint Pen', quantity=200, unit='pcs')
    db.session.add_all([item1, item2])
    db.session.commit()

    rfq = RFQ.query.get(rfq1.id)
    check('RFQ created and saved',               rfq is not None)
    check('RFQ status defaults to draft',        rfq.status == RFQStatus.DRAFT)
    check('RFQ has 2 items',                     len(rfq.items) == 2)
    check('RFQ item product_name correct',       rfq.items[0].product_name == 'A4 Paper')
    check('RFQ backref created_by works',        rfq.created_by.name == 'Bob PO')
    check('RFQ __repr__',                        'Office Supplies Q1' in repr(rfq))
    check('RFQItem __repr__',                    'A4 Paper' in repr(item1))

    # Many-to-many: invite vendors to RFQ
    rfq1.vendors.append(vendor_a)
    rfq1.vendors.append(vendor_b)
    db.session.commit()
    check('RFQ vendors many-to-many: 2 vendors invited', len(rfq1.vendors) == 2)
    check('Vendor backref invited_rfqs works',
          rfq1 in vendor_a.invited_rfqs)

    # Cascade delete: deleting RFQ removes its items
    rfq_tmp = RFQ(title='Temp RFQ', deadline=deadline, created_by_id=user_po.id)
    db.session.add(rfq_tmp)
    db.session.flush()
    db.session.add(RFQItem(rfq_id=rfq_tmp.id, product_name='Tmp Item', quantity=1))
    db.session.commit()
    tmp_item_id = rfq_tmp.items[0].id
    db.session.delete(rfq_tmp)
    db.session.commit()
    check('Cascade delete: RFQ deletion removes its RFQItems',
          RFQItem.query.get(tmp_item_id) is None)

    # ════════════════════════════════════════════════════════════════════════
    print('\n── 5. QUOTATION & QUOTATION ITEMS ───────────────────────────────')
    # ════════════════════════════════════════════════════════════════════════

    quot1 = Quotation(rfq_id=rfq1.id, vendor_id=vendor_a.id,
                      total_price=5000.505,   # unrounded on purpose
                      delivery_timeline=14, notes='Best price guaranteed')
    db.session.add(quot1)
    db.session.flush()

    qi1 = QuotationItem(quotation_id=quot1.id, rfq_item_id=item1.id,
                        unit_price=10.0, quantity=100)
    qi2 = QuotationItem(quotation_id=quot1.id, rfq_item_id=item2.id,
                        unit_price=20.0, quantity=200)
    db.session.add_all([qi1, qi2])
    db.session.commit()

    q = Quotation.query.get(quot1.id)
    check('Quotation created and saved',             q is not None)
    check('Quotation total_price rounded to 2dp',    q.total_price == 5000.51)
    check('Quotation status defaults to submitted',  q.status == QuotationStatus.SUBMITTED)
    check('Quotation has 2 items',                   len(q.items) == 2)
    check('QuotationItem total_price computed',      qi1.total_price == 1000.0)
    check('QuotationItem total_price computed (2)',  qi2.total_price == 4000.0)
    check('Quotation backref vendor works',          q.vendor.company_name == 'TechCorp')
    check('Quotation backref rfq works',             q.rfq.title == 'Office Supplies Q1')
    check('Quotation __repr__ contains IDs',         'Quotation#' in repr(q))

    # Cascade delete: deleting Quotation removes its items
    quot_tmp = Quotation(rfq_id=rfq1.id, vendor_id=vendor_b.id, total_price=100)
    db.session.add(quot_tmp)
    db.session.flush()
    db.session.add(QuotationItem(quotation_id=quot_tmp.id, rfq_item_id=item1.id,
                                 unit_price=1.0, quantity=1))
    db.session.commit()
    tmp_qi_id = quot_tmp.items[0].id
    db.session.delete(quot_tmp)
    db.session.commit()
    check('Cascade delete: Quotation deletion removes its QuotationItems',
          QuotationItem.query.get(tmp_qi_id) is None)

    # ════════════════════════════════════════════════════════════════════════
    print('\n── 6. APPROVAL ──────────────────────────────────────────────────')
    # ════════════════════════════════════════════════════════════════════════

    approval = Approval(quotation_id=quot1.id, approver_id=user_mgr.id)
    db.session.add(approval)
    db.session.commit()

    a = Approval.query.get(approval.id)
    check('Approval created and saved',             a is not None)
    check('Approval status defaults to pending',    a.status == ApprovalStatus.PENDING)
    check('Approval reviewed_at is None initially', a.reviewed_at is None)
    check('Approval backref quotation works',       a.quotation.id == quot1.id)
    check('Approval backref approver works',        a.approver.name == 'Carol Mgr')
    check('Quotation.approval uselist=False works', quot1.approval.id == approval.id)
    check('Approval __repr__',                      'Approval#' in repr(a))

    # Approve it
    a.status      = ApprovalStatus.APPROVED
    a.reviewed_at = datetime.utcnow()
    db.session.commit()
    check('Approval status updated to approved',    a.status == ApprovalStatus.APPROVED)
    check('Approval reviewed_at set',               a.reviewed_at is not None)

    # ════════════════════════════════════════════════════════════════════════
    print('\n── 7. PURCHASE ORDER ────────────────────────────────────────────')
    # ════════════════════════════════════════════════════════════════════════

    po = PurchaseOrder(quotation_id=quot1.id)
    db.session.add(po)
    db.session.commit()

    p = PurchaseOrder.query.get(po.id)
    year = datetime.utcnow().year
    check('PurchaseOrder created and saved',             p is not None)
    check('PO number format correct',                    p.po_number.startswith(f'PO-{year}-'))
    check('PO number zero-padded to 4 digits',           p.po_number == f'PO-{year}-0001')
    check('PO status defaults to generated',             p.status == POStatus.GENERATED)
    check('PO backref quotation works',                  p.quotation.id == quot1.id)
    check('Quotation.purchase_order uselist=False works', quot1.purchase_order.id == po.id)
    check('PO __repr__',                                 f'PO-{year}-0001' in repr(p))

    # Second PO gets incremented number
    quot2 = Quotation(rfq_id=rfq1.id, vendor_id=vendor_b.id, total_price=4500)
    db.session.add(quot2)
    db.session.flush()
    po2 = PurchaseOrder(quotation_id=quot2.id)
    db.session.add(po2)
    db.session.commit()
    check('Second PO number increments correctly', po2.po_number == f'PO-{year}-0002')

    # ════════════════════════════════════════════════════════════════════════
    print('\n── 8. INVOICE ───────────────────────────────────────────────────')
    # ════════════════════════════════════════════════════════════════════════

    inv = Invoice(purchase_order_id=po.id, subtotal=5000.0, tax_rate=18.0,
                  notes='Net 30', due_date=datetime.utcnow() + timedelta(days=30))
    db.session.add(inv)
    db.session.commit()

    i = Invoice.query.get(inv.id)
    check('Invoice created and saved',                i is not None)
    check('Invoice number format correct',            i.invoice_number.startswith(f'INV-{year}-'))
    check('Invoice number zero-padded',               i.invoice_number == f'INV-{year}-0001')
    check('Invoice subtotal stored rounded',          i.subtotal == 5000.0)
    check('Invoice tax_amount computed (18%)',        i.tax_amount == 900.0)
    check('Invoice total_amount = subtotal + tax',    i.total_amount == 5900.0)
    check('Invoice status defaults to draft',         i.status == InvoiceStatus.DRAFT)
    check('Invoice due_date stored',                  i.due_date is not None)
    check('Invoice backref purchase_order works',     i.purchase_order.po_number == p.po_number)
    check('PurchaseOrder.invoice uselist=False works', p.invoice.id == inv.id)
    check('Invoice __repr__',                         f'INV-{year}-0001' in repr(i))

    # Rounding correctness: subtotal with fractional cents
    inv2 = Invoice(purchase_order_id=po2.id, subtotal=999.999, tax_rate=18.0)
    db.session.add(inv2)
    db.session.commit()
    check('Invoice subtotal rounded to 2dp',  inv2.subtotal   == 1000.0)
    check('Invoice tax_amount rounded 2dp',   inv2.tax_amount == round(999.999 * 18 / 100, 2))
    check('Invoice total uses rounded values',
          inv2.total_amount == round(inv2.subtotal + inv2.tax_amount, 2))

    # ════════════════════════════════════════════════════════════════════════
    print('\n── 9. NOTIFICATION ──────────────────────────────────────────────')
    # ════════════════════════════════════════════════════════════════════════

    notif = Notification(
        user_id    = user_po.id,
        title      = 'New Quotation Received',
        message    = 'TechCorp submitted a quotation for Office Supplies Q1.',
        notif_type = NotificationType.QUOTATION_SUBMITTED,
        entity_type= 'quotation',
        entity_id  = quot1.id,
    )
    db.session.add(notif)
    db.session.commit()

    n = Notification.query.get(notif.id)
    check('Notification created and saved',           n is not None)
    check('Notification notif_type stored correctly', n.notif_type == NotificationType.QUOTATION_SUBMITTED)
    check('Notification is_read defaults to False',   n.is_read is False)
    check('Notification read_at is None initially',   n.read_at is None)
    check('Notification entity_type stored',          n.entity_type == 'quotation')
    check('Notification entity_id stored',            n.entity_id == quot1.id)
    check('Notification backref recipient works',     n.recipient.name == 'Bob PO')
    check('User.notifications backref works',         notif in user_po.notifications)
    check('Notification __repr__ contains unread',    'unread' in repr(n))

    # mark_as_read
    n.mark_as_read()
    db.session.commit()
    check('mark_as_read sets is_read=True',  n.is_read is True)
    check('mark_as_read sets read_at',       n.read_at is not None)
    check('Notification __repr__ after read contains read', 'read' in repr(n))

    # Default notif_type
    notif2 = Notification(user_id=user_mgr.id, title='Hello', message='Test')
    db.session.add(notif2)
    db.session.commit()
    check('Notification notif_type defaults to general',
          notif2.notif_type == NotificationType.GENERAL)

    # ════════════════════════════════════════════════════════════════════════
    print('\n── 10. ACTIVITY LOG ─────────────────────────────────────────────')
    # ════════════════════════════════════════════════════════════════════════

    log1 = ActivityLog(action='RFQ #1 published',
                       user_id=user_po.id, entity_type='rfq', entity_id=rfq1.id)
    log2 = ActivityLog(action='System startup')   # no user (system event)
    db.session.add_all([log1, log2])
    db.session.commit()

    l1 = ActivityLog.query.get(log1.id)
    l2 = ActivityLog.query.get(log2.id)
    check('ActivityLog created with user',       l1 is not None and l1.user_id == user_po.id)
    check('ActivityLog entity_type stored',      l1.entity_type == 'rfq')
    check('ActivityLog entity_id stored',        l1.entity_id == rfq1.id)
    check('ActivityLog timestamp set',           l1.timestamp is not None)
    check('ActivityLog without user (nullable)', l2.user_id is None)
    check('ActivityLog backref user works',      l1.user.name == 'Bob PO')
    check('ActivityLog __repr__',                'RFQ #1 published' in repr(l1))

    # ════════════════════════════════════════════════════════════════════════
    print('\n── 11. CROSS-MODEL INTEGRITY ────────────────────────────────────')
    # ════════════════════════════════════════════════════════════════════════

    # Full chain: RFQ → Quotation → Approval → PO → Invoice
    check('Full chain: RFQ → Quotation linked',       quot1.rfq_id == rfq1.id)
    check('Full chain: Quotation → Approval linked',  approval.quotation_id == quot1.id)
    check('Full chain: Quotation → PO linked',        po.quotation_id == quot1.id)
    check('Full chain: PO → Invoice linked',          inv.purchase_order_id == po.id)

    # User.rfqs_created backref
    check('User.rfqs_created backref works',
          rfq1 in user_po.rfqs_created)

    # User.approvals_made backref
    check('User.approvals_made backref works',
          approval in user_mgr.approvals_made)

    # User.activity_logs backref
    check('User.activity_logs backref works',
          log1 in user_po.activity_logs)

    # Vendor.quotations backref
    check('Vendor.quotations backref works',
          quot1 in vendor_a.quotations)

    # ════════════════════════════════════════════════════════════════════════
    # SUMMARY
    # ════════════════════════════════════════════════════════════════════════
    total = passed + failed
    print(f'\n{"═"*60}')
    print(f'  Results:  {passed}/{total} passed', end='')
    if failed:
        print(f'   |   {failed} FAILED  ❌')
    else:
        print('   |   All tests passed  🎉')
    print(f'{"═"*60}\n')

sys.exit(0 if failed == 0 else 1)