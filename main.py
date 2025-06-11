import sys
import os

# Modül yollarını ekle
current_dir = os.path.abspath(os.path.dirname(__file__))
for module_dir in ['parts', 'auth', 'catalogs', 'faults', 'contact', 'maintenance', 
                  'periodic_maintenance', 'offers', 'machines']:
    module_path = os.path.join(current_dir, module_dir)
    if module_path not in sys.path and os.path.exists(module_path):
        sys.path.append(module_path)

from models import Permission, User
from flask import Flask, redirect, url_for, render_template, request, flash, send_from_directory
from flask_login import LoginManager, current_user, login_required
from flask_migrate import Migrate
from flask_mail import Mail, Message
from database import db, init_db
from models import User, Machine, MachineMaintenanceRecord, QRCode, PeriodicMaintenance, Offer

# Blueprint importları
try:
    from auth.routes import auth
    from parts.routes import parts_bp
    from catalogs.routes import catalogs_bp
    from faults.routes import faults_bp
    from contact.routes import contact_bp
    from maintenance.routes import maintenance_bp
    from periodic_maintenance.routes import periodic_maintenance_bp
    from offers.routes import offers
    from machines.routes import machines_bp as machines
except ImportError as e:
    print(f"Modül import hatası: {str(e)}")
    sys.exit(1)

from werkzeug.utils import secure_filename
from utils import exchange_rates, fetch_exchange_rates, scheduler, logger
from datetime import datetime, timezone
import qrcode
from werkzeug.security import generate_password_hash
from sqlalchemy.sql import text
from config import Config
from init_data import initialize_data


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

# QR kodlar için static dosya sunucusu ayarları
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Cache'i devre dışı bırak
app.config['STATIC_FOLDER'] = os.path.join(app.root_path, 'static')

# QR kod klasörlerini oluştur
qr_code_folder = os.path.join(app.static_folder, 'qrcodes')
os.makedirs(qr_code_folder, exist_ok=True)

# os modülünü Jinja2 ortamına ekle
app.jinja_env.globals['os'] = os

# Veritabanı başlatma
init_db(app)

