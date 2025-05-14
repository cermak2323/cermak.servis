import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from models import Permission, User
from flask import Flask, redirect, url_for, render_template, request, flash
from flask_login import LoginManager, current_user, login_required
from flask_migrate import Migrate
from flask_mail import Mail
from database import db, init_db
from models import User, Machine, MachineMaintenanceRecord, QRCode
from auth.routes import auth
from parts.routes import parts_bp
from catalogs.routes import catalogs_bp
from faults.routes import faults_bp
from contact.routes import contact_bp
from maintenance.routes import maintenance_bp
from warranty.routes import warranty_bp
from accounting.routes import accounting_bp
from periodic_maintenance.routes import periodic_maintenance_bp
from offers.routes import offers
from machines.routes import machines
from werkzeug.utils import secure_filename
from utils import exchange_rates, fetch_exchange_rates, scheduler, logger
from datetime import datetime, timezone
import qrcode
from werkzeug.security import generate_password_hash
from sqlalchemy.sql import text


# Logging yapılandırması
logger.info("Uygulama başlatılıyor...")

app = Flask(__name__)
app.config.from_object('config.Config')

# Flask-Mail başlatma
mail = Mail(app)

# Dosya yükleme için yapılandırma
UPLOAD_FOLDER = os.path.join('static', 'uploads')
QR_CODE_FOLDER = os.path.join('static', 'qrcodes')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_CODE_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['QR_CODE_FOLDER'] = QR_CODE_FOLDER

# os modülünü Jinja2 ortamına ekle
app.jinja_env.globals['os'] = os

# Veritabanı başlatma
init_db(app)

# Flask-Migrate başlatma
migrate = Migrate(app, db)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# TL fiyat formatlama filtresi
@app.template_filter('format_currency')
def format_currency(value):
    if value is None:
        return '-'
    return f"{value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') + " TL"

# Blueprint'leri kaydetme
app.register_blueprint(auth, url_prefix='/auth')
app.register_blueprint(parts_bp, url_prefix='/parts')
app.register_blueprint(catalogs_bp, url_prefix='/catalogs')
app.register_blueprint(faults_bp, url_prefix='/faults')
app.register_blueprint(contact_bp, url_prefix='/contact')
app.register_blueprint(maintenance_bp, url_prefix='/maintenance')
app.register_blueprint(warranty_bp, url_prefix='/warranty')
app.register_blueprint(accounting_bp, url_prefix='/accounting')
app.register_blueprint(periodic_maintenance_bp, url_prefix='/periodic_maintenance')
app.register_blueprint(offers, url_prefix='/offers')
app.register_blueprint(machines, url_prefix='/machines')

# Kök rota
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    return redirect(url_for('auth.login'))

