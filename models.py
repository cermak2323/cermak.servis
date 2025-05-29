# Adding invoice_file field to the Equipment model.
from database import db
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Equipment Type Constants
EQUIPMENT_TYPES = {
    'BUCKET': 'Kova',
    'ATTACHMENT': 'Ataşman',
    'QUICKHITCH': 'Quickhitch',
    'MAINTENANCE_KIT': 'Bakım Kiti'
}

# Equipment Status Types
EQUIPMENT_STATUS = {
    'PENDING': 'Beklemede',
    'IN_PREPARATION': 'Hazırlanıyor',
    'READY_FOR_DELIVERY': 'Teslime Hazır',
    'DELIVERED': 'Teslim Edildi',
    'RETURNED': 'İade Edildi',
    'UNDER_MAINTENANCE': 'Bakımda',
    'DAMAGED': 'Hasarlı'
}

# Bucket Types
BUCKET_TYPES = [
    'Yükleme Kovası',
    'Tesviye Kovası',
    'Tırmık Kova',
    'Taş-Tırmık Kova',
    'Kanal Kovası'
]

# Bucket Widths (in cm)
BUCKET_WIDTHS = [
    20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160
]

# Attachment Types
ATTACHMENT_TYPES = [
    'Kıskaç Ataşmanı',
    'Tomruk Ataşmanı (Rotatorlu)',
    'Tomruk Ataşmanı (Rotatorsuz)'
]

# Maintenance Kit Types
MAINTENANCE_KIT_TYPES = [
    '50 Saat Bakım Kiti',
    '250 Saat Bakım Kiti',
    '500 Saat Bakım Kiti',
    '750 Saat Bakım Kiti',
    '1000 Saat Bakım Kiti'
]

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user')  # 'admin' veya 'user'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    permissions = db.relationship('Permission', back_populates='user', uselist=False)

    def __init__(self, username, password, role='user', email=None, created_at=None):
        self.username = username
        self.set_password(password)  # password hash'i güvenli şekilde oluştur
        self.role = role
        self.email = email or f"{username}@example.com"  # Default email if not provided
        if created_at:
            self.created_at = created_at

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, value):
        self.set_password(value)

