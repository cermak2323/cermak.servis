from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response, current_app
from flask_login import login_required, current_user
from weasyprint import HTML
from datetime import datetime, timedelta
import json
import os
import base64

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

@offers.route('/create_spare_parts_offer', methods=['GET', 'POST'])
@login_required
def create_spare_parts_offer():
    if not current_user.permissions.can_create_offers:
        flash('Teklif oluşturma yetkiniz yok!', 'danger')
        return redirect(url_for('offers.offers_dashboard'))

    if request.method == 'POST':
        try:
            # Get form data
            serial_number = request.form.get('serial_number')
            customer_name = request.form.get('customer_name')
            company_name = request.form.get('company_name')
            phone = request.form.get('phone')
            selected_parts = request.form.get('selected_parts')
            discount_type = request.form.get('discount_type', 'none')
            discount_value = float(request.form.get('discount_value', 0))

            # Process parts
            parts = json.loads(selected_parts) if selected_parts else []

            # --- YENİ: Parça fiyatlarını ve adetlerini validasyondan geçir ---
            for part in parts:
                try:
                    part['price_try'] = float(part.get('price_try', 0)) or 0
                except Exception:
                    part['price_try'] = 0
                try:
                    part['quantity'] = int(part.get('quantity', 1)) or 1
                except Exception:
                    part['quantity'] = 1
            # --- SON ---

            # Generate offer number
            offer_number = f"SPARE-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            # Get logo
            logo_path = os.path.join(current_app.static_folder, 'img', 'logo.png')
            logo_base64 = ''
            try:
                with open(logo_path, 'rb') as f:
                    logo_base64 = base64.b64encode(f.read()).decode()
            except Exception as e:
                current_app.logger.warning(f"Logo dosyası okunamadı: {str(e)}")

            # Calculate totals
            subtotal_try = sum(float(part.get('price_try', 0)) * int(part.get('quantity', 1)) for part in parts)

            # Calculate discount
            discount_amount = 0
            if discount_type == 'percentage':
                discount_amount = subtotal_try * (discount_value / 100)
            elif discount_type == 'amount':
                discount_amount = min(discount_value, subtotal_try)  # Discount can't exceed total
            discounted_total = max(0, subtotal_try - discount_amount)  # Total can't be negative
            kdv = discounted_total * 0.20
            total_with_vat = discounted_total + kdv

            # Generate parts table content
            parts_table_content = ""
            for idx, part in enumerate(parts, 1):
                code = str(part.get('part_code', ''))
                name = str(part.get('name', ''))
                price = float(part.get('price_try', 0))
                qty = int(part.get('quantity', 1))
                line_total = price * qty
                parts_table_content += f"""
                    <tr>
                        <td>{idx}</td>
                        <td>{code}</td>
                        <td>{name}</td>
                        <td>{qty}</td>
                        <td>{price:,.2f} TL</td>
                        <td>{line_total:,.2f} TL</td>
                    </tr>
                """

            # Generate discount row
            discount_row = ""
            discount_label = ""
            if discount_amount > 0:
                discount_label = "İskonto (%{:.0f})".format(discount_value) if discount_type == 'percentage' else "İskonto"
                discount_row = f"""
                <div class=\"total-row\">
                    <div>{discount_label}</div>
                    <div>-{discount_amount:,.2f} TL</div>
                </div>
                """

            # Prepare context for template
            offer = type('Offer', (), {})()
            offer.offer_number = offer_number
            offer.created_at = datetime.now()
            offer.customer_first_name = customer_name.split()[0] if customer_name else ''
            offer.customer_last_name = ' '.join(customer_name.split()[1:]) if customer_name and len(customer_name.split()) > 1 else ''
            offer.company_name = company_name
            offer.phone = phone
            offer.machine_model = request.form.get('machine_model', '')
            offer.serial_number = serial_number
            offer.offeror_name = current_user.full_name if hasattr(current_user, 'full_name') else current_user.username
            # Set validity date
            validity_date = (datetime.now() + timedelta(days=7)).strftime('%d.%m.%Y')

            # Render PDF HTML using the new template
            html_content = render_template(
                'offers_spare_parts_pdf.html',
                logo_base64=logo_base64,
                offer=offer,
                validity_date=validity_date,
                parts_table_content=parts_table_content,
                subtotal_try=subtotal_try,
                discount_amount=discount_amount,
                discount_label=discount_label,
                kdv=kdv,
                total_amount_try=total_with_vat
            )

            # Generate PDF using WeasyPrint
            pdf = HTML(string=html_content).write_pdf()
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename=spare_parts_offer_{offer_number}.pdf'
            return response
        except Exception as e:
            current_app.logger.error(f"PDF oluşturulurken hata: {str(e)}")
            flash('Teklif PDF oluşturulurken bir hata oluştu.', 'danger')
            return redirect(url_for('offers.offers_dashboard'))
    return render_template('create_spare_parts_offer.html')