from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, current_app
from flask_login import login_required, current_user
from database import db
from models import CatalogItem, MaintenanceRecord, Machine, MaintenanceReminder, MaintenanceReminderSettings, MachineMaintenanceRecord, Equipment
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta
from utils import allowed_file

maintenance_bp = Blueprint('maintenance', __name__)
maintenance_reminders = Blueprint('maintenance_reminders', __name__)

# Dosya yükleme için ayarlar
UPLOAD_FOLDER = 'static/uploads/maintenance'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@maintenance_bp.route('/maintenance/<int:item_id>', methods=['GET', 'POST'])
@login_required
def maintenance_view(item_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_maintenance:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    item = CatalogItem.query.get_or_404(item_id)
    if request.method == 'POST':
        if not current_user.permissions.can_edit_maintenance:
            flash('Bakım kaydı ekleme yetkiniz yok.', 'danger')
            return redirect(url_for('maintenance.maintenance_view', item_id=item_id))
        description = request.form.get('description')
        maintenance_date_str = request.form.get('maintenance_date')
        try:
            maintenance_date = datetime.strptime(maintenance_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError:
            flash('Geçersiz tarih formatı! Lütfen tarihi YYYY-MM-DD formatında girin.', 'danger')
            return redirect(url_for('maintenance.maintenance_view', item_id=item.id))
        invoice_file = request.files.get('invoice_file')
        image_file = request.files.get('image_file')
        invoice_path = None
        image_path = None
        if invoice_file and allowed_file(invoice_file.filename):
            filename = secure_filename(invoice_file.filename)
            invoice_dir = os.path.join(UPLOAD_FOLDER, 'invoices')
            os.makedirs(invoice_dir, exist_ok=True)
            invoice_path = os.path.join(invoice_dir, f"{item_id}_{filename}")
            invoice_file.save(invoice_path)
            invoice_path = f"uploads/maintenance/invoices/{item_id}_{filename}"
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_dir = os.path.join(UPLOAD_FOLDER, 'images')
            os.makedirs(image_dir, exist_ok=True)
            image_path = os.path.join(image_dir, f"{item_id}_{filename}")
            image_file.save(image_path)
            image_path = f"uploads/maintenance/images/{item_id}_{filename}"
        maintenance_record = MaintenanceRecord(
            catalog_item_id=item.id,
            maintenance_date=maintenance_date,
            description=description,
            invoice_file=invoice_path,
            image_file=image_path
        )
        db.session.add(maintenance_record)
        db.session.commit()
        flash('Bakım kaydı başarıyla eklendi!', 'success')
        return redirect(url_for('maintenance.maintenance_view', item_id=item.id))
    records = MaintenanceRecord.query.filter_by(catalog_item_id=item.id).order_by(MaintenanceRecord.maintenance_date.desc()).all()
    return render_template('maintenance.html', item=item, records=records)

@maintenance_bp.route('/maintenance/<int:item_id>/delete/<int:record_id>', methods=['GET'])
@login_required
def delete_maintenance_record(item_id, record_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_maintenance:
        flash('Bu işlemi yapmak için yetkiniz yok!', 'danger')
        return redirect(url_for('maintenance.maintenance_view', item_id=item_id))
    record = MaintenanceRecord.query.get_or_404(record_id)
    if record.catalog_item_id != item_id:
        flash('Bu kayıt bu makineye ait değil!', 'danger')
        return redirect(url_for('maintenance.maintenance_view', item_id=item_id))
    if record.invoice_file and os.path.exists(os.path.join('static', record.invoice_file)):
        os.remove(os.path.join('static', record.invoice_file))
    if record.image_file and os.path.exists(os.path.join('static', record.image_file)):
        os.remove(os.path.join('static', record.image_file))
    db.session.delete(record)
    db.session.commit()
    flash('Bakım kaydı başarıyla silindi!', 'success')
    return redirect(url_for('maintenance.maintenance_view', item_id=item_id))

@maintenance_bp.route('/maintenance/<int:item_id>/edit/<int:record_id>', methods=['GET', 'POST'])
@login_required
def edit_maintenance_record(item_id, record_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_maintenance:
        flash('Bu işlemi yapmak için yetkiniz yok!', 'danger')
        return redirect(url_for('maintenance.maintenance_view', item_id=item_id))
    record = MaintenanceRecord.query.get_or_404(record_id)
    item = CatalogItem.query.get_or_404(item_id)
    if record.catalog_item_id != item_id:
        flash('Bu kayıt bu makineye ait değil!', 'danger')
        return redirect(url_for('maintenance.maintenance_view', item_id=item_id))
    if request.method == 'POST':
        description = request.form.get('description')
        maintenance_date_str = request.form.get('maintenance_date')
        try:
            maintenance_date = datetime.strptime(maintenance_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError:
            flash('Geçersiz tarih formatı! Lütfen tarihi YYYY-MM-DD formatında girin.', 'danger')
        return redirect(url_for('maintenance.edit_maintenance_record', item_id=item_id, record_id=record_id))
    invoice_file = request.files.get('invoice_file')
    image_file = request.files.get('image_file')
    if invoice_file and allowed_file(invoice_file.filename):
        if record.invoice_file and os.path.exists(os.path.join('static', record.invoice_file)):
            os.remove(os.path.join('static', record.invoice_file))
        filename = secure_filename(invoice_file.filename)
        invoice_dir = os.path.join(UPLOAD_FOLDER, 'invoices')
        os.makedirs(invoice_dir, exist_ok=True)
        invoice_path = os.path.join(invoice_dir, f"{item_id}_{filename}")
        invoice_file.save(invoice_path)
        record.invoice_file = f"uploads/maintenance/invoices/{item_id}_{filename}"
    if image_file and allowed_file(image_file.filename):
        if record.image_file and os.path.exists(os.path.join('static', record.image_file)):
            os.remove(os.path.join('static', record.image_file))
        filename = secure_filename(image_file.filename)
        image_dir = os.path.join(UPLOAD_FOLDER, 'images')
        os.makedirs(image_dir, exist_ok=True)
        image_path = os.path.join(image_dir, f"{item_id}_{filename}")
        image_file.save(image_path)
        record.image_file = f"uploads/maintenance/images/{item_id}_{filename}"
    record.maintenance_date = maintenance_date
    record.description = description
    db.session.commit()
    flash('Bakım kaydı başarıyla güncellendi!', 'success')
    return redirect(url_for('maintenance.maintenance_view', item_id=item_id))

    # Return template if not POST request
    return render_template('edit_maintenance_record.html', item=item, record=record)

@maintenance_bp.route('/reminder-system')
@login_required
def reminder_system():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_maintenance:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))

    now_aware = datetime.now(timezone.utc)

    upcoming_reminders = MaintenanceReminder.query.filter(
        MaintenanceReminder.reminder_date >= now_aware,
        MaintenanceReminder.reminder_date <= now_aware + timedelta(days=180),
        MaintenanceReminder.is_completed == False
    ).order_by(MaintenanceReminder.reminder_date).all()

    completed_reminders = MaintenanceReminder.query.filter(
        MaintenanceReminder.is_completed == True
    ).order_by(MaintenanceReminder.completed_at.desc()).limit(10).all()

    machines = Machine.query.order_by(Machine.model).all()
    reminder_settings = MaintenanceReminderSettings.query.all()

    now = datetime.now(timezone.utc)
    return render_template('maintenance/reminder_system.html',
        now=now,
                         upcoming_reminders=upcoming_reminders,
                         completed_reminders=completed_reminders,
                         machines=machines,
                         reminder_settings=reminder_settings,
                         )

@maintenance_bp.route('/reminder-history', methods=['GET'])
@login_required
def reminder_history():
    if not hasattr(current_user, 'permissions') or not (current_user.permissions.can_view_maintenance_reminders or current_user.permissions.can_view_maintenance):
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))

    from models import MaintenanceReminder, Machine

    # Tamamlanan bakım hatırlatıcılarını getir
    completed_reminders = MaintenanceReminder.query.filter(
        MaintenanceReminder.is_completed == True
    ).order_by(MaintenanceReminder.completed_at.desc()).all()

    # Makine bilgilerini yükle
    machines = {}
    for reminder in completed_reminders:
        if reminder.machine_id not in machines:
            machine = Machine.query.get(reminder.machine_id)
            if machine:
                machines[reminder.machine_id] = machine

    # Get current time as aware datetime
    now_aware = datetime.now(timezone.utc)

    # Ensure all reminders have timezone aware dates for proper comparison
    for reminder in completed_reminders:
        if reminder.reminder_date and reminder.reminder_date.tzinfo is None:
            reminder.reminder_date = reminder.reminder_date.replace(tzinfo=timezone.utc)

    return render_template('maintenance/reminder_system.html', 
                           upcoming_maintenances=completed_reminders, 
                           machines=machines,
                           now=now_aware, 
                           is_history=True)

@maintenance_bp.route('/maintenance-settings', methods=['GET'])
@login_required
def maintenance_settings():
    if not current_user.permissions.can_edit_maintenance:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('maintenance.reminder_system'))

    settings = MaintenanceReminderSettings.query.all()
    return render_template('maintenance/maintenance_settings.html', settings=settings)

