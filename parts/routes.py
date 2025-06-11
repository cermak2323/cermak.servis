from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from models import Part
from database import db
from utils import exchange_rates
import pandas as pd
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timezone

parts_bp = Blueprint('parts', __name__)

@parts_bp.route('/parts', methods=['GET', 'POST'])
@login_required
def parts_view():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_parts:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    
    search = request.args.get('search', '')
    parts = []
    alternate_parts = []
    
    if search:
        # Ana parçaları ara
        parts = Part.query.filter(
            (Part.part_code.ilike(f'%{search}%')) |
            (Part.name.ilike(f'%{search}%'))
        ).all()
        # Muadil parçaları bul
        alternate_codes = [part.part_code for part in parts if part.part_code]
        alternate_parts = Part.query.filter(
            Part.alternate_part_code.in_(alternate_codes)
        ).all()
    
    return render_template('parts.html',
                         parts=parts,
                         alternate_parts=alternate_parts,
                         search=search,
                         exchange_rate=exchange_rates.get('EUR', 35.0))

@parts_bp.route('/parts/<int:part_id>')
@login_required
def part_detail(part_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_parts:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    
    part = Part.query.get_or_404(part_id)
    return render_template('part_detail.html',
                         part=part,
                         exchange_rate=exchange_rates.get('EUR', 35.0))

@parts_bp.route('/parts/upload_excel', methods=['POST'])
@login_required
def upload_excel():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_parts:
        flash('Bu işlem için yetkiniz yok!', 'danger')
        return redirect(url_for('parts.parts_view'))
    
    if 'excel_file' not in request.files:
        flash('Dosya seçilmedi!', 'danger')
        return redirect(url_for('parts.parts_view'))
    
    file = request.files['excel_file']
    if file.filename == '':
        flash('Dosya seçilmedi!', 'danger')
        return redirect(url_for('parts.parts_view'))
    
    if file and file.filename.endswith(('.xlsx', '.xls')):
        try:
            df = pd.read_excel(file)
            required_columns = ['Parça Kodu', 'Parça Adı', 'Değişen Parça Kodu', 'Geliş Fiyatı (EUR)']
            if not all(col in df.columns for col in required_columns):
                flash('Excel dosyasında gerekli sütunlar eksik! Gerekli sütunlar: Parça Kodu, Parça Adı, Değişen Parça Kodu, Geliş Fiyatı (EUR)', 'danger')
                return redirect(url_for('parts.parts_view'))
            
            for _, row in df.iterrows():
                part_code = str(row['Parça Kodu']).strip()
                existing_part = Part.query.filter_by(part_code=part_code).first()
                alternate_code = str(row['Değişen Parça Kodu']).strip() if pd.notna(row['Değişen Parça Kodu']) else None
                
                if existing_part:
                    existing_part.name = str(row['Parça Adı']).strip()
                    existing_part.alternate_part_code = alternate_code
                    existing_part.price_eur = float(row['Geliş Fiyatı (EUR)'])
                else:
                    new_part = Part(
                        part_code=part_code,
                        name=str(row['Parça Adı']).strip(),
                        alternate_part_code=alternate_code,
                        price_eur=float(row['Geliş Fiyatı (EUR)'])
                    )
                    db.session.add(new_part)
            db.session.commit()
            flash('Excel dosyası başarıyla yüklendi!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Dosya yüklenirken hata oluştu: {str(e)}', 'danger')
    else:
        flash('Sadece .xlsx veya .xls dosyaları kabul edilir!', 'danger')
    
    return redirect(url_for('parts.parts_view'))

@parts_bp.route('/parts/export_excel')
@login_required
def export_excel():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_parts:
        flash('Bu işlem için yetkiniz yok!', 'danger')
        return redirect(url_for('parts.parts_view'))
    
    parts = Part.query.all()
    data = []
    for part in parts:
        part_data = {
            'Parça Kodu': part.part_code,
            'Parça Adı': part.name,
            'Değişen Parça Kodu': part.alternate_part_code or '',
            'Geliş Fiyatı (EUR)': part.price_eur
        }
        data.append(part_data)
    
    df = pd.DataFrame(data)
    export_path = os.path.join('static', 'exports', 'parts_export.xlsx')
    os.makedirs(os.path.dirname(export_path), exist_ok=True)
    df.to_excel(export_path, index=False)
    return send_file(export_path, as_attachment=True)

@parts_bp.route('/parts/upload_part_image/<int:part_id>', methods=['POST'])
@login_required
def upload_part_image(part_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_parts:
        flash('Bu işlem için yetkiniz yok!', 'danger')
        return redirect(url_for('parts.part_detail', part_id=part_id))
    
    part = Part.query.get_or_404(part_id)
    if 'image' not in request.files:
        flash('Resim seçilmedi!', 'danger')
        return redirect(url_for('parts.part_detail', part_id=part_id))
    
    file = request.files['image']
    if file.filename == '':
        flash('Resim seçilmedi!', 'danger')
        return redirect(url_for('parts.part_detail', part_id=part_id))
    
    if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        try:
            filename = secure_filename(f"{part.part_code}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.{file.filename.rsplit('.', 1)[1]}")
            upload_path = os.path.join('static', 'uploads', filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)
            part.image_url = os.path.join('uploads', filename).replace('\\', '/')
            db.session.commit()
            flash('Resim başarıyla yüklendi!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Resim yüklenirken hata oluştu: {str(e)}', 'danger')
    else:
        flash('Sadece .png, .jpg veya .jpeg dosyaları kabul edilir!', 'danger')
    
    return redirect(url_for('parts.part_detail', part_id=part_id))

@parts_bp.route('/parts/update_part_description/<int:part_id>', methods=['POST'])
@login_required
def update_part_description(part_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_edit_parts:
        flash('Bu işlem için yetkiniz yok!', 'danger')
        return redirect(url_for('parts.part_detail', part_id=part_id))
    
    part = Part.query.get_or_404(part_id)
    description = request.form.get('description')
    if description:
        part.description = description
        db.session.commit()
        flash('Açıklama başarıyla güncellendi!', 'success')
    else:
        flash('Açıklama boş olamaz!', 'danger')
    
    return redirect(url_for('parts.part_detail', part_id=part_id))

@parts_bp.route('/parts/search', methods=['GET'])
@login_required
def search_parts():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_parts:
        return {"error": "Yetkiniz yok."}, 403
    
    search = request.args.get('q', '')
    results = []
    if search:
        parts = Part.query.filter(
            (Part.part_code.ilike(f'%{search}%')) |
            (Part.name.ilike(f'%{search}%'))
        ).all()
        for part in parts:
            # Hesaplanan TL fiyatı
            price_try = round((part.price_eur or 0) * exchange_rates.get('EUR', 35.0) * 3, 2)
            results.append({
                'id': part.id,
                'part_code': part.part_code,
                'name': part.name,
                'price_eur': part.price_eur,
                'price_try': price_try
            })
    return {"results": results}