from flask import Blueprint, render_template, request, flash, redirect, url_for
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
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash(f'Hoş geldiniz, {username}!', 'success')  # Kişiselleştirilmiş mesaj
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
    return render_template('dashboard.html')

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
        permission = Permission(
            user_id=user.id,
            can_view_parts=True,
            can_view_faults=True,
            can_view_contact=True
        )
        db.session.add(permission)
        db.session.commit()
    if request.method == 'POST':
        user.username = request.form.get('username')
        password = request.form.get('password')
        if password:
            user.password = generate_password_hash(password, method='pbkdf2:sha256')
        user.role = request.form.get('role')
        permission.can_view_parts = 'can_view_parts' in request.form
        permission.can_edit_parts = 'can_edit_parts' in request.form
        permission.can_view_faults = 'can_view_faults' in request.form
        permission.can_add_solutions = 'can_add_solutions' in request.form
        permission.can_view_catalogs = 'can_view_catalogs' in request.form
        permission.can_view_maintenance = 'can_view_maintenance' in request.form
        permission.can_edit_maintenance = 'can_edit_maintenance' in request.form
        permission.can_view_contact = 'can_view_contact' in request.form
        permission.can_view_purchase_prices = 'can_view_purchase_prices' in request.form
        permission.can_view_offers = 'can_view_offers' in request.form
        permission.can_view_admin_panel = 'can_view_admin_panel' in request.form
        permission.can_create_offers = 'can_create_offers' in request.form
        permission.can_upload_excel = 'can_upload_excel' in request.form
        db.session.commit()
        flash('Kullanıcı bilgileri ve yetkiler güncellendi.', 'success')
        return redirect(url_for('auth.admin_panel'))
    return render_template('edit_user.html', user=user, permission=permission)

@auth.route('/create_user', methods=['GET', 'POST'])
@login_required
def create_user():
    if current_user.role != 'admin':
        flash('Bu işlemi yapma yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    
    form = CreateUserForm()
    if form.validate_on_submit():
        # Yeni kullanıcı oluştur
        user = User(
            username=form.username.data,
            password=generate_password_hash(form.password.data, method='pbkdf2:sha256'),
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