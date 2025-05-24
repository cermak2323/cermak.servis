from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, Permission, Announcement # Announcement model added
from database import db
from forms import CreateUserForm
from datetime import datetime, timezone

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))

    # Aktif duyuruları getir
    announcements = Announcement.query.filter_by(is_active=True).order_by(Announcement.created_at.desc()).all()

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f'Hoş geldiniz, {username}!', 'success')
            return redirect(url_for('auth.dashboard'))
        else:
            flash('Kullanıcı adı veya şifre yanlış.', 'danger')
    return render_template('login.html', announcements=announcements)

@auth.route('/announcements/<int:announcement_id>/delete', methods=['POST'])
@login_required
def delete_announcement(announcement_id):
    if current_user.role != 'admin':
        flash('Bu işlemi yapmak için yetkiniz yok!', 'danger')
        return redirect(url_for('auth.dashboard'))

    announcement = Announcement.query.get_or_404(announcement_id)
    db.session.delete(announcement)
    db.session.commit()
    flash('Duyuru başarıyla silindi.', 'success')
    return redirect(url_for('auth.manage_announcements'))

@auth.route('/announcements', methods=['GET', 'POST'])
@login_required
def manage_announcements():
    if current_user.role != 'admin':
        flash('Bu sayfaya erişim yetkiniz yok!', 'danger')
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        announcement = Announcement(
            title=title,
            content=content,
            created_by=current_user.id
        )
        db.session.add(announcement)
        db.session.commit()
        flash('Duyuru başarıyla oluşturuldu.', 'success')
        return redirect(url_for('auth.manage_announcements'))

    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template('manage_announcements.html', announcements=announcements)