class Permission(db.Model):
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Makine Yönetimi
    can_view_machines = db.Column(db.Boolean, default=False)
    can_add_machines = db.Column(db.Boolean, default=False)
    can_edit_machines = db.Column(db.Boolean, default=False)
    can_delete_machines = db.Column(db.Boolean, default=False)
    can_search_machines = db.Column(db.Boolean, default=False)
    can_export_machines = db.Column(db.Boolean, default=False)
    can_list_machines = db.Column(db.Boolean, default=False)

    # Arıza Çözüm Sistemi
    can_view_faults = db.Column(db.Boolean, default=False)
    can_add_faults = db.Column(db.Boolean, default=False)
    can_edit_faults = db.Column(db.Boolean, default=False)
    can_delete_faults = db.Column(db.Boolean, default=False)
    can_assign_faults = db.Column(db.Boolean, default=False)
    can_resolve_faults = db.Column(db.Boolean, default=False)
    can_add_fault_solutions = db.Column(db.Boolean, default=False)
    can_view_fault_history = db.Column(db.Boolean, default=False)
    can_manage_fault_categories = db.Column(db.Boolean, default=False)
    can_export_fault_reports = db.Column(db.Boolean, default=False)
    
    # Bakım Yönetimi
    can_view_maintenance = db.Column(db.Boolean, default=False)
    can_add_maintenance = db.Column(db.Boolean, default=False)
    can_edit_maintenance = db.Column(db.Boolean, default=False)
    can_delete_maintenance = db.Column(db.Boolean, default=False)
    can_view_maintenance_history = db.Column(db.Boolean, default=False)
    can_view_maintenance_reminders = db.Column(db.Boolean, default=False)
    can_manage_maintenance_schedules = db.Column(db.Boolean, default=False)
    
    # Ekipman Yönetimi
    can_view_equipment = db.Column(db.Boolean, default=False)
    can_add_equipment = db.Column(db.Boolean, default=False)
    can_edit_equipment = db.Column(db.Boolean, default=False)
    can_delete_equipment = db.Column(db.Boolean, default=False)
    can_manage_equipment_status = db.Column(db.Boolean, default=False)
    
    # Parça ve Katalog Yönetimi
    can_view_parts = db.Column(db.Boolean, default=False)
    can_edit_parts = db.Column(db.Boolean, default=False)
    can_view_catalogs = db.Column(db.Boolean, default=False)
    can_manage_catalogs = db.Column(db.Boolean, default=False)
    can_view_purchase_prices = db.Column(db.Boolean, default=False)
    
    # Teklif Yönetimi
    can_view_offers = db.Column(db.Boolean, default=False)
    can_create_offers = db.Column(db.Boolean, default=False)
    can_edit_offers = db.Column(db.Boolean, default=False)
    can_delete_offers = db.Column(db.Boolean, default=False)
    can_approve_offers = db.Column(db.Boolean, default=False)
    can_reject_offers = db.Column(db.Boolean, default=False)
    can_view_periodic_maintenance = db.Column(db.Boolean, default=False)
    can_manage_periodic_maintenance = db.Column(db.Boolean, default=False)
    
    # Garanti ve Muhasebe
    can_view_warranty = db.Column(db.Boolean, default=False)
    can_manage_warranty = db.Column(db.Boolean, default=False)
    can_view_accounting = db.Column(db.Boolean, default=False)
    can_manage_accounting = db.Column(db.Boolean, default=False)
    
    # Sistem Yönetimi
    can_view_users = db.Column(db.Boolean, default=False)
    can_manage_users = db.Column(db.Boolean, default=False)
    can_view_roles = db.Column(db.Boolean, default=False)
    can_manage_roles = db.Column(db.Boolean, default=False)
    can_view_admin_panel = db.Column(db.Boolean, default=False)
    can_manage_system_settings = db.Column(db.Boolean, default=False)
    can_view_logs = db.Column(db.Boolean, default=False)
    
    # Raporlama
    can_view_reports = db.Column(db.Boolean, default=False)
    can_create_reports = db.Column(db.Boolean, default=False)
    can_export_reports = db.Column(db.Boolean, default=False)
    can_view_statistics = db.Column(db.Boolean, default=False)
    
    # Dosya Yönetimi
    can_upload_files = db.Column(db.Boolean, default=False)
    can_download_files = db.Column(db.Boolean, default=False)
    can_delete_files = db.Column(db.Boolean, default=False)
    can_upload_excel = db.Column(db.Boolean, default=False)
    
    # İletişim ve Bildirimler
    can_view_contact = db.Column(db.Boolean, default=False)
    can_send_notifications = db.Column(db.Boolean, default=False)
    can_manage_announcements = db.Column(db.Boolean, default=False)
    
    # Relationships
    user = db.relationship('User', back_populates='permissions')

    @classmethod
    def get_permission_groups(cls):
        """Yetki gruplarını ve açıklamalarını döndürür"""
        return {
            'machine_management': {
                'title': 'Makine Yönetimi',
                'permissions': [
                    ('can_view_machines', 'Makine Yönetimini Görüntüleme'),
                    ('can_add_machines', 'Makine Ekleme'),
                    ('can_edit_machines', 'Makine Düzenleme'),
                    ('can_delete_machines', 'Makine Silme'),
                    ('can_search_machines', 'Makine Arama'),
                    ('can_export_machines', 'Makine Dışa Aktarma'),
                    ('can_list_machines', 'Makine Listesi')
                ]
            },
            'maintenance_management': {
                'title': 'Bakım Yönetimi',
                'permissions': [
                    ('can_view_maintenance', 'Bakımları Görüntüleme'),
                    ('can_add_maintenance', 'Bakım Ekleme'),
                    ('can_edit_maintenance', 'Bakım Düzenleme'),
                    ('can_delete_maintenance', 'Bakım Silme'),
                    ('can_view_maintenance_history', 'Bakım Geçmişi Görüntüleme'),
                    ('can_view_maintenance_reminders', 'Bakım Hatırlatıcıları'),
                    ('can_manage_maintenance_schedules', 'Bakım Programı Yönetimi')
                ]
            },
            'equipment_management': {
                'title': 'Ekipman Yönetimi',
                'permissions': [
                    ('can_view_equipment', 'Ekipmanları Görüntüleme'),
                    ('can_add_equipment', 'Ekipman Ekleme'),
                    ('can_edit_equipment', 'Ekipman Düzenleme'),
                    ('can_delete_equipment', 'Ekipman Silme'),
                    ('can_manage_equipment_status', 'Ekipman Durumu Yönetimi')
                ]
            },
            'parts_catalog': {
                'title': 'Parça ve Katalog',
                'permissions': [
                    ('can_view_parts', 'Parçaları Görüntüleme'),
                    ('can_edit_parts', 'Parça Düzenleme'),
                    ('can_view_catalogs', 'Katalogları Görüntüleme'),
                    ('can_manage_catalogs', 'Katalog Yönetimi'),
                    ('can_view_purchase_prices', 'Satın Alma Fiyatlarını Görme')
                ]
            },
            'offer_management': {
                'title': 'Teklif Yönetimi',
                'permissions': [
                    ('can_view_offers', 'Teklifleri Görüntüleme'),
                    ('can_create_offers', 'Teklif Oluşturma'),
                    ('can_edit_offers', 'Teklif Düzenleme'),
                    ('can_delete_offers', 'Teklif Silme'),
                    ('can_approve_offers', 'Teklif Onaylama'),
                    ('can_reject_offers', 'Teklif Reddetme'),
                    ('can_view_periodic_maintenance', 'Periyodik Bakım Görüntüleme'),
                    ('can_manage_periodic_maintenance', 'Periyodik Bakım Yönetimi')
                ]
            },
            'warranty_accounting': {
                'title': 'Garanti ve Muhasebe',
                'permissions': [
                    ('can_view_warranty', 'Garantileri Görüntüleme'),
                    ('can_manage_warranty', 'Garanti Yönetimi'),
                    ('can_view_accounting', 'Muhasebeyi Görüntüleme'),
                    ('can_manage_accounting', 'Muhasebe Yönetimi')
                ]
            },
            'system_management': {
                'title': 'Sistem Yönetimi',
                'permissions': [
                    ('can_view_users', 'Kullanıcıları Görüntüleme'),
                    ('can_manage_users', 'Kullanıcı Yönetimi'),
                    ('can_view_roles', 'Rolleri Görüntüleme'),
                    ('can_manage_roles', 'Rol Yönetimi'),
                    ('can_view_admin_panel', 'Yönetici Paneli'),
                    ('can_manage_system_settings', 'Sistem Ayarları'),
                    ('can_view_logs', 'Sistem Logları')
                ]
            },
            'reporting': {
                'title': 'Raporlama',
                'permissions': [
                    ('can_view_reports', 'Raporları Görüntüleme'),
                    ('can_create_reports', 'Rapor Oluşturma'),
                    ('can_export_reports', 'Rapor Dışa Aktarma'),
                    ('can_view_statistics', 'İstatistikleri Görüntüleme')
                ]
            },
            'file_management': {
                'title': 'Dosya Yönetimi',
                'permissions': [
                    ('can_upload_files', 'Dosya Yükleme'),
                    ('can_download_files', 'Dosya İndirme'),
                    ('can_delete_files', 'Dosya Silme'),
                    ('can_upload_excel', 'Excel Yükleme')
                ]
            },
            'communication': {
                'title': 'İletişim ve Bildirimler',
                'permissions': [
                    ('can_view_contact', 'İletişim Bilgilerini Görme'),
                    ('can_send_notifications', 'Bildirim Gönderme'),
                    ('can_manage_announcements', 'Duyuru Yönetimi')
                ]
            }
        }