# Kullanıcıları ve yetkileri oluşturma
def create_users():
    with app.app_context():
        if User.query.count() > 0:
            logger.info("Kullanıcılar zaten mevcut, ekleme yapılmadı.")
            return

        # Kullanıcı listeleri
        servis_users = [f"servis{i}" for i in range(1, 45)]
        muhendis_users = [f"Mühendis{i}" for i in range(1, 5)]
        admin_users = [{"username": "admin1", "role": "admin", "password": "password123"}]
        guest_user = {"username": "guest_musteri", "role": "musteri", "password": "guest_password"}

        # Yetkili Servis varsayılan yetkileri
        servis_permissions = {
            "can_view_parts": True,
            "can_edit_parts": False,
            "can_view_faults": True,
            "can_add_solutions": False,
            "can_view_catalogs": False,
            "can_view_maintenance": True,
            "can_edit_maintenance": True,
            "can_view_contact": True,
            "can_view_purchase_prices": False,
            "can_view_warranty": False,
            "can_view_accounting": False,
            "can_view_periodic_maintenance": False,
            "can_view_machines": True
        }

        # Mühendis varsayılan yetkileri
        muhendis_permissions = {
            "can_view_parts": True,
            "can_edit_parts": False,
            "can_view_faults": True,
            "can_add_solutions": True,
            "can_view_catalogs": True,
            "can_view_maintenance": True,
            "can_edit_maintenance": False,
            "can_view_contact": True,
            "can_view_purchase_prices": False,
            "can_view_warranty": True,
            "can_view_accounting": True,
            "can_view_periodic_maintenance": True
        }

        # Müşteri varsayılan yetkileri
        musteri_permissions = {
            "can_view_parts": True,
            "can_edit_parts": False,
            "can_view_faults": True,
            "can_add_solutions": False,
            "can_view_catalogs": False,
            "can_view_maintenance": False,
            "can_edit_maintenance": False,
            "can_view_contact": True,
            "can_view_purchase_prices": False,
            "can_view_warranty": False,
            "can_view_accounting": False,
            "can_view_periodic_maintenance": False
        }

        # Admin varsayılan yetkileri
        admin_permissions = {
            "can_view_parts": True,
            "can_edit_parts": True,
            "can_view_faults": True,
            "can_add_solutions": True,
            "can_view_catalogs": True,
            "can_view_maintenance": True,
            "can_edit_maintenance": True,
            "can_view_contact": True,
            "can_view_purchase_prices": True,
            "can_view_warranty": True,
            "can_view_accounting": True,
            "can_view_periodic_maintenance": True
        }

        # Kullanıcıları ve yetkileri ekle
        for username in servis_users:
            user = User(
                username=username,
                password=generate_password_hash("Cermak.2025", method='pbkdf2:sha256'),
                role='servis'
            )
            db.session.add(user)
            db.session.flush()
            permission = Permission(user_id=user.id, **servis_permissions)
            db.session.add(permission)

        for username in muhendis_users:
            user = User(
                username=username,
                password=generate_password_hash("Cermak.2025", method='pbkdf2:sha256'),
                role='muhendis'
            )
            db.session.add(user)
            db.session.flush()
            permission = Permission(user_id=user.id, **muhendis_permissions)
            db.session.add(permission)

        for admin in admin_users:
            user = User(
                username=admin['username'],
                password=generate_password_hash(admin['password'], method='pbkdf2:sha256'),
                role=admin['role']
            )
            db.session.add(user)
            db.session.flush()
            permission = Permission(user_id=user.id, **admin_permissions)
            db.session.add(permission)

        guest = User(
            username=guest_user['username'],
            password=generate_password_hash(guest_user['password'], method='pbkdf2:sha256'),
            role=guest_user['role']
        )
        db.session.add(guest)
        db.session.flush()
        permission = Permission(user_id=guest.id, **musteri_permissions)
        db.session.add(permission)

        db.session.commit()
        logger.info("Kullanıcılar ve yetkiler başarıyla oluşturuldu.")

# Dosya uzantısını kontrol etme
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# E-posta gönderme fonksiyonu
def send_email(subject, recipients, body):
    try:
        msg = Message(subject=subject, recipients=recipients, body=body)
        mail.send(msg)
        logger.info(f"E-posta gönderildi: {recipients}")
    except Exception as e:
        logger.error(f"E-posta gönderim hatası: {str(e)}")

# QR kod oluşturma fonksiyonu
def generate_qr_code_for_pool(qr_id):
    qr_url = f"http://127.0.0.1:5000/machines/maintenance/{qr_id}"
    qr_filename = f"qr_{qr_id}.png"
    os.makedirs(app.config['QR_CODE_FOLDER'], exist_ok=True)
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_url)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    qr_path = os.path.join(app.config['QR_CODE_FOLDER'], secure_filename(qr_filename))
    try:
        img.save(qr_path)
        print(f"QR kod oluşturuldu: {qr_path}")
    except Exception as e:
        print(f"QR kod oluşturma hatası: {e}")
        return None
    return os.path.join('qrcodes', qr_filename).replace('\\', '/')

# Havuz için 1000 QR kod oluşturma
def generate_qr_code_pool(count=1000):
    with app.app_context():
        existing_qr_codes = QRCode.query.count()
        if existing_qr_codes >= count:
            print(f"Zaten {existing_qr_codes} adet QR kod mevcut.")
            return
        for i in range(existing_qr_codes + 1, count + 1):
            qr_code_url = generate_qr_code_for_pool(i)
            if qr_code_url:
                try:
                    new_qr_code = QRCode(
                        qr_code_url=qr_code_url,
                        is_used=False,
                        created_at=datetime.now(timezone.utc)
                    )
                    db.session.add(new_qr_code)
                    db.session.commit()
                    print(f"QR kod {i}/{count} oluşturuldu.")
                except Exception as e:
                    print(f"QR kod eklenirken hata: {e}")
                    db.session.rollback()

