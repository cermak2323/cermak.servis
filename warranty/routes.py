from flask import Blueprint, render_template
from flask_login import login_required

warranty_bp = Blueprint('warranty', __name__)

@warranty_bp.route('/')
@login_required
def warranty_view():
    return render_template('warranty/not_active.html')