class Announcement(db.Model):
    __tablename__ = 'announcement'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

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
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    solution = db.Column(db.Text)
    machine_model = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FaultSolution(db.Model):
    __tablename__ = 'fault_solution'
    id = db.Column(db.Integer, primary_key=True)
    fault_id = db.Column(db.Integer, db.ForeignKey('fault.id'), nullable=False)
    solution = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FaultReport(db.Model):
    __tablename__ = 'fault_report'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    machine_model = db.Column(db.String(100), nullable=False)
    serial_number = db.Column(db.String(50), nullable=False)
    reported_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='open')  # open, in_progress, resolved, closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MachineModel(db.Model):
    __tablename__ = 'machine_models'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    machine_type_id = db.Column(db.Integer, db.ForeignKey('machine_types.id'), nullable=False)
    description = db.Column(db.String(255))
    machines = db.relationship('Machine', backref='machine_model', lazy=True)
    machine_type = db.relationship('MachineType', backref='models', lazy=True)

class Machine(db.Model):
    __tablename__ = 'machines'
    id = db.Column(db.Integer, primary_key=True)
    serial_number = db.Column(db.String(100), unique=True, nullable=False)
    model = db.Column(db.String(100), nullable=False)
    owner_name = db.Column(db.String(200))
    phone_number = db.Column(db.String(20))
    city = db.Column(db.String(100))
    address = db.Column(db.Text)
    responsible_service = db.Column(db.String(200))
    equipment = db.relationship('Equipment', backref='machine', lazy=True, cascade="all, delete-orphan")
    registration_document = db.Column(db.String(500))  # Registration PDF
    machine_photos = db.Column(db.JSON)  # List of photo URLs
    delivery_date = db.Column(db.DateTime)
    usage_hours = db.Column(db.Integer, default=0)
    last_maintenance_hours = db.Column(db.Integer, default=0)
    last_maintenance_date = db.Column(db.DateTime)
    next_maintenance_hours = db.Column(db.Integer, default=250)
    maintenance_status = db.Column(db.String(50), default='OK')
    machine_type_id = db.Column(db.Integer, db.ForeignKey('machine_types.id'))
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id'))
    registration_step = db.Column(db.Integer, default=1)  # To track the registration progress
    machine_model_id = db.Column(db.Integer, db.ForeignKey('machine_models.id'))