# Makine için QR kod atama
def assign_qr_code_to_machine(machine_id):
    with app.app_context():
        try:
            machine = Machine.query.get(machine_id)
            if not machine:
                print(f"Hata: Makine ID {machine_id} bulunamadı!")
                return None
            existing_qr_code = QRCode.query.filter_by(machine_id=machine_id, is_used=True).first()
            if existing_qr_code:
                print(f"QR kod zaten atanmış: ID {existing_qr_code.id}, URL {existing_qr_code.qr_code_url}")
                return existing_qr_code.qr_code_url
            qr_code = QRCode.query.filter_by(is_used=False).first()
            if not qr_code:
                print("Hata: Kullanılabilir QR kod bulunamadı!")
                return None
            qr_code.machine_id = machine_id
            qr_code.is_used = True
            db.session.commit()
            print(f"QR kod {qr_code.id} makine ID {machine_id}'e atandı.")
            return qr_code.qr_code_url
        except Exception as e:
            print(f"QR kod atanırken hata: {str(e)}")
            db.session.rollback()
            return None

# Makine Listesi ve Yeni Makine Ekleme

@app.route('/machine-registration', methods=['GET', 'POST'])
def machine_registration():
    machine = None
    if request.method == 'GET' and 'serial_number' in request.args:
        serial_number = request.args.get('serial_number')
        machine = Machine.query.filter_by(serial_number=serial_number).first()
    if request.method == 'POST':
        serial_number = request.form.get('serial_number')
        model = request.form.get('model')
        owner_name = request.form.get('owner_name')
        address = request.form.get('address')
        responsible_service = request.form.get('responsible_service')
        if Machine.query.filter_by(serial_number=serial_number).first():
            flash('Bu seri numarası zaten kayıtlı!', 'danger')
            return redirect(url_for('machines.machine_registration'))
        new_machine = Machine(
            serial_number=serial_number,
            model=model,
            owner_name=owner_name if owner_name else None,
            address=address if address else None,
            responsible_service=responsible_service if responsible_service else None
        )
        db.session.add(new_machine)
        db.session.commit()
        qr_code_url = assign_qr_code_to_machine(new_machine.id)
        if qr_code_url:
            flash('Makine başarıyla eklendi ve QR kod atandı!', 'success')
        else:
            flash('Makine eklendi, ancak QR kod atanamadı!', 'warning')
        return redirect(url_for('machines.machine_registration'))
    return render_template('machines.html', machine=machine)

# Makine Bakım Sayfası
@app.route('/machines/maintenance/<int:machine_id>', methods=['GET', 'POST'])
def machine_maintenance(machine_id):
    machine = Machine.query.get_or_404(machine_id)
    qr_code = QRCode.query.filter_by(machine_id=machine_id, is_used=True).first()
    if not qr_code:
        qr_code_url = assign_qr_code_to_machine(machine_id)
        if qr_code_url:
            qr_code = QRCode.query.filter_by(qr_code_url=qr_code_url, is_used=True).first()
        else:
            print(f"Uyarı: Makine ID {machine_id} için QR kod atanamadı.")
            flash('QR kod atanamadı, lütfen tekrar deneyin veya yöneticiyle iletişime geçin.', 'warning')
    records = MachineMaintenanceRecord.query.filter_by(machine_id=machine_id).order_by(MachineMaintenanceRecord.action_date.desc()).all()
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('Bakım kaydı eklemek için giriş yapmalısınız.', 'danger')
            return redirect(url_for('auth.login'))
        if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_maintenance:
            flash('Bakım kaydı ekleme yetkiniz yok.', 'danger')
            return redirect(url_for('machine_maintenance', machine_id=machine_id))
        action_type = request.form.get('action_type')
        description = request.form.get('description')
        invoice_file = request.files.get('invoice_file')
        part_image = request.files.get('part_image')
        invoice_path = None
        part_image_path = None
        if invoice_file and allowed_file(invoice_file.filename):
            invoice_filename = secure_filename(invoice_file.filename)
            invoice_path = os.path.join(app.config['UPLOAD_FOLDER'], invoice_filename)
            os.makedirs(os.path.dirname(invoice_path), exist_ok=True)
            invoice_file.save(invoice_path)
            invoice_path = os.path.join('uploads', invoice_filename).replace('\\', '/')
        if part_image and allowed_file(part_image.filename):
            part_image_filename = secure_filename(part_image.filename)
            part_image_path = os.path.join(app.config['UPLOAD_FOLDER'], part_image_filename)
            os.makedirs(os.path.dirname(part_image_path), exist_ok=True)
            part_image.save(part_image_path)
            part_image_path = os.path.join('uploads', part_image_filename).replace('\\', '/')
        new_record = MachineMaintenanceRecord(
            machine_id=machine_id,
            action_type=action_type,
            action_date=datetime.now(timezone.utc),
            description=description,
            invoice_file=invoice_path,
            part_image=part_image_path
        )
        db.session.add(new_record)
        db.session.commit()
        flash('Bakım kaydı başarıyla eklendi!', 'success')
        return redirect(url_for('machine_maintenance', machine_id=machine_id))
    return render_template('machine_maintenance.html', machine=machine, records=records, qr_code=qr_code)

