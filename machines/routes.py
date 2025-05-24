from flask import Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, jsonify
from flask_login import login_required, current_user
from database import db
from models import (
    Machine, MachineMaintenanceRecord, QRCode, MaintenanceReminder, Equipment,
    MachineType, City, MachineModel, EQUIPMENT_TYPES, BUCKET_TYPES, BUCKET_WIDTHS,
    ATTACHMENT_TYPES, MAINTENANCE_KIT_TYPES
)
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timezone
from flask import session
import qrcode
import base64
from io import BytesIO

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename, allowed_extensions=None):
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_EXTENSIONS
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

machines_bp = Blueprint('machines', __name__)

@machines_bp.route('/api/models/<int:type_id>')
@login_required
def get_models_by_type(type_id):
    """API endpoint to get machine models by type ID"""
    try:
        models = MachineModel.query.filter_by(machine_type_id=type_id).all()
        return jsonify([{'id': model.id, 'name': model.name} for model in models])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@machines_bp.route('/equipment/invoice/<int:equipment_id>', methods=['POST'])
@login_required
def upload_invoice(equipment_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_maintenance:
        flash('Bu işlemi yapmak için yetkiniz yok!', 'danger')
        return redirect(url_for('machines.machine_maintenance', machine_id=equipment_id))

    equipment = Equipment.query.get_or_404(equipment_id)

    if 'invoice_file' not in request.files:
        flash('Dosya seçilmedi!', 'danger')
        return redirect(url_for('machines.machine_maintenance', machine_id=equipment.machine_id))

    file = request.files['invoice_file']
    if file.filename == '':
        flash('Dosya seçilmedi!', 'danger')
        return redirect(url_for('machines.machine_maintenance', machine_id=equipment.machine_id))

    if file and allowed_file(file.filename, {'pdf'}):
        filename = secure_filename(f"invoice_{equipment_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        invoice_dir = os.path.join('static', 'uploads', 'invoices')
        os.makedirs(invoice_dir, exist_ok=True)
        file_path = os.path.join(invoice_dir, filename)
        file.save(file_path)

        equipment.invoice_file = os.path.join('uploads', 'invoices', filename)
        print(f"Saved invoice file: {equipment.invoice_file}")  # Debug log

        db.session.commit()

        flash('Fatura başarıyla yüklendi!', 'success')
    else:
        flash('Geçersiz dosya türü! Sadece PDF dosyaları yüklenebilir.', 'danger')

    return redirect(url_for('machines.machine_maintenance', machine_id=equipment.machine_id))

@machines_bp.route('/equipment/delivery-status/<int:equipment_id>', methods=['POST'])
@login_required
def update_equipment_delivery_status(equipment_id):
    equipment = Equipment.query.get_or_404(equipment_id)

    equipment.delivery_status = request.form.get('status')
    delivery_date = request.form.get('delivery_date')
    if delivery_date:
        equipment.delivery_date = datetime.strptime(delivery_date, '%Y-%m-%d')
        equipment.delivered_by = current_user.id

    db.session.commit()
    flash('Ekipman teslim durumu güncellendi.', 'success')
    return redirect(url_for('machines.machine_maintenance', machine_id=equipment.machine_id))

@machines_bp.route('/')
@login_required
def index():
    if not hasattr(current_user, 'permissions'):
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    return render_template('machines.html')

@machines_bp.route('/list')
@login_required
def list_machines():
    if not hasattr(current_user, 'permissions') or not current_user.permissions:
        flash('Kullanıcı yetkileri bulunamadı.', 'danger')
        return redirect(url_for('auth.dashboard'))

    if not current_user.permissions.can_list_machines and current_user.role != 'admin':
        flash('Makine listesini görüntüleme yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))

    machines = Machine.query.all()
    return render_template('machine_list.html', machines=machines)

@machines_bp.route('/search', methods=['GET', 'POST'])
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

@machines_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_machine():
    if not current_user.permissions.can_add_machines:
        flash('Bu işlem için yetkiniz yok!', 'danger')
        return redirect(url_for('auth.dashboard'))

    machine_types = MachineType.query.all()
    cities = City.query.order_by(City.name).all()
    machine_data = session.get('machine_registration_data', {})
    current_step = machine_data.get('step', 1)

    if request.method == 'POST':
        if 'cancel' in request.form:
            session.pop('machine_registration_data', None)
            flash('Makine kaydı iptal edildi.', 'info')
            return redirect(url_for('machines.index'))

        if current_step == 1:
            serial_number = request.form.get('serial_number')
            machine_type_id = request.form.get('machine_type_id')
            machine_model_id = request.form.get('machine_model_id')
            
            if not all([serial_number, machine_type_id, machine_model_id]):
                flash('Lütfen tüm makine bilgilerini doldurun!', 'danger')
                return redirect(url_for('machines.add_machine'))
            
            if Machine.query.filter_by(serial_number=serial_number).first():
                flash('Bu seri numarası zaten kayıtlı!', 'danger')
                return redirect(url_for('machines.add_machine'))

            # Get model name from machine model
            machine_model = MachineModel.query.get(machine_model_id)
            if not machine_model:
                flash('Geçersiz makine modeli!', 'danger')
                return redirect(url_for('machines.add_machine'))
                
            machine_data.update({
                'serial_number': serial_number,
                'machine_type_id': machine_type_id,
                'machine_model_id': machine_model_id,
                'model': machine_model.name,
                'step': 2
            })
            
        elif current_step == 2:
            # Müşteri bilgileri
            owner_name = request.form.get('owner_name')
            phone_number = request.form.get('phone_number')
            city_id = request.form.get('city_id')
            address = request.form.get('address')

            if not all([owner_name, phone_number, city_id, address]):
                flash('Lütfen tüm müşteri bilgilerini doldurun!', 'danger')
                return redirect(url_for('machines.add_machine'))

            machine_data.update({
                'owner_name': owner_name,
                'phone_number': phone_number,
                'city_id': city_id,
                'address': address,
                'step': 3
            })
            
        elif current_step == 3:
            # Ekipman bilgileri
            equipment_list = []
            
            # Kova bilgileri (opsiyonel)
            bucket_types = request.form.getlist('bucket_types[]')
            bucket_widths = request.form.getlist('bucket_widths[]')
            
            # Kova bilgilerini sadece doldurulmuşsa ekle
            for type_name, width in zip(bucket_types, bucket_widths):
                if type_name and width:  # Her iki alan da doldurulmuşsa ekle
                    try:
                        width_int = int(width)
                        if width_int not in BUCKET_WIDTHS:
                            flash(f'Geçersiz kova genişliği: {width}cm', 'danger')
                            return redirect(url_for('machines.add_machine'))
                        
                        if type_name not in BUCKET_TYPES:
                            flash(f'Geçersiz kova tipi: {type_name}', 'danger')
                            return redirect(url_for('machines.add_machine'))
                            
                        equipment_list.append({
                            'equipment_type': EQUIPMENT_TYPES['BUCKET'],
                            'subtype': type_name,
                            'width': width_int
                        })
                    except ValueError:
                        flash(f'Geçersiz kova genişliği formatı: {width}', 'danger')
                        return redirect(url_for('machines.add_machine'))
            
            # Ataşman bilgileri
            attachment_types = request.form.getlist('attachment_types[]')
            for type_name in attachment_types:
                if type_name:
                    if type_name not in ATTACHMENT_TYPES:
                        flash(f'Geçersiz ataşman tipi: {type_name}', 'danger')
                        return redirect(url_for('machines.add_machine'))
                        
                    equipment_list.append({
                        'equipment_type': EQUIPMENT_TYPES['ATTACHMENT'],
                        'subtype': type_name
                    })
            
            # Quickhitch
            if request.form.get('quickhitch') == 'on':
                equipment_list.append({
                    'equipment_type': EQUIPMENT_TYPES['QUICKHITCH']
                })
            
            # Bakım kiti
            maintenance_types = request.form.getlist('maintenance_types[]')
            for type_name in maintenance_types:
                if type_name:
                    if type_name not in MAINTENANCE_KIT_TYPES:
                        flash(f'Geçersiz bakım kiti tipi: {type_name}', 'danger')
                        return redirect(url_for('machines.add_machine'))
                        
                    equipment_list.append({
                        'equipment_type': EQUIPMENT_TYPES['MAINTENANCE_KIT'],
                        'subtype': type_name
                    })
            
            # Ekipman listesi boş olabilir
            machine_data['equipment'] = equipment_list
            machine_data['step'] = 4
            
        elif current_step == 4:
            try:
                # Kayıt belgesi kontrolü
                if 'registration_document' not in request.files:
                    flash('Kayıt belgesi (PDF) yüklemelisiniz!', 'danger')
                    return redirect(url_for('machines.add_machine'))

                registration_doc = request.files['registration_document']
                if not registration_doc or not registration_doc.filename:
                    flash('Kayıt belgesi (PDF) yüklemelisiniz!', 'danger')
                    return redirect(url_for('machines.add_machine'))

                if not allowed_file(registration_doc.filename, {'pdf'}):
                    flash('Kayıt belgesi PDF formatında olmalıdır!', 'danger')
                    return redirect(url_for('machines.add_machine'))

                # Fotoğraf kontrolü
                photo_count = 0
                photos = []
                for i in range(6):
                    photo = request.files.get(f'photo_{i}')
                    if photo and photo.filename:
                        if not allowed_file(photo.filename, {'png', 'jpg', 'jpeg'}):
                            flash('Fotoğraflar PNG, JPG veya JPEG formatında olmalıdır!', 'danger')
                            return redirect(url_for('machines.add_machine'))
                        photo_count += 1

                if photo_count < 1:
                    flash('En az bir fotoğraf yüklemelisiniz!', 'danger')
                    return redirect(url_for('machines.add_machine'))

                # Dosyaları kaydet
                filename = secure_filename(f"reg_doc_{datetime.now().strftime('%Y%m%d%H%M%S')}_{registration_doc.filename}")
                doc_path = os.path.join('static', 'uploads', 'documents', filename)
                os.makedirs(os.path.dirname(doc_path), exist_ok=True)
                registration_doc.save(doc_path)
                # Veritabanı için yolu normalize et
                machine_data['registration_document'] = 'uploads/documents/' + filename

                photos = []
                for i in range(6):
                    photo = request.files.get(f'photo_{i}')
                    if photo and photo.filename:
                        filename = secure_filename(f"photo_{i}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{photo.filename}")
                        photo_path = os.path.join('static', 'uploads', 'photos', filename)
                        os.makedirs(os.path.dirname(photo_path), exist_ok=True)
                        photo.save(photo_path)
                        # Veritabanı için yolu normalize et
                        photos.append('uploads/photos/' + filename)

                machine_data['machine_photos'] = photos
                
                # Create new machine
                machine = Machine(
                    serial_number=machine_data['serial_number'],
                    model=machine_data['model'],
                    machine_type_id=machine_data['machine_type_id'],
                    machine_model_id=machine_data['machine_model_id'],
                    owner_name=machine_data['owner_name'],
                    phone_number=machine_data['phone_number'],
                    city_id=machine_data['city_id'],
                    address=machine_data['address'],
                    registration_document=machine_data['registration_document'],
                    machine_photos=machine_data['machine_photos']
                )
                db.session.add(machine)
                db.session.flush()

                # Add equipment if any
                if machine_data.get('equipment'):
                    for equip_data in machine_data['equipment']:
                        equipment = Equipment(
                            equipment_type=equip_data['equipment_type'],
                            subtype=equip_data.get('subtype'),
                            width=equip_data.get('width'),
                            machine_id=machine.id,
                            delivered_by=current_user.id
                        )
                        db.session.add(equipment)

                # Create and assign QR code
                # QR kod içeriği - Makine sorgulama sayfasına yönlendir
                base_url = "https://cermakservis.onrender.com"
                qr_url = f"{base_url}/machines/machine-search?serial_number={machine.serial_number}"  # Seri numarasına göre arama yap
                
                # QR kod oluştur
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(qr_url)
                qr.make(fit=True)

                # QR kodu resme dönüştür
                img = qr.make_image(fill_color="black", back_color="white")
                
                # Resmi kaydet
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                qr_image = buffer.getvalue()

                # QR kod dosyasını kaydet
                qr_filename = f"qr_code_{machine.serial_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                qr_path = os.path.join('static', 'uploads', 'qr_codes', qr_filename)
                os.makedirs(os.path.dirname(qr_path), exist_ok=True)
                
                with open(qr_path, 'wb') as f:
                    f.write(qr_image)

                # QR kodu veritabanına kaydet (normalize edilmiş yol ile)
                qr_code = QRCode(
                    qr_code_url='uploads/qr_codes/' + qr_filename,
                    machine_id=machine.id,
                    is_used=True
                )
                db.session.add(qr_code)

                # Create maintenance reminders
                from maintenance.routes import create_maintenance_reminders
                create_maintenance_reminders(machine.id)

                db.session.commit()
                session.pop('machine_registration_data', None)
                flash('Makine başarıyla kaydedildi!', 'success')
                return redirect(url_for('machines.list_machines'))

            except Exception as e:
                db.session.rollback()
                flash(f'Hata oluştu: {str(e)}', 'danger')
                return redirect(url_for('machines.add_machine'))

        session['machine_registration_data'] = machine_data
        return redirect(url_for('machines.add_machine'))

    return render_template(
        'add_machine.html',
        current_step=current_step,
        machine_data=machine_data,
        machine_types=machine_types,
        cities=cities,
        bucket_types=BUCKET_TYPES,
        bucket_widths=BUCKET_WIDTHS,
        attachment_types=ATTACHMENT_TYPES,
        maintenance_kit_types=MAINTENANCE_KIT_TYPES,
        equipment_types=EQUIPMENT_TYPES
    )

@machines_bp.route('/machine-search', methods=['GET'])
@login_required
def machine_search():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_maintenance:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))

    serial_number = request.args.get('serial_number', '')
    machine = None
    qr_code = None
    maintenance_records = None
    
    if serial_number:
        machine = Machine.query.filter_by(serial_number=serial_number).first()
        if machine:
            qr_code = QRCode.query.filter_by(machine_id=machine.id, is_used=True).first()
            maintenance_records = MachineMaintenanceRecord.query.filter_by(machine_id=machine.id).order_by(MachineMaintenanceRecord.action_date.desc()).all()
    
    return render_template('machine_search.html', 
                         machine=machine, 
                         qr_code=qr_code, 
                         maintenance_records=maintenance_records)

@machines_bp.route('/edit_machine/<int:machine_id>', methods=['GET', 'POST'])
@login_required
def edit_machine(machine_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_maintenance:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))

    machine = Machine.query.get_or_404(machine_id)

    if request.method == 'POST':
        machine.model = request.form.get('model')
        machine.serial_number = request.form.get('serial_number')
        machine.owner_name = request.form.get('owner_name')
        machine.address = request.form.get('address')
        machine.responsible_service = request.form.get('responsible_service')

        try:
            db.session.commit()
            flash('Makine bilgileri güncellendi.', 'success')
            return redirect(url_for('machines.machine_maintenance', machine_id=machine_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Güncelleme sırasında hata oluştu: {str(e)}', 'danger')

    return render_template('edit_machine.html', machine=machine)

@machines_bp.route('/machine-maintenance/<int:machine_id>', methods=['GET', 'POST'])
@login_required
def machine_maintenance(machine_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_maintenance:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))

    machine = Machine.query.get_or_404(machine_id)
    maintenance_records = MachineMaintenanceRecord.query.filter_by(machine_id=machine_id).order_by(MachineMaintenanceRecord.action_date.desc()).all()
    
    if request.method == 'POST':
        try:
            action_type = request.form.get('action_type')
            action_date = datetime.strptime(request.form.get('action_date'), '%Y-%m-%d')
            description = request.form.get('description')
            
            # Handle file uploads
            invoice_file = request.files.get('invoice_file')
            part_image = request.files.get('part_image')
            
            invoice_filename = None
            part_image_filename = None
            
            if invoice_file and allowed_file(invoice_file.filename):
                invoice_filename = secure_filename(f"{machine.serial_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_invoice.{invoice_file.filename.rsplit('.', 1)[1].lower()}")
                invoice_file.save(os.path.join(current_app.config['DOCUMENTS_FOLDER'], invoice_filename))
            
            if part_image and allowed_file(part_image.filename, {'png', 'jpg', 'jpeg'}):
                part_image_filename = secure_filename(f"{machine.serial_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_part.{part_image.filename.rsplit('.', 1)[1].lower()}")
                part_image.save(os.path.join(current_app.config['PHOTOS_FOLDER'], part_image_filename))
            
            maintenance_record = MachineMaintenanceRecord(
                machine_id=machine_id,
                action_type=action_type,
                action_date=action_date,
                description=description,
                invoice_file=invoice_filename,
                part_image=part_image_filename
            )
            
            db.session.add(maintenance_record)
            
            # Update machine maintenance info
            machine.last_maintenance_date = action_date
            machine.last_maintenance_hours = machine.usage_hours
            machine.next_maintenance_hours = machine.usage_hours + 250  # Next maintenance after 250 hours
            
            db.session.commit()
            flash('Bakım kaydı başarıyla eklendi.', 'success')
            return redirect(url_for('machines.machine_maintenance', machine_id=machine_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Bakım kaydı eklenirken hata oluştu: {str(e)}', 'danger')
    
    return render_template('machines/machine_maintenance.html', machine=machine, maintenance_records=maintenance_records)

@machines_bp.route('/view-machine/<int:machine_id>')
@login_required
def view_machine(machine_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_machines:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))

    machine = Machine.query.get_or_404(machine_id)
    maintenance_records = MachineMaintenanceRecord.query.filter_by(machine_id=machine_id).order_by(MachineMaintenanceRecord.action_date.desc()).limit(5).all()
    
    return render_template('machines/view_machine.html', machine=machine, maintenance_records=maintenance_records)

@machines_bp.route('/delete-maintenance/<int:machine_id>/<int:record_id>')
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

@machines_bp.route('/delete/<int:machine_id>')
@login_required
def delete_machine(machine_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_maintenance:
        flash('Bu işlemi yapmak için yetkiniz yok!', 'danger')
        return redirect(url_for('machines.index'))

    machine = Machine.query.get_or_404(machine_id)

    try:
        # İlişkili kayıtları sil
        MaintenanceReminder.query.filter_by(machine_id=machine_id).delete()
        MachineMaintenanceRecord.query.filter_by(machine_id=machine_id).delete()
        QRCode.query.filter_by(machine_id=machine_id).delete()

        # Makineyi sil
        db.session.delete(machine)
        db.session.commit()
        flash('Makine başarıyla silindi!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Makine silinirken bir hata oluştu: {str(e)}', 'danger')

    return redirect(url_for('machines.index'))

@machines_bp.route('/equipment-status/<int:machine_id>', methods=['GET', 'POST'])
@login_required
def equipment_status(machine_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_equipment:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))

    machine = Machine.query.get_or_404(machine_id)
    
    if request.method == 'POST':
        try:
            for equipment in machine.equipment:
                status_key = f'status_{equipment.id}'
                delivery_date_key = f'delivery_date_{equipment.id}'
                notes_key = f'notes_{equipment.id}'
                
                if status_key in request.form:
                    new_status = request.form[status_key]
                    notes = request.form.get(notes_key, '')
                    equipment.update_status(new_status, current_user.id, notes)
                    
                    if new_status == 'DELIVERED':
                        delivery_date = request.form.get(delivery_date_key)
                        if delivery_date:
                            equipment.delivered_at = datetime.strptime(delivery_date, '%Y-%m-%d')
            
            db.session.commit()
            flash('Ekipman durumları başarıyla güncellendi.', 'success')
            return redirect(url_for('machines.view_machine', machine_id=machine_id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Güncelleme sırasında hata oluştu: {str(e)}', 'danger')
    
    return render_template('machines/equipment_status.html', machine=machine)

@machines_bp.route('/add-maintenance/<int:machine_id>', methods=['GET', 'POST'])
@login_required
def add_maintenance(machine_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_maintenance:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))

    machine = Machine.query.get_or_404(machine_id)
    
    if request.method == 'POST':
        try:
            action_type = request.form.get('action_type')
            description = request.form.get('description')
            action_date = datetime.strptime(request.form.get('action_date'), '%Y-%m-%d')

            if not all([action_type, description, action_date]):
                flash('Lütfen tüm zorunlu alanları doldurun.', 'danger')
                return redirect(url_for('machines.add_maintenance', machine_id=machine_id))

            new_record = MachineMaintenanceRecord(
                machine_id=machine_id,
                action_type=action_type,
                description=description,
                action_date=action_date
            )

            # Fatura PDF'i
            if 'invoice' in request.files:
                invoice = request.files['invoice']
                if invoice and invoice.filename and allowed_file(invoice.filename, {'pdf'}):
                    filename = secure_filename(f"invoice_{datetime.now().strftime('%Y%m%d%H%M%S')}_{invoice.filename}")
                    invoice_path = os.path.join(current_app.config['DOCUMENTS_FOLDER'], filename)
                    invoice.save(invoice_path)
                    new_record.invoice_file = os.path.join('uploads', 'documents', filename)

            # Parça fotoğrafı
            if 'part_image' in request.files:
                part_image = request.files['part_image']
                if part_image and part_image.filename and allowed_file(part_image.filename, {'png', 'jpg', 'jpeg'}):
                    filename = secure_filename(f"part_{datetime.now().strftime('%Y%m%d%H%M%S')}_{part_image.filename}")
                    image_path = os.path.join(current_app.config['PHOTOS_FOLDER'], filename)
                    part_image.save(image_path)
                    new_record.part_image = os.path.join('uploads', 'photos', filename)

            db.session.add(new_record)
            db.session.commit()
            flash('Bakım kaydı başarıyla eklendi!', 'success')
            return redirect(url_for('machines.machine_maintenance', machine_id=machine_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Bakım kaydı eklenirken bir hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('machines.add_maintenance', machine_id=machine_id))

    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('add_maintenance.html', machine=machine, today=today)