# Flask-Migrate başlatma
migrate = Migrate()
migrate.init_app(app, db)

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
            "can_view_machines": True,
            "can_add_machines": True,
            "can_edit_machines": True,
            "can_search_machines": True,
            "can_list_machines": True,
            "can_view_maintenance": True,
            "can_add_maintenance": True,
            "can_edit_maintenance": True,
            "can_view_maintenance_reminders": True,
            "can_view_equipment": True,
            "can_add_equipment": True,
            "can_edit_equipment": True,
            "can_manage_equipment_status": True,
            "can_view_parts": True,
            "can_view_catalogs": True,
            "can_view_offers": True,
            "can_create_offers": True,
            "can_view_periodic_maintenance": True,
            "can_view_contact": True
        }

        # Mühendis varsayılan yetkileri
        muhendis_permissions = {
            "can_view_machines": True,
            "can_search_machines": True,
            "can_list_machines": True,
            "can_view_maintenance": True,
            "can_view_maintenance_history": True,
            "can_view_equipment": True,
            "can_edit_equipment": True,
            "can_manage_equipment_status": True,
            "can_view_parts": True,
            "can_edit_parts": True,
            "can_view_catalogs": True,
            "can_manage_catalogs": True,
            "can_view_offers": True,
            "can_approve_offers": True,
            "can_reject_offers": True,
            "can_view_periodic_maintenance": True,
            "can_manage_periodic_maintenance": True,
            "can_view_contact": True,
            "can_view_purchase_prices": True,
            "can_view_warranty": True,
            "can_view_accounting": True
        }

        # Müşteri varsayılan yetkileri
        musteri_permissions = {
            "can_view_machines": True,
            "can_search_machines": True,
            "can_list_machines": True,
            "can_view_maintenance": True,
            "can_view_maintenance_history": True,
            "can_view_equipment": True,
            "can_view_parts": True,
            "can_view_offers": True,
            "can_view_contact": True
        }

        # Admin varsayılan yetkileri (tüm yetkiler)
        admin_permissions = {
            "can_view_machines": True,
            "can_add_machines": True,
            "can_edit_machines": True,
            "can_delete_machines": True,
            "can_search_machines": True,
            "can_export_machines": True,
            "can_list_machines": True,
            "can_view_maintenance": True,
            "can_add_maintenance": True,
            "can_edit_maintenance": True,
            "can_delete_maintenance": True,
            "can_view_maintenance_history": True,
            "can_view_maintenance_reminders": True,
            "can_manage_maintenance_schedules": True,
            "can_view_equipment": True,
            "can_add_equipment": True,
            "can_edit_equipment": True,
            "can_delete_equipment": True,
            "can_manage_equipment_status": True,
            "can_view_parts": True,
            "can_edit_parts": True,
            "can_view_catalogs": True,
            "can_manage_catalogs": True,
            "can_view_purchase_prices": True,
            "can_view_offers": True,
            "can_create_offers": True,
            "can_edit_offers": True,
            "can_delete_offers": True,
            "can_approve_offers": True,
            "can_reject_offers": True,
            "can_view_periodic_maintenance": True,
            "can_manage_periodic_maintenance": True,
            "can_view_contact": True,
            "can_view_warranty": True,
            "can_view_accounting": True,
            "can_view_admin_panel": True,
            "can_manage_users": True,
            "can_upload_excel": True
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
    # Tam URL'yi oluştur (production için domain adresini config'den al)
    base_url = "https://cermakservis.onrender.com"
    
    # Makineyi bul
    machine = Machine.query.get(qr_id)
    if not machine:
        return None
        
    qr_url = f"{base_url}/machines/machine-search?serial_number={machine.serial_number}"  # Seri numarasına göre arama yap
    qr_filename = f"qr_{qr_id}.png"
    
    os.makedirs(app.config['QR_CODE_FOLDER'], exist_ok=True)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=5
    )
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
def generate_qr_code_pool(count=400):
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
    return redirect(url_for('machines.add_machine'))

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
    with app.app_context():
        # Create all tables if they don't exist
        db.create_all()
        
        # Create initial users only if there are no users
        if User.query.count() == 0:
            create_users()
            # Initialize reference data
            initialize_data()
        
        # Create indexes
        try:
            connection = db.engine.connect()
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_user_username ON users(username)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_machine_serial ON machines(serial_number)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_offer_number ON offers(offer_number)"))
            connection.close()
        except Exception as e:
            logger.error(f"Index oluşturma hatası: {str(e)}")
            pass

# Mevcut QR kodları güncelle
def update_existing_qr_codes():
    with app.app_context():
        try:
            # Kullanılmış QR kodları al
            used_qr_codes = QRCode.query.filter_by(is_used=True).all()
            
            for qr_code in used_qr_codes:
                if qr_code.machine_id:
                    # Yeni QR kodu oluştur
                    new_qr_url = generate_qr_code_for_pool(qr_code.machine_id)
                    if new_qr_url:
                        # Eski QR kod dosyasını sil
                        old_qr_path = os.path.join(app.config['QR_CODE_FOLDER'], qr_code.qr_code_url.split('/')[-1])
                        if os.path.exists(old_qr_path):
                            os.remove(old_qr_path)
                        
                        # Yeni QR kod URL'sini kaydet
                        qr_code.qr_code_url = new_qr_url
                        db.session.commit()
                        print(f"QR kod güncellendi: Makine ID {qr_code.machine_id}")
            
            print("Tüm QR kodlar başarıyla güncellendi.")
        except Exception as e:
            print(f"QR kodlar güncellenirken hata: {str(e)}")
            db.session.rollback()

# Static dosya sunucusu için özel route
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# QR kod görüntüleme route'u
@app.route('/qr/<path:filename>')
def serve_qr(filename):
    return send_from_directory(os.path.join(app.static_folder, 'qrcodes'), filename)

if __name__ == '__main__':
    with app.app_context():
        initialize_database()
        fetch_exchange_rates()
    # QR kodları güncelle
    update_existing_qr_codes()
    # Döviz kuru güncelleme zamanlayıcısını başlat (her saat başı otomatik güncelle)
    try:
        scheduler.start()
        logger.info('Döviz kuru güncelleme zamanlayıcısı başlatıldı (her saat başı)')
    except Exception as e:
        logger.error(f'Zamanlayıcı başlatılamadı: {e}')
    # Uygulama başlat
    app.run(debug=True, host='0.0.0.0', port=5000)