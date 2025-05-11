from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

contact_bp = Blueprint('contact', __name__)

@contact_bp.route('/', methods=['GET', 'POST'])
@login_required
def contact_view():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_contact:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        flash('Mesajınız başarıyla gönderildi!', 'success')
        return redirect(url_for('contact.contact_view'))
    return render_template('contact.html')