@auth.route('/guest_login')
def guest_login():
    guest = User.query.filter_by(username='guest_musteri').first()
    if guest:
        login_user(guest)
        flash(f'Hoş geldiniz, guest_musteri!', 'success')  # Kişiselleştirilmiş mesaj
        return redirect(url_for('auth.dashboard'))
    else:
        flash('Misafir kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('auth.login'))

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Çıkış yaptınız.', 'success')
    return redirect(url_for('auth.login'))

@auth.route('/dashboard')
@login_required
def dashboard():
    from flask_login import current_user
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html', current_user=current_user)

@auth.route('/admin_panel')
@login_required
def admin_panel():
    if current_user.role != 'admin':
        flash('Bu sayfaya erişim yetkiniz yok!', 'danger')
        return redirect(url_for('auth.dashboard'))
    users = User.query.all()
    return render_template('admin_panel.html', users=users)

@auth.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin':
        flash('Bu işlemi yapma yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    
    user = User.query.get_or_404(user_id)
    permission = Permission.query.filter_by(user_id=user.id).first()
    
    if not permission:
        permission = Permission(user_id=user.id)
        db.session.add(permission)
        db.session.commit()
    
    if request.method == 'POST':
        user.username = request.form.get('username')
        password = request.form.get('password')
        if password:
            user.set_password(password)
        user.role = request.form.get('role')
        
        # Update all permission fields
        for field in permission.__dict__:
            if field.startswith('can_'):
                setattr(permission, field, field in request.form)
        
        db.session.commit()
        flash('Kullanıcı bilgileri ve yetkiler güncellendi.', 'success')
        return redirect(url_for('auth.admin_panel'))
    
    # Permission nesnesini sözlüğe dönüştür
    permission_dict = {}
    for field in permission.__dict__:
        if field.startswith('can_'):
            permission_dict[field] = getattr(permission, field)
    
    permission_groups = {
        'machine': {
            'title': 'Makine Yönetimi',
            'permissions': [
                ('can_view_machines', 'Makineleri Görüntüleme'),
                ('can_add_machines', 'Makine Ekleme'),
                ('can_edit_machines', 'Makine Düzenleme'),
                ('can_delete_machines', 'Makine Silme'),
                ('can_search_machines', 'Makine Arama'),
                ('can_export_machines', 'Makine Dışa Aktarma'),
                ('can_list_machines', 'Makine Listeleme')
            ]
        },
        'maintenance': {
            'title': 'Bakım Yönetimi',
            'permissions': [
                ('can_view_maintenance', 'Bakımları Görüntüleme'),
                ('can_add_maintenance', 'Bakım Ekleme'),
                ('can_edit_maintenance', 'Bakım Düzenleme'),
                ('can_delete_maintenance', 'Bakım Silme'),
                ('can_view_maintenance_history', 'Bakım Geçmişi'),
                ('can_view_maintenance_reminders', 'Bakım Hatırlatmaları'),
                ('can_manage_maintenance_schedules', 'Bakım Programları')
            ]
        },
        'equipment': {
            'title': 'Ekipman Yönetimi',
            'permissions': [
                ('can_view_equipment', 'Ekipmanları Görüntüleme'),
                ('can_add_equipment', 'Ekipman Ekleme'),
                ('can_edit_equipment', 'Ekipman Düzenleme'),
                ('can_delete_equipment', 'Ekipman Silme'),
                ('can_manage_equipment_status', 'Ekipman Durumu')
            ]
        },
        'parts': {
            'title': 'Parça ve Katalog',
            'permissions': [
                ('can_view_parts', 'Parçaları Görüntüleme'),
                ('can_edit_parts', 'Parça Düzenleme'),
                ('can_view_catalogs', 'Katalogları Görüntüleme'),
                ('can_manage_catalogs', 'Katalog Yönetimi'),
                ('can_view_purchase_prices', 'Satın Alma Fiyatları')
            ]
        },
        'offers': {
            'title': 'Teklif Yönetimi',
            'permissions': [
                ('can_view_offers', 'Teklifleri Görüntüleme'),
                ('can_create_offers', 'Teklif Oluşturma'),
                ('can_edit_offers', 'Teklif Düzenleme'),
                ('can_delete_offers', 'Teklif Silme'),
                ('can_approve_offers', 'Teklif Onaylama'),
                ('can_reject_offers', 'Teklif Reddetme'),
                ('can_view_periodic_maintenance', 'Periyodik Bakımları Görüntüleme'),
                ('can_manage_periodic_maintenance', 'Periyodik Bakım Yönetimi')
            ]
        },
        'warranty': {
            'title': 'Garanti ve Muhasebe',
            'permissions': [
                ('can_view_warranty', 'Garanti Görüntüleme'),
                ('can_manage_warranty', 'Garanti Yönetimi'),
                ('can_view_accounting', 'Muhasebe Görüntüleme'),
                ('can_manage_accounting', 'Muhasebe Yönetimi')
            ]
        },
        'system': {
            'title': 'Sistem Yönetimi',
            'permissions': [
                ('can_view_users', 'Kullanıcıları Görüntüleme'),
                ('can_manage_users', 'Kullanıcı Yönetimi'),
                ('can_view_roles', 'Rolleri Görüntüleme'),
                ('can_manage_roles', 'Rol Yönetimi'),
                ('can_view_admin_panel', 'Yönetici Paneli'),
                ('can_manage_system_settings', 'Sistem Ayarları'),
                ('can_view_logs', 'Logları Görüntüleme')
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
        'files': {
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
                ('can_view_contact', 'İletişim Görüntüleme'),
                ('can_send_notifications', 'Bildirim Gönderme'),
                ('can_manage_announcements', 'Duyuru Yönetimi')
            ]
        },
        'faults': {
            'title': 'Arıza Çözüm Sistemi',
            'permissions': [
                ('can_view_faults', 'Arızaları Görüntüleme'),
                ('can_add_faults', 'Arıza Kaydı Oluşturma'),
                ('can_edit_faults', 'Arıza Kaydı Düzenleme'),
                ('can_delete_faults', 'Arıza Kaydı Silme'),
                ('can_assign_faults', 'Arıza Atama'),
                ('can_resolve_faults', 'Arıza Çözme'),
                ('can_add_fault_solutions', 'Çözüm Ekleme'),
                ('can_view_fault_history', 'Arıza Geçmişi'),
                ('can_manage_fault_categories', 'Arıza Kategorileri'),
                ('can_export_fault_reports', 'Arıza Raporları')
            ]
        }
    }
    
    return render_template('auth/edit_user.html', 
                         user=user, 
                         permission=permission_dict, 
                         permission_groups=permission_groups)

@auth.route('/create_user', methods=['GET', 'POST'])
@login_required
def create_user():
    if current_user.role != 'admin' or current_user.username != 'admin1':
        flash('Bu işlemi yapma yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))

    form = CreateUserForm()
    if form.validate_on_submit():
        # Yeni kullanıcı oluştur
        user = User(
            username=form.username.data,
            password=form.password.data,
            role=form.role.data,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(user)
        db.session.commit()

        # Yetkileri oluştur
        permission = Permission(
            user_id=user.id,
            can_view_parts=form.can_view_parts.data,
            can_edit_parts=form.can_edit_parts.data,
            can_view_purchase_prices=form.can_view_purchase_prices.data,
            can_view_catalogs=form.can_view_catalogs.data,
            can_view_maintenance=form.can_view_maintenance.data,
            can_edit_maintenance=form.can_edit_maintenance.data,
            can_view_faults=form.can_view_faults.data,
            can_add_solutions=form.can_add_solutions.data,
            can_view_contact=form.can_view_contact.data
        )
        db.session.add(permission)
        db.session.commit()

        flash(f'Kullanıcı "{form.username.data}" başarıyla oluşturuldu.', 'success')
        return redirect(url_for('auth.admin_panel'))

    return render_template('create_user.html', form=form)

from flask_login import login_required, current_user

@auth.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@auth.route('/delete_user/<int:user_id>', methods=['GET', 'POST', 'DELETE'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('Bu işlemi yapma yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))

    user = User.query.get_or_404(user_id)

    # First delete associated permissions
    Permission.query.filter_by(user_id=user.id).delete()

    # Then delete the user
    db.session.delete(user)
    db.session.commit()

    flash('Kullanıcı başarıyla silindi.', 'success')
    return redirect(url_for('auth.admin_panel'))

@auth.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not current_user.check_password(current_password):
        flash('Mevcut şifre yanlış.', 'danger')
        return redirect(url_for('auth.profile'))

    if new_password != confirm_password:
        flash('Yeni şifreler eşleşmiyor.', 'danger')
        return redirect(url_for('auth.profile'))

    current_user.set_password(new_password)
    db.session.commit()
    flash('Şifreniz başarıyla değiştirildi.', 'success')
    return redirect(url_for('auth.profile'))

@auth.route('/upload_profile_image', methods=['POST'])
@login_required
def upload_profile_image():
    if 'profile_image' not in request.files:
        flash('Resim seçilmedi!', 'danger')
        return redirect(url_for('auth.profile'))

    file = request.files['profile_image']
    if file.filename == '':
        flash('Resim seçilmedi!', 'danger')
        return redirect(url_for('auth.profile'))

    if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        try:
            filename = secure_filename(f"profile_{current_user.id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.{file.filename.rsplit('.', 1)[1]}")
            upload_path = os.path.join('static', 'uploads', 'profiles', filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)

            if current_user.profile:
                current_user.profile.image_url = os.path.join('uploads', 'profiles', filename).replace('\\', '/')
            else:
                profile = Profile(user_id=current_user.id, image_url=os.path.join('uploads', 'profiles', filename).replace('\\', '/'))
                db.session.add(profile)

            db.session.commit()
            flash('Profil resmi başarıyla yüklendi!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Resim yüklenirken hata oluştu: {str(e)}', 'danger')
    else:
        flash('Sadece .png, .jpg veya .jpeg dosyaları kabul edilir!', 'danger')

    return redirect(url_for('auth.profile'))

@auth.route('/manage-permissions')
@login_required
def manage_permissions():
    if not current_user.permissions.can_manage_users:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    
    users = User.query.all()
    for user in users:
        user.role_display = {
            'admin': 'Yönetici',
            'muhendis': 'Mühendis',
            'servis': 'Yetkili Servis',
            'musteri': 'Müşteri'
        }.get(user.role, user.role)
        
        user.role_badge = {
            'admin': 'danger',
            'muhendis': 'info',
            'servis': 'success',
            'musteri': 'warning'
        }.get(user.role, 'secondary')
    
    permission_groups = Permission.get_permission_groups()
    return render_template('auth/manage_permissions.html', 
                         users=users, 
                         permission_groups=permission_groups)

@auth.route('/get_permissions/<int:user_id>')
@login_required
def get_permissions(user_id):
    if not current_user.permissions.can_manage_users:
        return jsonify({'error': 'Yetkiniz yok'}), 403
    
    user = User.query.get_or_404(user_id)
    permissions = {}
    
    for column in Permission.__table__.columns:
        if column.name.startswith('can_'):
            permissions[column.name] = getattr(user.permissions, column.name)
    
    return jsonify({
        'username': user.username,
        'permissions': permissions
    })

@auth.route('/update_permissions', methods=['POST'])
@login_required
def update_permissions():
    if not current_user.permissions.can_manage_users:
        return jsonify({'success': False, 'message': 'Yetkiniz yok'})
    
    user_id = request.form.get('user_id')
    user = User.query.get_or_404(user_id)
    
    try:
        for column in Permission.__table__.columns:
            if column.name.startswith('can_'):
                setattr(user.permissions, column.name, 
                       request.form.get(column.name) == 'on')
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@auth.route('/add_user', methods=['POST'])
@login_required
def add_user():
    if not current_user.permissions.can_manage_users:
        flash('Bu işlem için yetkiniz yok.', 'danger')
        return redirect(url_for('auth.manage_permissions'))
    
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')
    
    if User.query.filter_by(username=username).first():
        flash('Bu kullanıcı adı zaten kullanılıyor.', 'danger')
        return redirect(url_for('auth.manage_permissions'))
    
    try:
        user = User(username=username, email=email, password=password, role=role)
        db.session.add(user)
        db.session.flush()
        
        # Rol bazlı varsayılan yetkileri ata
        default_permissions = {
            'admin': {
                'can_manage_users': True,
                'can_manage_roles': True,
                'can_view_admin_panel': True,
                'can_manage_system_settings': True,
                'can_view_logs': True,
                'can_view_statistics': True,
                'can_manage_announcements': True,
                'can_view_faults': True,
                'can_add_faults': True,
                'can_edit_faults': True,
                'can_delete_faults': True,
                'can_assign_faults': True,
                'can_resolve_faults': True,
                'can_add_fault_solutions': True,
                'can_view_fault_history': True,
                'can_manage_fault_categories': True,
                'can_export_fault_reports': True
            },
            'muhendis': {
                'can_view_machines': True,
                'can_view_maintenance': True,
                'can_view_equipment': True,
                'can_view_parts': True,
                'can_view_catalogs': True,
                'can_view_faults': True,
                'can_add_faults': True,
                'can_edit_faults': True,
                'can_assign_faults': True,
                'can_resolve_faults': True,
                'can_add_fault_solutions': True,
                'can_view_fault_history': True,
                'can_add_solutions': True,
                'can_view_reports': True
            },
            'servis': {
                'can_view_machines': True,
                'can_add_maintenance': True,
                'can_edit_maintenance': True,
                'can_view_equipment': True,
                'can_manage_equipment_status': True,
                'can_upload_files': True,
                'can_download_files': True,
                'can_view_faults': True,
                'can_add_faults': True,
                'can_edit_faults': True,
                'can_resolve_faults': True,
                'can_add_fault_solutions': True,
                'can_view_fault_history': True
            },
            'musteri': {
                'can_view_machines': True,
                'can_view_maintenance': True,
                'can_view_equipment': True,
                'can_download_files': True,
                'can_view_contact': True,
                'can_view_faults': True,
                'can_add_faults': True,
                'can_view_fault_history': True
            }
        }
        
        permissions = Permission(user_id=user.id)
        role_permissions = default_permissions.get(role, {})
        
        for permission, value in role_permissions.items():
            setattr(permissions, permission, value)
        
        db.session.add(permissions)
        db.session.commit()
        
        flash('Kullanıcı başarıyla eklendi.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Kullanıcı eklenirken hata oluştu: {str(e)}', 'danger')
    
    return redirect(url_for('auth.manage_permissions'))