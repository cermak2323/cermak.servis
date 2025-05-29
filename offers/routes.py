from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

offers = Blueprint('offers', __name__)

@offers.route('/dashboard')
@login_required
def offers_dashboard():
    if not current_user.permissions.can_view_periodic_maintenance or not current_user.permissions.can_create_offers:
        flash('Bu modüle erişim veya teklif oluşturma yetkiniz yok!', 'danger')
        return redirect(url_for('auth.dashboard'))
    return render_template('offers_dashboard.html')

@offers.route('/spare_parts')
@login_required
def spare_parts_offers():
    if not current_user.permissions.can_view_periodic_maintenance or not current_user.permissions.can_create_offers:
        flash('Bu modüle erişim veya teklif oluşturma yetkiniz yok!', 'danger')
        return redirect(url_for('auth.dashboard'))
    return render_template('spare_parts_offers.html')