class Equipment(db.Model):
    __tablename__ = 'equipment'
    
    id = db.Column(db.Integer, primary_key=True)
    equipment_type = db.Column(db.String(50), nullable=False)
    subtype = db.Column(db.String(50))
    width = db.Column(db.Integer)  # cm cinsinden
    machine_id = db.Column(db.Integer, db.ForeignKey('machines.id'), nullable=False)
    
    # Status tracking
    status = db.Column(db.String(20), default='PENDING')  # PENDING, IN_PROGRESS, READY, DELIVERED
    delivered_at = db.Column(db.DateTime)
    delivered_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    
    @property
    def status_label(self):
        status_labels = {
            'PENDING': 'warning',
            'IN_PROGRESS': 'info',
            'READY': 'success',
            'DELIVERED': 'primary'
        }
        return status_labels.get(self.status, 'secondary')
    
    @property
    def status_text(self):
        status_texts = {
            'PENDING': 'Beklemede',
            'IN_PROGRESS': 'Hazırlanıyor',
            'READY': 'Teslime Hazır',
            'DELIVERED': 'Teslim Edildi'
        }
        return status_texts.get(self.status, 'Bilinmiyor')
    
    def update_status(self, new_status, user_id, notes=None):
        self.status = new_status
        self.updated_at = datetime.utcnow()
        
        if new_status == 'DELIVERED':
            self.delivered_at = datetime.utcnow()
            self.delivered_by = user_id
            
        if notes:
            self.notes = notes

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
    machine_id = db.Column(db.Integer, db.ForeignKey('machines.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    action_date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text, nullable=False)
    invoice_file = db.Column(db.String(200))
    part_image = db.Column(db.String(200))

class QRCode(db.Model):
    __tablename__ = 'qr_code'
    id = db.Column(db.Integer, primary_key=True)
    qr_code_url = db.Column(db.String(200), unique=True, nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey('machines.id'))
    is_used = db.Column(db.Boolean, default=False)
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

class Oil(db.Model):
    __tablename__ = 'oils'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price_eur = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_price_tl(self, exchange_rate):
        """Calculate TL price based on current exchange rate"""
        return self.price_eur * exchange_rate

class Offer(db.Model):
    __tablename__ = 'offers'

    id = db.Column(db.Integer, primary_key=True)
    offer_number = db.Column(db.String(50), unique=True, nullable=False)
    serial_number = db.Column(db.String(50), nullable=False)
    machine_model = db.Column(db.String(100), nullable=False)
    maintenance_interval = db.Column(db.String(50), nullable=False)
    customer_first_name = db.Column(db.String(50), nullable=False)
    customer_last_name = db.Column(db.String(50), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    filter_type = db.Column(db.String(20), nullable=False)  # 'original' veya 'alternate'
    parts = db.Column(db.Text)  # JSON string olarak saklanacak
    oils = db.Column(db.Text)   # JSON string olarak saklanacak
    labor_cost = db.Column(db.Float, nullable=False)
    travel_cost = db.Column(db.Float, nullable=False)
    discount_type = db.Column(db.String(20))  # 'percentage' veya 'amount'
    discount_value = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    subtotal = db.Column(db.Float, nullable=False)
    grand_total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='Teklif Verildi')
    is_active = db.Column(db.Boolean, default=True)
    invoice_number = db.Column(db.String(50))
    pdf_file_path = db.Column(db.String(200))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)

class MaintenanceReminder(db.Model):
    __tablename__ = 'maintenance_reminder'
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machines.id'), nullable=False)
    reminder_date = db.Column(db.DateTime, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    machine = db.relationship('Machine', backref='maintenance_reminders', lazy=True)
    completed_by_user = db.relationship('User', backref='completed_reminders', lazy=True)

class MaintenanceReminderSettings(db.Model):
    __tablename__ = 'maintenance_reminder_settings'
    id = db.Column(db.Integer, primary_key=True)
    machine_type = db.Column(db.String(100), nullable=True)  # TB215R, TB216, etc.
    first_maintenance_hours = db.Column(db.Integer, nullable=True)  # 50 or 250
    hours_interval = db.Column(db.Integer, nullable=False, default=250)
    notify_before_days = db.Column(db.Integer, nullable=False, default=7)  # Kaç gün önce bildirim yapılacak
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

    @classmethod
    def get_standard_intervals(cls):
        return [500, 750, 1000]

    @classmethod
    def get_machine_types(cls):
        return ['TB215R', 'TB216', 'TB217R', 'TB325R', 'TB235-2', 
                'TB240-2', 'TB260-2', 'TB290-2', 'TL8R-2']

    @classmethod
    def get_first_maintenance_hours(cls, machine_type):
        if machine_type in ['TB215R', 'TB216', 'TB217R']:
            return 50
        return 250

    @classmethod
    def get_maintenance_intervals(cls):
        return [500, 750, 1000]

class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey('machines.id'))
    service_id = db.Column(db.Integer)
    amount_eur = db.Column(db.Float, nullable=False)
    issue_date = db.Column(db.DateTime, nullable=False)
    document_url = db.Column(db.String(200))
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='Beklemede')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class InvoiceApproval(db.Model):
    __tablename__ = 'invoice_approvals'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved = db.Column(db.Boolean, default=False)
    approved_at = db.Column(db.DateTime)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MachineType(db.Model):
    __tablename__ = 'machine_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    machines = db.relationship('Machine', backref='machine_type', lazy=True)

class City(db.Model):
    __tablename__ = 'cities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    region = db.Column(db.String(100))
    machines = db.relationship('Machine', backref='city_rel', lazy=True)