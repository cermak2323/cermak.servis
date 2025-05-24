from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import FaultSolution, Part, FaultReport
from database import db
from datetime import datetime
import os
from werkzeug.utils import secure_filename

faults_bp = Blueprint('faults', __name__)

@faults_bp.route('/management')
@login_required
def fault_management():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_faults:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    return render_template('fault_management.html')

@faults_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_fault_report():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_faults:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        city = request.form.get('city')
        phone = request.form.get('phone')
        machine_model = request.form.get('machine_model')
        serial_number = request.form.get('serial_number')
        fault_type = request.form.get('fault_type')
        description = request.form.get('description')
        media_file = request.files.get('media_file')
        if not all([first_name, last_name, city, phone, machine_model, serial_number, fault_type, description]):
            flash('Tüm zorunlu alanları doldurun!', 'danger')
            return redirect(url_for('faults.new_fault_report'))
        media_path = None
        if media_file and media_file.filename:
            allowed_extensions = {'png', 'jpg', 'jpeg', 'mp4', 'mov'}
            if '.' in media_file.filename and media_file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                filename = secure_filename(f"fault_{datetime.now().strftime('%Y%m%d%H%M%S')}_{media_file.filename}")
                upload_path = os.path.join('static', 'uploads', filename)
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                media_file.save(upload_path)
                media_path = os.path.join('Uploads', filename).replace('\\', '/')
            else:
                flash('Sadece .png, .jpg, .jpeg, .mp4 veya .mov dosyaları kabul edilir!', 'danger')
                return redirect(url_for('faults.new_fault_report'))
        fault_report = FaultReport(
            first_name=first_name,
            last_name=last_name,
            city=city,
            phone=phone,
            machine_model=machine_model,
            serial_number=serial_number,
            fault_type=fault_type,
            description=description,
            media_file=media_path,
            reported_by=current_user.id,
            reported_date=datetime.now(),
            status='pending'
        )
        db.session.add(fault_report)
        db.session.commit()
        flash('Arıza kaydı başarıyla oluşturuldu!', 'success')
        return redirect(url_for('auth.dashboard'))
    return render_template('new_fault_report.html', machine_models=MACHINE_MODELS, fault_types=FAULT_TYPES)

MACHINE_MODELS = ['TB215R', 'TB216', 'TB250', 'TB260']  # Gerçek modellerini ekle
FAULT_TYPES = ['Mekanik', 'Hidrolik', 'Elektrik']  # Gerçek tiplerini ekle

@faults_bp.route('/delete_solution/<int:solution_id>', methods=['POST'])
@login_required
def delete_solution(solution_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_add_solutions:
        flash('Çözüm silme yetkiniz yok.', 'danger')
        return redirect(url_for('faults.fault_search'))
    
    solution = FaultSolution.query.get_or_404(solution_id)
    if solution.media_file and os.path.exists(os.path.join('static', solution.media_file)):
        os.remove(os.path.join('static', solution.media_file))
    
    db.session.delete(solution)
    db.session.commit()
    flash('Çözüm başarıyla silindi!', 'success')
    return redirect(url_for('faults.fault_search'))

@faults_bp.route('/add_general_solution', methods=['GET', 'POST'])
@login_required
def add_general_solution():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_add_solutions:
        flash('Çözüm ekleme yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
        
    machine_models = ['TB210R', 'TB016', 'TB215R', 'TB216', 'TB217R', 'TB225', 'TB325', 'TB235', 'TB235-2', 'TB138FR', 'TB240', 'TB240-2', 'TB250', 'TB153FR', 'TB260', 'TB260-2', 'TB285', 'TB290-2']
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        part_codes = request.form.get('part_codes')
        media_file = request.files.get('media_file')
        machine_model = request.form.get('machine_model')
        fault_type = request.form.get('fault_type')
        if not title or not description or not machine_model or not fault_type:
            flash('Başlık, açıklama, makine modeli ve arıza tipi zorunludur.', 'danger')
            return redirect(url_for('faults.add_general_solution'))
        media_path = None
        if media_file and media_file.filename:
            allowed_extensions = {'png', 'jpg', 'jpeg', 'mp4', 'mov'}
            if '.' in media_file.filename and media_file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                filename = secure_filename(f"solution_{datetime.now().strftime('%Y%m%d%H%M%S')}_{media_file.filename}")
                upload_path = os.path.join('static', 'Uploads', filename)
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                media_file.save(upload_path)
                media_path = os.path.join('Uploads', filename).replace('\\', '/')
            else:
                flash('Sadece .png, .jpg, .jpeg, .mp4 veya .mov dosyaları kabul edilir.', 'danger')
                return redirect(url_for('faults.add_general_solution'))
        if part_codes:
            codes = [code.strip() for code in part_codes.split(',')]
            invalid_codes = [code for code in codes if not Part.query.filter_by(part_code=code).first()]
            if invalid_codes:
                flash(f'Geçersiz parça kodları: {", ".join(invalid_codes)}', 'danger')
                return redirect(url_for('faults.add_general_solution'))
        solution = FaultSolution(
            title=title.strip(),
            description=description.strip(),
            part_codes=part_codes.strip() if part_codes else None,
            media_file=media_path,
            machine_model=machine_model.strip(),
            fault_type=fault_type.strip(),
            created_by=current_user.id,
            created_date=datetime.now()
        )
        db.session.add(solution)
        db.session.commit()
        flash('Genel çözüm başarıyla eklendi!', 'success')
        return redirect(url_for('faults.add_general_solution'))
    return render_template('add_general_solution.html', machine_models=machine_models, fault_types=FAULT_TYPES)

@faults_bp.route('/search', methods=['GET', 'POST'])
@login_required
def fault_search():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_faults:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))

    machine_type = request.form.get('machine_type', '') if request.method == 'POST' else request.args.get('machine_type', '')
    query = request.form.get('query', '') if request.method == 'POST' else request.args.get('query', '')
    solutions = []
    part_map = {}

    if machine_type and query:
        solutions = FaultSolution.query.filter(
            FaultSolution.machine_model == machine_type,
            (FaultSolution.title.ilike(f'%{query}%')) |
            (FaultSolution.description.ilike(f'%{query}%')) |
            (FaultSolution.fault_type.ilike(f'%{query}%')) |
            (FaultSolution.part_codes.ilike(f'%{query}%'))
        ).all()
    elif machine_type:
        flash('Lütfen aranacak arıza/çözüm bilgisini girin.', 'warning')
    elif query:
        flash('Lütfen önce makine tipini seçin.', 'warning')

        # Parça kodları için eşleme oluştur
        for solution in solutions:
            if solution.part_codes:
                for code in solution.part_codes.split(','):
                    code = code.strip()
                    part = Part.query.filter_by(part_code=code).first()
                    if part:
                        part_map[code] = part.id

    return render_template('fault_search.html', query=query, solutions=solutions, part_map=part_map)