@maintenance_bp.route('/save-reminder-settings', methods=['POST'])
@login_required
def save_reminder_settings():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_maintenance:
        flash('Bu işlemi yapmak için yetkiniz yok!', 'danger')
        return redirect(url_for('maintenance.reminder_system'))

    from models import MaintenanceReminderSettings

    settings_count = int(request.form.get('settings_count', 0))

    for i in range(1, settings_count + 1):
        setting_id = request.form.get(f'setting_id_{i}')
        reminder_type = request.form.get(f'reminder_type_{i}')
        days_interval = int(request.form.get(f'days_interval_{i}', 0))
        hours_interval = int(request.form.get(f'hours_interval_{i}', 0))
        notify_before_days = int(request.form.get(f'notify_before_days_{i}', 0))
        is_active = f'is_active_{i}' in request.form

        if setting_id and reminder_type:
            setting = MaintenanceReminderSettings.query.get(setting_id)
            if setting:
                setting.reminder_type = reminder_type
                setting.days_interval = days_interval
                setting.hours_interval = hours_interval
                setting.notify_before_days = notify_before_days
                setting.is_active = is_active
                setting.updated_at = datetime.now(timezone.utc)

    db.session.commit()
    flash('Hatırlatma ayarları başarıyla güncellendi!', 'success')
    return redirect(url_for('maintenance.maintenance_settings'))

