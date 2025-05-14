from flask import Blueprint, render_template, request, flash, redirect, url_for, send_from_directory
from flask_login import login_required, current_user
from database import db
from models import Machine, MachineMaintenanceRecord, QRCode
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timezone

machines = Blueprint('machines', __name__)

UPLOAD_FOLDER = '/var/data/machine'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@machines.route('/')
@login_required
def index():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_machines:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    return render_template('machines.html')

@machines.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_maintenance:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    serial_number = request.args.get('serial_number', '')
    machine = None
    qr_code = None
    if serial_number:
        machine = Machine.query.filter_by(serial_number=serial_number).first()
        if machine:
            qr_code = QRCode.query.filter_by(machine_id=machine.id, is_used=True).first()
    return render_template('machine_search.html', machine=machine, qr_code=qr_code)

@machines.route('/machine-registration', methods=['GET', 'POST'])
@login_required
def machine_registration():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_add_machines:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))

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
            owner_name=owner_name,
            address=address,
            responsible_service=responsible_service
        )

        try:
            db.session.add(new_machine)
            db.session.commit()

            # Get an unused QR code
            qr_code = QRCode.query.filter_by(is_used=False).first()
            if qr_code:
                qr_code.machine_id = new_machine.id
                qr_code.is_used = True
                db.session.commit()
                flash('Makine başarıyla eklendi ve QR kod atandı!', 'success')
            else:
                flash('Makine eklendi fakat QR kod atanamadı - QR kod havuzu boş!', 'warning')

            return redirect(url_for('machines.machine_maintenance', machine_id=new_machine.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Makine eklenirken bir hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('machines.machine_registration'))

    return render_template('new_machine_registration.html')

@machines.route('/machine-search', methods=['GET'])
@login_required
def machine_search():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_search_machines:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))

    serial_number = request.args.get('serial_number', '')
    machine = None
    qr_code = None
    if serial_number:
        machine = Machine.query.filter_by(serial_number=serial_number).first()
        if machine:
            qr_code = QRCode.query.filter_by(machine_id=machine.id, is_used=True).first()
    return render_template('machine_search.html', machine=machine, qr_code=qr_code)

@machines.route('/machine-maintenance/<int:machine_id>', methods=['GET', 'POST'])
@login_required
def machine_maintenance(machine_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_add_maintenance:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))

    try:
        machine_id = int(machine_id)
    except ValueError:
        flash('Geçersiz makine ID.', 'danger')
        return redirect(url_for('machines.machine_search'))

    # Makine ID 0 ise arama sayfasına yönlendir
    if machine_id == 0:
        flash('Lütfen önce bir makine seçin.', 'warning')
        return redirect(url_for('machines.machine_search'))

    # Makineyi bul
    machine = Machine.query.get(machine_id)
    if not machine:
        flash('Makine bulunamadı.', 'danger')
        return redirect(url_for('machines.machine_search'))

    # QR kodu bul
    qr_code = QRCode.query.filter_by(machine_id=machine_id, is_used=True).first()

    # Bakım kayıtlarını al
    records = MachineMaintenanceRecord.query.filter_by(machine_id=machine_id).order_by(MachineMaintenanceRecord.action_date.desc()).all()

    # POST isteği - yeni bakım kaydı ekleme
    if request.method == 'POST':
        if not current_user.permissions.can_edit_maintenance:
            flash('Bakım kaydı ekleme yetkiniz yok.', 'danger')
            return redirect(url_for('machines.machine_maintenance', machine_id=machine_id))

        # Form verilerini al
        action_type = request.form.get('action_type')
        description = request.form.get('description')

        if not action_type or not description:
            flash('Tüm alanları doldurun.', 'danger')
            return redirect(url_for('machines.machine_maintenance', machine_id=machine_id))

        invoice_path = None
        image_path = None

        # Fatura dosyası işleme
        if 'invoice_file' in request.files:
            invoice_file = request.files['invoice_file']
            if invoice_file and invoice_file.filename and allowed_file(invoice_file.filename):
                filename = secure_filename(f"{machine_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{invoice_file.filename}")
                invoice_dir = os.path.join(UPLOAD_FOLDER, 'invoices')
                os.makedirs(invoice_dir, exist_ok=True)
                full_path = os.path.join(invoice_dir, filename)
                invoice_file.save(full_path)
                invoice_path = os.path.join('uploads', 'invoices', filename)

        # Parça resmi işleme
        if 'part_image' in request.files:
            part_image = request.files['part_image']
            if part_image and part_image.filename and allowed_file(part_image.filename):
                filename = secure_filename(f"{machine_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{part_image.filename}")
                image_dir = os.path.join(UPLOAD_FOLDER, 'images')
                os.makedirs(image_dir, exist_ok=True)
                full_path = os.path.join(image_dir, filename)
                part_image.save(full_path)
                image_path = os.path.join('uploads', 'images', filename)

        # Yeni bakım kaydı oluştur
        new_record = MachineMaintenanceRecord(
            machine_id=machine_id,
            action_type=action_type,
            action_date=datetime.now(timezone.utc),
            description=description,
            invoice_file=invoice_path,
            part_image=image_path
        )

        try:
            db.session.add(new_record)
            db.session.commit()
            flash('Bakım kaydı başarıyla eklendi!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Bakım kaydı eklenirken bir hata oluştu: {str(e)}', 'danger')

        return redirect(url_for('machines.machine_maintenance', machine_id=machine_id))

    return render_template('machine_maintenance.html', machine=machine, records=records, qr_code=qr_code)

@machines.route('/delete-maintenance/<int:machine_id>/<int:record_id>')
@login_required
def delete_maintenance_record(machine_id, record_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_maintenance:
        flash('Bu işlemi yapmak için yetkiniz yok!', 'danger')
        return redirect(url_for('machines.machine_maintenance', machine_id=machine_id))

    record = MachineMaintenanceRecord.query.get_or_404(record_id)

    if record.machine_id != machine_id:
        flash('Bu kayıt bu makineye ait değil!', 'danger')
        return redirect(url_for('machines.machine_maintenance', machine_id=machine_id))

    if record.invoice_file and os.path.exists(os.path.join('static', record.invoice_file)):
        os.remove(os.path.join('static', record.invoice_file))
    if record.part_image and os.path.exists(os.path.join('static', record.part_image)):
        os.remove(os.path.join('static', record.part_image))

    db.session.delete(record)
    db.session.commit()

    flash('Bakım kaydı başarıyla silindi!', 'success')
    return redirect(url_for('machines.machine_maintenance', machine_id=machine_id))