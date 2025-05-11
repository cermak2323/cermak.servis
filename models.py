from database import db
from datetime import datetime, timezone
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='musteri')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

    # Permission ile ilişki tanımlama (one-to-one)
    permissions = db.relationship('Permission', back_populates='user', uselist=False)

class Announcement(db.Model):
    __tablename__ = 'announcement'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class Permission(db.Model):
    __tablename__ = 'permission'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    can_view_parts = db.Column(db.Boolean, default=False)
    can_edit_parts = db.Column(db.Boolean, default=False)
    can_view_faults = db.Column(db.Boolean, default=False)
    can_add_solutions = db.Column(db.Boolean, default=False)
    can_view_catalogs = db.Column(db.Boolean, default=False)
    can_view_maintenance = db.Column(db.Boolean, default=False)
    can_edit_maintenance = db.Column(db.Boolean, default=False)
    can_view_contact = db.Column(db.Boolean, default=False)
    can_view_purchase_prices = db.Column(db.Boolean, default=False)
    can_view_warranty = db.Column(db.Boolean, default=False)
    can_view_accounting = db.Column(db.Boolean, default=False)
    can_view_periodic_maintenance = db.Column(db.Boolean, default=False)
    can_view_admin_panel = db.Column(db.Boolean, default=False)
    can_create_offers = db.Column(db.Boolean, default=False)
    can_view_offers = db.Column(db.Boolean, default=False)
    can_upload_excel = db.Column(db.Boolean, default=False)
    can_view_admin_panel = db.Column(db.Boolean, default=False)
    can_create_offers = db.Column(db.Boolean, default=False)

    # User ile ilişki tanımlama
    user = db.relationship('User', back_populates='permissions')

class Part(db.Model):
    __tablename__ = 'part'
    id = db.Column(db.Integer, primary_key=True)
    part_code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    alternate_part_code = db.Column(db.String(50))
    price_eur = db.Column(db.Float)

class Catalog(db.Model):
    __tablename__ = 'catalog'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)

class CatalogItem(db.Model):
    __tablename__ = 'catalog_item'
    id = db.Column(db.Integer, primary_key=True)
    catalog_id = db.Column(db.Integer, db.ForeignKey('catalog.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    motor_pdf_url = db.Column(db.String(200))
    yedek_parca_pdf_url = db.Column(db.String(200))
    operator_pdf_url = db.Column(db.String(200))
    service_pdf_url = db.Column(db.String(200))

class Fault(db.Model):
    __tablename__ = 'fault'
    id = db.Column(db.Integer, primary_key=True)
    catalog_item_id = db.Column(db.Integer, db.ForeignKey('catalog_item.id'), nullable=False)
    fault_code = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    solution = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

class FaultSolution(db.Model):
    __tablename__ = 'fault_solution'
    id = db.Column(db.Integer, primary_key=True)
    fault_report_id = db.Column(db.Integer, db.ForeignKey('fault_report.id'), nullable=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    part_codes = db.Column(db.String(200), nullable=True)
    media_file = db.Column(db.String(200), nullable=True)
    machine_model = db.Column(db.String(100), nullable=False)
    fault_type = db.Column(db.String(50), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

class FaultReport(db.Model):
    __tablename__ = 'fault_report'
    id = db.Column(db.Integer, primary_key=True)
    fault_id = db.Column(db.Integer, db.ForeignKey('fault.id'), nullable=False)
    report_description = db.Column(db.Text, nullable=False)
    reported_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reported_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

class Machine(db.Model):
    __tablename__ = 'machine'
    id = db.Column(db.Integer, primary_key=True)
    serial_number = db.Column(db.String(50), unique=True, nullable=False)
    model = db.Column(db.String(100), nullable=False)
    owner_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    responsible_service = db.Column(db.String(100), nullable=False)

class MaintenanceRecord(db.Model):
    __tablename__ = 'maintenance_record'
    id = db.Column(db.Integer, primary_key=True)
    catalog_item_id = db.Column(db.Integer, db.ForeignKey('catalog_item.id'), nullable=False)
    maintenance_date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text, nullable=False)
    invoice_file = db.Column(db.String(200))
    image_file = db.Column(db.String(200))

class MachineMaintenanceRecord(db.Model):
    __tablename__ = 'machine_maintenance_record'
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    action_date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text, nullable=False)
    invoice_file = db.Column(db.String(200))
    part_image = db.Column(db.String(200))

class QRCode(db.Model):
    __tablename__ = 'qr_code'
    id = db.Column(db.Integer, primary_key=True)
    qr_code_url = db.Column(db.String(200), unique=True, nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'))
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

class Warranty(db.Model):
    __tablename__ = 'warranty'
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)
    serial_number = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text, nullable=False)
    document_url = db.Column(db.String(200))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

class PeriodicMaintenance(db.Model):
    __tablename__ = 'periodic_maintenance'
    id = db.Column(db.Integer, primary_key=True)
    machine_model = db.Column(db.String(100), nullable=False)
    filter_name = db.Column(db.String(100), nullable=False)
    filter_part_code = db.Column(db.String(50), nullable=False)
    alternate_part_code = db.Column(db.String(50))
    original_price_eur = db.Column(db.Float, nullable=False)
    alternate_price_eur = db.Column(db.Float)
    maintenance_interval = db.Column(db.String(50), nullable=False)
    created_by = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

class Offer(db.Model):
    __tablename__ = 'offer'
    id = db.Column(db.Integer, primary_key=True)
    offer_number = db.Column(db.String(50), unique=True, nullable=False)
    machine_model = db.Column(db.String(100), nullable=False)
    maintenance_interval = db.Column(db.String(50), nullable=False)
    serial_number = db.Column(db.String(50), nullable=False)
    filter_type = db.Column(db.String(50), nullable=False)
    customer_first_name = db.Column(db.String(100), nullable=False)
    customer_last_name = db.Column(db.String(100), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    offeror_name = db.Column(db.String(100), nullable=False)
    labor_cost = db.Column(db.Float, nullable=False)  # EUR cinsinden
    travel_cost = db.Column(db.Float, nullable=False)  # EUR cinsinden
    total_amount = db.Column(db.Float, nullable=False)  # TL cinsinden
    discount_type = db.Column(db.String(50), nullable=False)
    discount_value = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Teklif Hazırlandı')
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_at = db.Column(db.DateTime)
    invoice_number = db.Column(db.String(50))
    pdf_file_path = db.Column(db.String(200))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Yeni eklenen alan
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)

class Invoice(db.Model):
    __tablename__ = 'invoice'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('machine_maintenance_record.id'), nullable=False)
    amount_eur = db.Column(db.Float, nullable=False)
    issue_date = db.Column(db.DateTime, nullable=False)
    document_url = db.Column(db.String(200))
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='Onay Bekliyor')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    approvers = db.relationship('InvoiceApproval', backref='invoice', lazy=True)



class InvoiceApproval(db.Model):
    __tablename__ = 'invoice_approval'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    approved = db.Column(db.Boolean, default=False)
    approved_at = db.Column(db.DateTime)
    comment = db.Column(db.Text)