# Bakım Kaydını Silme
@app.route('/machines/maintenance/<int:machine_id>/delete/<int:record_id>')
@login_required
def delete_maintenance_record(machine_id, record_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_maintenance:
        flash('Bu işlemi yapmak için yetkiniz yok!', 'danger')
        return redirect(url_for('machine_maintenance', machine_id=machine_id))
    record = MachineMaintenanceRecord.query.get_or_404(record_id)
    if record.machine_id != machine_id:
        flash('Bu kayıt bu makineye ait değil!', 'danger')
        return redirect(url_for('machine_maintenance', machine_id=machine_id))
    try:
        if record.invoice_file and os.path.exists(os.path.join('static', record.invoice_file)):
            os.remove(os.path.join('static', record.invoice_file))
        if record.part_image and os.path.exists(os.path.join('static', record.part_image)):
            os.remove(os.path.join('static', record.part_image))
    except Exception as e:
        print(f"Dosya silme hatası: {e}")
    db.session.delete(record)
    db.session.commit()
    flash('Bakım kaydı başarıyla silindi!', 'success')
    return redirect(url_for('machine_maintenance', machine_id=machine_id))

# Bakım Kaydını Düzenleme
@app.route('/machines/maintenance/<int:machine_id>/edit/<int:record_id>', methods=['GET', 'POST'])
@login_required
def edit_maintenance_record(machine_id, record_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_maintenance:
        flash('Bu işlemi yapmak için yetkiniz yok!', 'danger')
        return redirect(url_for('machine_maintenance', machine_id=machine_id))
    record = MachineMaintenanceRecord.query.get_or_404(record_id)
    machine = Machine.query.get_or_404(machine_id)
    if record.machine_id != machine_id:
        flash('Bu kayıt bu makineye ait değil!', 'danger')
        return redirect(url_for('machine_maintenance', machine_id=machine_id))
    if request.method == 'POST':
        action_type = request.form.get('action_type')
        description = request.form.get('description')
        invoice_file = request.files.get('invoice_file')
        part_image = request.files.get('part_image')
        if invoice_file and allowed_file(invoice_file.filename):
            if record.invoice_file and os.path.exists(os.path.join('static', record.invoice_file)):
                os.remove(os.path.join('static', record.invoice_file))
            invoice_filename = secure_filename(invoice_file.filename)
            invoice_path = os.path.join(app.config['UPLOAD_FOLDER'], invoice_filename)
            os.makedirs(os.path.dirname(invoice_path), exist_ok=True)
            invoice_file.save(invoice_path)
            record.invoice_file = os.path.join('uploads', invoice_filename).replace('\\', '/')
        if part_image and allowed_file(part_image.filename):
            if record.part_image and os.path.exists(os.path.join('static', record.part_image)):
                os.remove(os.path.join('static', record.part_image))
            part_image_filename = secure_filename(part_image.filename)
            part_image_path = os.path.join(app.config['UPLOAD_FOLDER'], part_image_filename)
            os.makedirs(os.path.dirname(part_image_path), exist_ok=True)
            part_image.save(part_image_path)
            record.part_image = os.path.join('uploads', part_image_filename).replace('\\', '/')
        record.action_type = action_type
        record.description = description
        db.session.commit()
        flash('Bakım kaydı başarıyla güncellendi!', 'success')
        return redirect(url_for('machine_maintenance', machine_id=machine_id))
    return render_template('edit_machine_maintenance_record.html', machine=machine, record=record)

# Veritabanını sıfırlama ve test verileri ekleme
def initialize_database():
    print(f"Veritabanı bağlantısı: {app.config['SQLALCHEMY_DATABASE_URI']}")
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['QR_CODE_FOLDER'], exist_ok=True)
    with app.app_context():
        try:
            # Veritabanı bağlantısını sıfırla (şema önbelleğini temizle)
            db.session.close_all()
            db.engine.dispose()
            print("Veritabanı bağlantısı sıfırlandı.")

            # Eklenen hata ayıklama
            from models import User, Permission, Part, Catalog, CatalogItem, Fault, FaultSolution, FaultReport, Machine, MaintenanceRecord, MachineMaintenanceRecord, QRCode, Warranty, Invoice, PeriodicMaintenance, Offer
            print("Modeller yüklendi:", [model.__name__ for model in [User, Permission, Part, Catalog, CatalogItem, Fault, FaultSolution, FaultReport, Machine, MaintenanceRecord, MachineMaintenanceRecord, QRCode, Warranty, Invoice, PeriodicMaintenance, Offer]])
            print("Tablolar oluşturulmadan önceki tablo listesi:", db.metadata.tables.keys())
            db.create_all()
            print("Tablolar oluşturuldu veya zaten mevcut.")
            print("Tablolar oluşturulduktan sonraki tablo listesi:", db.metadata.tables.keys())

            # WAL modunu etkinleştir
            with db.engine.connect() as connection:
                connection.execute(text("PRAGMA journal_mode=WAL"))
            print("WAL modu etkinleştirildi.")

            # İndeks oluşturma
            with db.engine.connect() as connection:
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_user_username ON user(username)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_machine_serial_number ON machine(serial_number)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_periodic_maintenance_model ON periodic_maintenance(machine_model)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_periodic_maintenance_interval ON periodic_maintenance(maintenance_interval)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_offer_number ON offer(offer_number)"))
                connection.commit()
            print("İndeksler oluşturuldu veya zaten mevcut.")

            create_users()  # Kullanıcıları oluştur
            generate_qr_code_pool(1000)
            if not Catalog.query.filter_by(slug='excavators').first():
                excavators = Catalog(name="Ekskavatörler", slug="excavators")
                db.session.add(excavators)
                db.session.commit()
                print("Katalog 'Ekskavatörler' eklendi.")
            if not Catalog.query.filter_by(slug='tl-loader').first():
                tl_loader = Catalog(name="TL Loader", slug="tl-loader")
                db.session.add(tl_loader)
                db.session.commit()
                print("Katalog 'TL Loader' eklendi.")
            excavator_models = [
                "TB215R", "TB216", "TB217", "TB225", "TB138FR", "TB325R", "TB23R", "TB228",
                "TB235", "TB235-2", "TB240", "TB240-2", "TB250", "TB153FR",
                "TB260", "TB260-2", "TB285", "TB290-2"
            ]
            for model in excavator_models:
                if not CatalogItem.query.filter_by(name=model).first():
                    excavator_item = CatalogItem(
                        catalog_id=Catalog.query.filter_by(slug='excavators').first().id,
                        name=model,
                        motor_pdf_url=f"uploads/motor_{model.lower()}.pdf",
                        yedek_parca_pdf_url=f"uploads/yedek_parca_{model.lower()}.pdf",
                        operator_pdf_url=f"uploads/operator_{model.lower()}.pdf",
                        service_pdf_url=f"uploads/service_{model.lower()}.pdf"
                    )
                    db.session.add(excavator_item)
                    db.session.commit()
                    print(f"Test CatalogItem '{model}' eklendi.")
            test_parts = [
                {
                    "part_code": "PC001",
                    "name": "Filtre",
                    "alternate_part_code": "PC001-C",
                    "price_eur": 10.0
                },
                {
                    "part_code": "PC002",
                    "name": "Yağ Pompası",
                    "alternate_part_code": "PC002-C",
                    "price_eur": 20.0
                },
                {
                    "part_code": "PC001-C",
                    "name": "Filtre (Muadil)",
                    "alternate_part_code": "PC001",
                    "price_eur": 8.0
                },
                {
                    "part_code": "PC002-C",
                    "name": "Yağ Pompası (Muadil)",
                    "alternate_part_code": "PC002",
                    "price_eur": 15.0
                },
                {
                    "part_code": "119305-35150",
                    "name": "Motor Yağ Filtresi",
                    "alternate_part_code": "119305-35150-C",
                    "price_eur": 14.0
                },
                {
                    "part_code": "Y129004-55801",
                    "name": "Yakıt Filtresi",
                    "alternate_part_code": "Y129004-55801-C",
                    "price_eur": 15.0
                },
                {
                    "part_code": "15511-01300",
                    "name": "Hidrolik Filtre",
                    "alternate_part_code": "15511-01300-C",
                    "price_eur": 18.0
                }
            ]
            for part_data in test_parts:
                if not Part.query.filter_by(part_code=part_data['part_code']).first():
                    new_part = Part(**part_data)
                    db.session.add(new_part)
                    db.session.commit()
                    print(f"Test Part '{part_data['part_code']}' eklendi.")
            test_machines = [
                {"serial_number": "SN12345", "model": "TB225"},
                {"serial_number": "SN67890", "model": "TB260"}
            ]
            for machine_data in test_machines:
                if not Machine.query.filter_by(serial_number=machine_data['serial_number']).first():
                    new_machine = Machine(
                        serial_number=machine_data['serial_number'],
                        model=machine_data['model'],
                        owner_name='Test Owner',
                        address='Test Address',
                        responsible_service='Test Service'
                    )
                    db.session.add(new_machine)
                    db.session.commit()
                    qr_code_url = assign_qr_code_to_machine(new_machine.id)
                    if qr_code_url:
                        print(f"Test Machine '{machine_data['serial_number']}' eklendi ve QR kod atandı.")
                    else:
                        print(f"Test Machine '{machine_data['serial_number']}' eklendi, ancak QR kod atanamadı.")
                    test_records = [
                        {
                            "machine_id": new_machine.id,
                            "action_type": "Bakım",
                            "action_date": datetime.now(timezone.utc),
                            "description": "Yağ değişimi yapıldı.",
                            "invoice_file": None,
                            "part_image": None
                        },
                        {
                            "machine_id": new_machine.id,
                            "action_type": "Parça Değişimi",
                            "action_date": datetime.now(timezone.utc),
                            "description": "Kepçe dişi değiştirildi.",
                            "invoice_file": None,
                            "part_image": None
                        }
                    ]
                    for record_data in test_records:
                        if not MachineMaintenanceRecord.query.filter_by(machine_id=record_data['machine_id'], description=record_data['description']).first():
                            new_record = MachineMaintenanceRecord(**record_data)
                            db.session.add(new_record)
                            db.session.commit()
                            print(f"Test MachineMaintenanceRecord for Machine '{machine_data['serial_number']}' eklendi.")
            tb215r = CatalogItem.query.filter_by(name="TB215R").first()
            if tb215r:
                test_records = [
                    {
                        "catalog_item_id": tb215r.id,
                        "maintenance_date": datetime.now(timezone.utc),
                        "description": "Yağ değişimi yapıldı.",
                        "invoice_file": None,
                        "image_file": None
                    },
                    {
                        "catalog_item_id": tb215r.id,
                        "maintenance_date": datetime.now(timezone.utc),
                        "description": "Kepçe dişi değiştirildi.",
                        "invoice_file": None,
                        "image_file": None
                    }
                ]
                for record_data in test_records:
                    if not MaintenanceRecord.query.filter_by(catalog_item_id=record_data['catalog_item_id'], description=record_data['description']).first():
                        new_record = MaintenanceRecord(**record_data)
                        db.session.add(new_record)
                        db.session.commit()
                        print(f"Test MaintenanceRecord for CatalogItem '{tb215r.name}' eklendi.")
            admin_user = User.query.filter_by(username='admin1').first()
            if admin_user:
                machine = Machine.query.filter_by(serial_number='SN12345').first()
                if machine and not Warranty.query.filter_by(serial_number='SN12345').first():
                    warranty = Warranty(                        machine_id=machine.id,
                        serial_number='SN12345',
                        start_date=datetime.now(timezone.utc),
                        end_date=datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year + 2),
                        description='TB225 için 2 yıllık garanti',
                        document_url='uploads/warranty_sn12345.pdf',
                        created_by=admin_user.id,
                        created_at=datetime.now(timezone.utc)
                    )
                    db.session.add(warranty)
                    db.session.commit()
                    print("Test Warranty for SN12345 eklendi.")
                maintenance_record = MachineMaintenanceRecord.query.filter_by(machine_id=machine.id, description='Yağ değişimi yapıldı.').first()
                if maintenance_record and not Invoice.query.filter_by(invoice_number='INV001').first():
                    invoice = Invoice(
                        invoice_number='INV001',
                        machine_id=machine.id,
                        service_id=maintenance_record.id,
                        amount_eur=150.0,
                        issue_date=datetime.now(timezone.utc),
                        document_url='uploads/invoice_inv001.pdf',
                        description='Yağ değişimi faturası',
                        created_by=admin_user.id,
                        created_at=datetime.now(timezone.utc)
                    )
                    db.session.add(invoice)
                    db.session.commit()
                    print("Test Invoice INV001 eklendi.")
                if not PeriodicMaintenance.query.filter_by(machine_model='TB216').first():
                    maintenance_data = [
                        {
                            'machine_model': 'TB216',
                            'filter_name': 'Motor Yağ Filtresi',
                            'filter_part_code': '119305-35150',
                            'alternate_part_code': '119305-35150-C',
                            'original_price_eur': 14.0,
                            'alternate_price_eur': 15.0,
                            'maintenance_interval': '500 Saatlik Bakım',
                            'created_by': 'admin1',
                            'created_at': datetime.now(timezone.utc)
                        },
                        {
                            'machine_model': 'TB216',
                            'filter_name': 'Yakıt Filtresi',
                            'filter_part_code': 'Y129004-55801',
                            'alternate_part_code': 'Y129004-55801-C',
                            'original_price_eur': 15.0,
                            'alternate_price_eur': 16.0,
                            'maintenance_interval': '500 Saatlik Bakım',
                            'created_by': 'admin1',
                            'created_at': datetime.now(timezone.utc)
                        },
                        {
                            'machine_model': 'TB216',
                            'filter_name': 'Hidrolik Filtre',
                            'filter_part_code': '15511-01300',
                            'alternate_part_code': '15511-01300-C',
                            'original_price_eur': 18.0,
                            'alternate_price_eur': 19.0,
                            'maintenance_interval': '50 Saatlik Bakım',
                            'created_by': 'admin1',
                            'created_at': datetime.now(timezone.utc)
                        }
                    ]
                    for data in maintenance_data:
                        maintenance = PeriodicMaintenance(**data)
                        db.session.add(maintenance)
                    try:
                        db.session.commit()
                        print("Test PeriodicMaintenance for TB216 eklendi.")
                    except Exception as e:
                        db.session.rollback()
                        print(f"PeriodicMaintenance eklenirken hata: {str(e)}")
                # Test verisi ekleme: Offer tablosu
                if not Offer.query.filter_by(offer_number='OFFER001').first():
                    test_offer = Offer(
                        offer_number='OFFER001',
                        machine_model='TB225',
                        maintenance_interval='500 Saatlik Bakım',
                        serial_number='SN12345',
                        filter_type='Motor Yağ Filtresi',
                        customer_first_name='Ahmet',
                        customer_last_name='Soyadı',
                        company_name='ABC Şirketi',
                        phone='5551234567',
                        offeror_name='Servis1',
                        labor_cost=100.0,
                        travel_cost=50.0,
                        total_amount=1500.0,
                        discount_type='Yüzde',
                        discount_value=10.0,
                        status='Teklif Hazırlandı',
                        created_by=admin_user.id,
                        created_at=datetime.now(timezone.utc),
                        is_active=True,
                        approved_by=None,
                        approved_at=None
                    )
                    db.session.add(test_offer)
                    db.session.commit()
                    print("Test Offer 'OFFER001' eklendi.")
        except Exception as e:
            db.session.rollback()
            print(f"Veritabanı başlatma hatası: {str(e)}")
            raise

if __name__ == '__main__':
    with app.app_context():
        initialize_database()
        fetch_exchange_rates()
    try:
        scheduler.start()
        logger.info("Döviz kuru güncelleme zamanlayıcısı başlatıldı.")
        app.run(debug=True, host='0.0.0.0', port=5000)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Zamanlayıcı durduruldu.")