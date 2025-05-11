
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Invoice, InvoiceApproval, User
from datetime import datetime, timezone
import os

accounting_bp = Blueprint('accounting', __name__)

@accounting_bp.route('/')
@login_required
def accounting_view():
    if not current_user.permissions.can_view_accounting:
        flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('auth.dashboard'))
    
    invoices = Invoice.query.all()
    return render_template('accounting/invoice_list.html', invoices=invoices)

@accounting_bp.route('/invoice/add', methods=['GET', 'POST'])
@login_required
def add_invoice():
    if not current_user.permissions.can_edit_accounting:
        flash('Bu işlem için yetkiniz yok.', 'danger')
        return redirect(url_for('accounting.accounting_view'))
        
    if request.method == 'POST':
        invoice_number = request.form.get('invoice_number')
        description = request.form.get('description')
        amount = float(request.form.get('amount'))
        machine_id = request.form.get('machine_id')
        service_id = request.form.get('service_id')
        approver_ids = request.form.getlist('approvers')
        issue_date = datetime.strptime(request.form.get('issue_date'), '%Y-%m-%d')
        
        invoice_file = request.files.get('invoice_file')
        
        invoice = Invoice(
            invoice_number=invoice_number,
            description=description,
            amount_eur=amount,
            created_by=current_user.id,
            issue_date=datetime.now(timezone.utc)
        )
        
        if invoice_file:
            filename = secure_filename(invoice_file.filename)
            invoice_path = os.path.join('static/uploads/invoices', filename)
            os.makedirs(os.path.dirname(invoice_path), exist_ok=True)
            invoice_file.save(invoice_path)
            invoice.document_url = invoice_path
            
        
            
        db.session.add(invoice)
        db.session.flush()
        
        for user_id in approver_ids:
            approval = InvoiceApproval(invoice_id=invoice.id, user_id=int(user_id))
            db.session.add(approval)
            
        db.session.commit()
        flash('Fatura başarıyla eklendi.', 'success')
        return redirect(url_for('accounting.accounting_view'))
        
    users = User.query.all()
    return render_template('accounting/add_invoice.html', users=users)

@accounting_bp.route('/invoice/<int:invoice_id>/approve', methods=['POST'])
@login_required
def approve_invoice(invoice_id):
    approval = InvoiceApproval.query.filter_by(
        invoice_id=invoice_id,
        user_id=current_user.id
    ).first_or_404()
    
    approval.approved = True
    approval.approved_at = datetime.now(timezone.utc)
    approval.comment = request.form.get('comment')
    
    invoice = Invoice.query.get_or_404(invoice_id)
    all_approved = all(a.approved for a in invoice.approvers)
    
    if all_approved:
        invoice.status = 'Onaylandı'
        
    db.session.commit()
    flash('Fatura onayınız kaydedildi.', 'success')
    return redirect(url_for('accounting.accounting_view'))