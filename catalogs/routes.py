from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Catalog, CatalogItem, Part
from database import db
import os
from werkzeug.utils import secure_filename
from parts.routes import exchange_rates

catalogs_bp = Blueprint('catalogs', __name__)

# Dosya yükleme için ayarlar
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@catalogs_bp.route('/')
@login_required
def catalogs_view():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_catalogs:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    catalogs = Catalog.query.all()
    return render_template('catalogs.html', catalogs=catalogs)

@catalogs_bp.route('/catalog/<string:catalog_slug>')
@login_required
def catalog_detail(catalog_slug):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_catalogs:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    catalog = Catalog.query.filter_by(slug=catalog_slug).first_or_404()
    items = CatalogItem.query.filter_by(catalog_id=catalog.id).all()
    return render_template('catalog_detail.html', catalog=catalog, items=items)

@catalogs_bp.route('/catalog-item/<int:item_id>/parts')
@login_required
def catalog_item_parts(item_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_parts:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    item = CatalogItem.query.get_or_404(item_id)
    parts = Part.query.filter_by(catalog_item_id=item.id).all()
    eur_rate = exchange_rates['EUR']
    parts_with_prices = [{
        'id': p.id,
        'part_code': p.part_code,
        'name': p.name,
        'price_try': p.price_eur * eur_rate,
        'selling_price_try': p.price_eur * eur_rate * 3,
        'image_url': p.image_url
    } for p in parts]
    return render_template('catalog_item_parts.html', item=item, parts=parts_with_prices)

@catalogs_bp.route('/admin/add_catalog_item', methods=['GET', 'POST'])
@login_required
def add_catalog_item():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_catalogs:
        flash('Bu işlemi yapma yetkiniz yok.', 'danger')
        return redirect(url_for('catalogs.catalogs_view'))
    if request.method == 'POST':
        catalog_id = request.form.get('catalog_id')
        name = request.form.get('name')
        if not catalog_id or not name:
            flash('Katalog ve isim zorunludur.', 'danger')
            return redirect(url_for('catalogs.add_catalog_item'))
        motor_pdf = request.files.get('motor_pdf')
        yedek_parca_pdf = request.files.get('yedek_parca_pdf')
        operator_pdf = request.files.get('operator_pdf')
        service_pdf = request.files.get('service_pdf')
        motor_pdf_url = yedek_parca_pdf_url = operator_pdf_url = service_pdf_url = None
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        for pdf_file, pdf_type in [
            (motor_pdf, 'motor_pdf'),
            (yedek_parca_pdf, 'yedek_parca_pdf'),
            (operator_pdf, 'operator_pdf'),
            (service_pdf, 'service_pdf')
        ]:
            if pdf_file and pdf_file.filename:
                if not allowed_file(pdf_file.filename):
                    flash(f'{pdf_type} için sadece PDF dosyaları kabul edilir.', 'danger')
                    return redirect(url_for('catalogs.add_catalog_item'))
                filename = secure_filename(f"{pdf_type}_{catalog_id}_{name}_{pdf_file.filename}")
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                pdf_file.save(file_path)
                if pdf_type == 'motor_pdf':
                    motor_pdf_url = f"uploads/{filename}"
                elif pdf_type == 'yedek_parca_pdf':
                    yedek_parca_pdf_url = f"uploads/{filename}"
                elif pdf_type == 'operator_pdf':
                    operator_pdf_url = f"uploads/{filename}"
                elif pdf_type == 'service_pdf':
                    service_pdf_url = f"uploads/{filename}"
        new_item = CatalogItem(
            catalog_id=int(catalog_id),
            name=name.strip(),
            motor_pdf_url=motor_pdf_url,
            yedek_parca_pdf_url=yedek_parca_pdf_url,
            operator_pdf_url=operator_pdf_url,
            service_pdf_url=service_pdf_url
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Katalog öğesi başarıyla eklendi!', 'success')
        return redirect(url_for('catalogs.catalog_detail', catalog_slug=Catalog.query.get(catalog_id).slug))
    catalogs = Catalog.query.all()
    return render_template('add_catalog_item.html', catalogs=catalogs)