@faults_bp.route('/solution/<int:solution_id>')
@login_required
def solution_detail(solution_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_faults:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    solution = FaultSolution.query.get_or_404(solution_id)
    part_map = {}
    if solution.part_codes:
        for code in solution.part_codes.split(','):
            code = code.strip()
            part = Part.query.filter_by(part_code=code).first()
            if part:
                part_map[code] = part.id
    query = request.args.get('query', '')
    return render_template('solution_detail.html', solution=solution, part_map=part_map, query=query)

@faults_bp.route('/edit_solution/<int:solution_id>', methods=['GET', 'POST'])
@login_required
def edit_solution(solution_id):
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_add_solutions:
        flash('Çözüm düzenleme yetkiniz yok.', 'danger')
        return redirect(url_for('faults.fault_search'))
    solution = FaultSolution.query.get_or_404(solution_id)
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        part_codes = request.form.get('part_codes')
        media_file = request.files.get('media_file')
        machine_model = request.form.get('machine_model')
        fault_type = request.form.get('fault_type')
        if not title or not description or not machine_model or not fault_type:
            flash('Başlık, açıklama, makine modeli ve arıza tipi zorunludur.', 'danger')
            return redirect(url_for('faults.edit_solution', solution_id=solution_id))
        media_path = solution.media_file
        if media_file and media_file.filename:
            allowed_extensions = {'png', 'jpg', 'jpeg', 'mp4', 'mov'}
            if '.' in media_file.filename and media_file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                filename = secure_filename(f"solution_{datetime.now().strftime('%Y%m%d%H%M%S')}_{media_file.filename}")
                upload_path = os.path.join('static', 'Uploads', filename)
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                media_file.save(upload_path)
                media_path = os.path.join('Uploads', filename).replace('\\', '/')
                if solution.media_file and os.path.exists(os.path.join('static', solution.media_file)):
                    os.remove(os.path.join('static', solution.media_file))
            else:
                flash('Sadece .png, .jpg, .jpeg, .mp4 veya .mov dosyaları kabul edilir.', 'danger')
                return redirect(url_for('faults.edit_solution', solution_id=solution_id))
        if part_codes:
            codes = [code.strip() for code in part_codes.split(',')]
            invalid_codes = [code for code in codes if not Part.query.filter_by(part_code=code).first()]
            if invalid_codes:
                flash(f'Geçersiz parça kodları: {", ".join(invalid_codes)}', 'danger')
                return redirect(url_for('faults.edit_solution', solution_id=solution_id))
        solution.title = title.strip()
        solution.description = description.strip()
        solution.part_codes = part_codes.strip() if part_codes else None
        solution.media_file = media_path
        solution.machine_model = machine_model.strip()
        solution.fault_type = fault_type.strip()
        db.session.commit()
        flash('Çözüm başarıyla güncellendi!', 'success')
        return redirect(url_for('faults.fault_search'))
    return render_template('edit_solution.html', solution=solution, machine_models=MACHINE_MODELS, fault_types=FAULT_TYPES)