@maintenance_bp.route('/complete-maintenance/<int:reminder_id>', methods=['POST'])
@login_required
def complete_maintenance(reminder_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_maintenance:
        flash('Bu işlemi yapmak için yetkiniz yok!', 'danger')
        return redirect(url_for('maintenance.reminder_system'))

    from models import MaintenanceReminder, Machine

    reminder = MaintenanceReminder.query.get_or_404(reminder_id)
    machine = Machine.query.get(reminder.machine_id)

    if not machine:
        flash('Makine bulunamadı!', 'danger')
        return redirect(url_for('maintenance.reminder_system'))

    # Bakım detayları modalındaki verileri al
    description = request.form.get('description', f"{reminder.reminder_type} tamamlandı")
    notes = request.form.get('notes', '')

    # Bakımı tamamlandı olarak işaretle
    reminder.is_completed = True
    reminder.completed_at = datetime.now(timezone.utc)
    reminder.completed_by = current_user.id

    # Detaylı bakım kaydı oluştur
    maintenance_record = MachineMaintenanceRecord(
        machine_id=reminder.machine_id,
        action_type=reminder.reminder_type,
        action_date=datetime.now(timezone.utc),
        description=f"{description}\n\nMüşteri: {machine.owner_name}\n\nNotlar: {notes}"
    )

    # İsteğe bağlı dosya eklemeleri
    invoice_file = request.files.get('invoice_file')
    part_image = request.files.get('part_image')

    if invoice_file and allowed_file(invoice_file.filename):
        filename = secure_filename(invoice_file.filename)
        invoice_dir = os.path.join(UPLOAD_FOLDER, 'invoices')
        os.makedirs(invoice_dir, exist_ok=True)
        invoice_path = os.path.join(invoice_dir, f"{reminder.machine_id}_{filename}")
        invoice_file.save(invoice_path)
        maintenance_record.invoice_file = f"uploads/maintenance/invoices/{reminder.machine_id}_{filename}"

    if part_image and allowed_file(part_image.filename):
        filename = secure_filename(part_image.filename)
        image_dir = os.path.join(UPLOAD_FOLDER, 'images')
        os.makedirs(image_dir, exist_ok=True)
        image_path = os.path.join(image_dir, f"{reminder.machine_id}_{filename}")
        part_image.save(image_path)
        maintenance_record.part_image = f"uploads/maintenance/images/{reminder.machine_id}_{filename}"

    db.session.add(maintenance_record)
    db.session.commit()

    flash(f'"{machine.model}" için {reminder.reminder_type} bakımı başarıyla tamamlandı ve kayıt oluşturuldu!', 'success')

    # Müşteri bilgilerini göstermek için bakım kayıtlarına yönlendir
    return redirect(url_for('machines.machine_maintenance', machine_id=reminder.machine_id))

@maintenance_bp.route('/add-reminder-type', methods=['POST'])
@login_required
def add_reminder_type():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_maintenance:
        flash('Bu işlemi yapmak için yetkiniz yok!', 'danger')
        return redirect(url_for('maintenance.reminder_system'))

    from models import MaintenanceReminderSettings

    new_reminder_type = request.form.get('new_reminder_type')
    new_days_interval = int(request.form.get('new_days_interval', 0))
    new_hours_interval = int(request.form.get('new_hours_interval', 0))

    if new_reminder_type and (new_days_interval > 0 or new_hours_interval > 0):
        # Aynı isimde başka bir hatırlatıcı var mı kontrol et
        existing = MaintenanceReminderSettings.query.filter_by(reminder_type=new_reminder_type).first()
        if existing:
            flash(f'"{new_reminder_type}" isimli bir hatırlatıcı zaten mevcut!', 'warning')
        else:
            new_setting = MaintenanceReminderSettings(
                reminder_type=new_reminder_type,
                days_interval=new_days_interval,
                hours_interval=new_hours_interval,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.session.add(new_setting)
            db.session.commit()
            flash('Yeni hatırlatma türü başarıyla eklendi!', 'success')
    else:
        flash('Geçerli bir hatırlatma türü ve gün/saat aralığı girmelisiniz!', 'danger')

    return redirect(url_for('maintenance.reminder_system'))

@maintenance_bp.route('/create-custom-reminder', methods=['POST'])
@login_required
def create_custom_reminder():
    if not hasattr(current_user, 'permissions') or not (current_user.permissions.can_edit_maintenance and current_user.permissions.can_view_maintenance_reminders):
        flash('Bu işlemi yapmak için yeterli yetkiniz yok!', 'danger')
        return redirect(url_for('maintenance.reminder_system'))

    machine_id = request.form.get('machine_id')
    machine = Machine.query.get_or_404(machine_id)

    # Makine tipine göre ilk bakım saatini belirle
    first_maintenance = MaintenanceReminderSettings.get_first_maintenance_hours(machine.model)
    next_reminder_hours = first_maintenance

    # Mevcut çalışma saatine göre bir sonraki bakım saatini belirle
    if machine.usage_hours >= first_maintenance:
        intervals = MaintenanceReminderSettings.get_standard_intervals()
        for interval in sorted(intervals):
            if machine.usage_hours < interval:
                next_reminder_hours = interval
                break
        else:
            next_reminder_hours = intervals[-1]  # En son aralığı kullan

    reminder = MaintenanceReminder(
        machine_id=machine_id,
        reminder_type=f"{next_reminder_hours} Saatlik Bakım",
        reminder_date=datetime.now(timezone.utc) + timedelta(days=30),  # Varsayılan 30 gün
        is_completed=False,
        created_at=datetime.now(timezone.utc)
    )

    db.session.add(reminder)
    db.session.commit()

    flash(f'"{machine.model}" için {next_reminder_hours} saatlik bakım hatırlatıcısı oluşturuldu!', 'success')
    return redirect(url_for('maintenance.reminder_system'))

    machine = Machine.query.get_or_404(machine_id)
    reminder_date = datetime.now(timezone.utc) + timedelta(days=days_interval)

    # Yeni hatırlatıcı oluştur
    new_reminder = MaintenanceReminder(
        machine_id=machine_id,
        reminder_type=reminder_type,
        reminder_date=reminder_date,
        is_completed=False,
        created_at=datetime.now(timezone.utc)
    )

    db.session.add(new_reminder)
    db.session.commit()

    flash(f'"{machine.model}" için {days_interval} gün sonra "{reminder_type}" hatırlatıcısı başarıyla oluşturuldu!', 'success')
    return redirect(url_for('maintenance.reminder_system'))

def create_maintenance_reminders(machine_id):
    machine = Machine.query.get(machine_id)
    if not machine:
        return False

    settings = MaintenanceReminderSettings.query.all()
    now = datetime.now(timezone.utc)

    # Bakım saatlerine göre hatırlatma günlerini belirle
    reminder_days = {
        50: 10,    # 50 saatlik bakım için 10 gün
        250: 45,   # 250 saatlik bakım için 45 gün
        500: 90,   # 500 saatlik bakım için 90 gün
        750: 135,  # 750 saatlik bakım için 135 gün
        1000: 200  # 1000 saatlik bakım için 200 gün
    }

    for setting in settings:
        if setting.hours_interval in reminder_days:
            days = reminder_days[setting.hours_interval]
            reminder = MaintenanceReminder(
                machine_id=machine_id,
                reminder_type=f"{setting.hours_interval} Saatlik Bakım",
                reminder_date=now + timedelta(days=days),
                is_completed=False,
                created_at=now
            )
            db.session.add(reminder)

    db.session.commit()
    return True

@maintenance_bp.route('/test-reminder/<int:machine_id>')
@login_required
def test_reminder(machine_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_maintenance:
        flash('Bu işlemi yapmak için yetkiniz yok!', 'danger')
        return redirect(url_for('maintenance.reminder_system'))

    from models import MaintenanceReminder, Machine

    # Makine bilgisini al
    machine = Machine.query.get_or_404(machine_id)

    # Test hatırlatıcısı oluştur
    test_reminder = MaintenanceReminder(
        machine_id=machine.id,
        reminder_type="Test Hatırlatıcısı",
        reminder_date=datetime.now(timezone.utc),
        is_completed=False,
        created_at=datetime.now(timezone.utc)
    )

    db.session.add(test_reminder)
    db.session.commit()

    flash(f'"{machine.model}" için test hatırlatıcısı oluşturuldu!', 'success')
    return redirect(url_for('maintenance.reminder_system'))

@maintenance_bp.route('/view-machine/<int:machine_id>')
@login_required
def view_machine(machine_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_machines:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))

    # Doğrudan makine bakım sayfasına yönlendir
    return redirect(url_for('machines.machine_maintenance', machine_id=machine_id))

@maintenance_bp.route('/download_qr/<int:item_id>')
@login_required
def download_qr(item_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_maintenance:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    item = CatalogItem.query.get_or_404(item_id)
    if not item.qr_code_url:
        flash('Bu makine için QR kod bulunamadı.', 'danger')
        return redirect(url_for('catalogs.catalog_detail', catalog_slug=item.catalog.slug))
    qr_path = item.qr_code_url.split('qr_codes/')[1]
    return send_from_directory(directory=os.path.join('static', 'qr_codes'), path=qr_path, as_attachment=True)
@maintenance_bp.route('/update_machine_hours/<int:machine_id>', methods=['POST'])
@login_required
def update_machine_hours(machine_id):
    if not current_user.permissions.can_edit_maintenance:
        flash('Bu işlemi yapmak için yetkiniz yok!', 'danger')
        return redirect(url_for('maintenance.reminder_system'))

    machine = Machine.query.get_or_404(machine_id)
    new_hours = request.form.get('usage_hours', type=int)

    if new_hours < machine.usage_hours:
        flash('Yeni saat değeri mevcut değerden küçük olamaz!', 'danger')
        return redirect(url_for('maintenance.reminder_system'))

    machine.usage_hours = new_hours

    # Check if maintenance is needed
    if machine.usage_hours >= machine.next_maintenance_hours:
        machine.maintenance_status = 'BAKIM GEREKLİ'
        reminder = MaintenanceReminder(
            machine_id=machine.id,
            reminder_type=f"{machine.next_maintenance_hours} Saatlik Bakım",
            reminder_date=datetime.now(timezone.utc),
            is_completed=False
        )
        db.session.add(reminder)

    db.session.commit()
    flash(f'Makine çalışma saati güncellendi: {new_hours} saat', 'success')
    return redirect(url_for('maintenance.reminder_system'))

def save_file(file, folder):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], folder, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)
        return os.path.join(folder, filename)
    return None

@maintenance_bp.route('/equipment/<int:equipment_id>', methods=['GET', 'POST'])
@login_required
def equipment_maintenance(equipment_id):
    if not current_user.permissions.can_edit_maintenance:
        flash('Bu işlem için yetkiniz bulunmamaktadır.', 'danger')
        return redirect(url_for('auth.dashboard'))

    equipment = Equipment.query.get_or_404(equipment_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_maintenance':
            description = request.form.get('description')
            maintenance_date = datetime.strptime(request.form.get('maintenance_date'), '%Y-%m-%d')
            next_maintenance_date = datetime.strptime(request.form.get('next_maintenance_date'), '%Y-%m-%d') if request.form.get('next_maintenance_date') else None
            
            # Dosya yüklemeleri
            photos = request.files.getlist('maintenance_photos')
            photo_paths = []
            for photo in photos:
                photo_path = save_file(photo, 'maintenance_photos')
                if photo_path:
                    photo_paths.append(photo_path)
            
            document = request.files.get('maintenance_document')
            document_path = save_file(document, 'maintenance_documents') if document else None
            
            try:
                equipment.add_maintenance_record(
                    maintenance_date=maintenance_date,
                    description=description,
                    user_id=current_user.id
                )
                
                if next_maintenance_date:
                    equipment.next_maintenance_date = next_maintenance_date
                
                if photo_paths:
                    if not equipment.maintenance_history[-1].get('photos'):
                        equipment.maintenance_history[-1]['photos'] = []
                    equipment.maintenance_history[-1]['photos'].extend(photo_paths)
                
                if document_path:
                    equipment.maintenance_history[-1]['document'] = document_path
                
                db.session.commit()
                flash('Bakım kaydı başarıyla eklendi.', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Bakım kaydı eklenirken bir hata oluştu: {str(e)}', 'danger')
        
        elif action == 'update_status':
            new_status = request.form.get('status')
            notes = request.form.get('notes')
            
            try:
                equipment.update_status(new_status, current_user.id, notes)
                db.session.commit()
                flash('Ekipman durumu güncellendi.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Durum güncellenirken bir hata oluştu: {str(e)}', 'danger')
        
        return redirect(url_for('maintenance.equipment_maintenance', equipment_id=equipment_id))

    return render_template(
        'maintenance/equipment_maintenance.html',
        equipment=equipment,
        status_types=equipment.EQUIPMENT_STATUS,
        today=datetime.now().strftime('%Y-%m-%d')
    )

@maintenance_bp.route('/equipment/<int:equipment_id>/history')
@login_required
def maintenance_history(equipment_id):
    equipment = Equipment.query.get_or_404(equipment_id)
    return render_template(
        'maintenance/maintenance_history.html',
        equipment=equipment
    )