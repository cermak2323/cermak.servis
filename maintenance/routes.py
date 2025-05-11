from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import login_required, current_user
from database import db
from models import CatalogItem, MaintenanceRecord
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timezone

maintenance_bp = Blueprint('maintenance', __name__)

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
    return render_template('edit_maintenance_record.html', item=item, record=record)

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