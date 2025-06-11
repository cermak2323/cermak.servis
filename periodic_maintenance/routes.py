import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Eksik model ve modül importları
from database import db
from models import User, Permission, Part, Catalog, CatalogItem, Fault, FaultSolution, FaultReport, Machine, MaintenanceRecord, MachineMaintenanceRecord, QRCode, Invoice, Offer, PeriodicMaintenance, Oil, Notification
import io

from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, jsonify, current_app, session
from flask_login import login_required, current_user
from datetime import datetime, timezone, timedelta
import os
import time
from weasyprint import HTML
import logging
from utils import exchange_rates, get_latest_exchange_rate, get_current_exchange_rate  # Dinamik döviz kurlarını utils modülünden al, yeni import eklendi
import pandas as pd  # Excel işlemleri için
from sqlalchemy import inspect
from sqlalchemy.sql import text
import base64
import json

# Logger ayarları
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

periodic_maintenance_bp = Blueprint("periodic_maintenance", __name__)

def query_maintenances(machine_model="", maintenance_interval=""):
    """PeriodicMaintenance tablosundan filtreli bakım kayıtlarını sorgular ve formatı günceller."""
    query = PeriodicMaintenance.query
    if machine_model:
        query = query.filter_by(machine_model=machine_model)
    if maintenance_interval:
        query = query.filter(PeriodicMaintenance.maintenance_interval.in_([maintenance_interval, maintenance_interval.replace("Saatlik Bakım", "SAATLİK BAKIM")]))
    maintenances = query.all()

    # Veritabanındaki kayıtları yeni formata güncelle
    for m in maintenances:
        if "SAATLİK BAKIM" in m.maintenance_interval:
            m.maintenance_interval = m.maintenance_interval.replace("SAATLİK", "Saatlik")
    db.session.commit()

    return maintenances

@periodic_maintenance_bp.route("/periodic_maintenance", methods=["GET", "POST"])
@login_required
def periodic_maintenance():
    if not hasattr(current_user, "permissions") or not current_user.permissions.can_view_periodic_maintenance:
        flash("Bu modüle erişim yetkiniz yok!", "danger")
        return redirect(url_for("auth.dashboard"))

    machine_model = request.args.get("machine_model", "")
    maintenance_interval = request.args.get("maintenance_interval", "")
    filter_type = request.args.get("filter_type", "")

    # Yağları veritabanından al
    oils = Oil.query.all()

    # Bakım kayıtlarını sorgula
    maintenances = query_maintenances(machine_model, maintenance_interval)

    if request.method == "POST":
        try:
            # Yağ seçimlerini işle
            selected_oils = []
            for oil in oils:
                if request.form.get(f'oil_selected_{oil.id}'):
                    quantity = int(request.form.get(f'oil_quantity_{oil.id}', 1))
                    selected_oils.append({
                        'id': oil.id,
                        'name': oil.name,
                        'quantity': quantity
                    })
            
            # Seçilen yağları session'a kaydet
            session['selected_oils'] = selected_oils
            flash('Yağ seçimleri kaydedildi.', 'success')
            
            return redirect(url_for('periodic_maintenance.periodic_maintenance', 
                                  machine_model=machine_model,
                                  maintenance_interval=maintenance_interval))
        except Exception as e:
            flash(f'Yağ seçimleri kaydedilirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('periodic_maintenance.periodic_maintenance'))

    # Benzersiz machine_model değerlerini al
    machine_models = sorted(
        set([row[0] for row in PeriodicMaintenance.query.with_entities(PeriodicMaintenance.machine_model).distinct().all()])
    )
    valid_intervals = [
        "50 Saatlik Bakım", "250 Saatlik Bakım", "500 Saatlik Bakım",
        "750 Saatlik Bakım", "1000 Saatlik Bakım"
    ]

    # Önceden seçilmiş yağları al
    selected_oils = session.get('selected_oils', [])

    return render_template(
        "periodic_maintenance_view.html",
        maintenances=maintenances,
        machine_models=machine_models,
        maintenance_intervals=valid_intervals,
        selected_model=machine_model,
        selected_interval=maintenance_interval,
        exchange_rates={"EUR": {"sell": exchange_rates["EUR"]}},
        oils=oils,  # Yağları template'e gönder
        selected_oils=selected_oils  # Seçilmiş yağları template'e gönder
    )

@periodic_maintenance_bp.route("/update_database_schema", methods=["GET"])
@login_required
def update_database_schema():
    if current_user.role != 'admin':
        flash("Bu işlemi yapmak için yönetici yetkisine ihtiyacınız var!", "danger")
        return redirect(url_for("auth.dashboard"))

    try:
        inspector = inspect(db.engine)

        # Tüm modelleri tanımla
        models = [
            User, Permission, Part, Catalog, CatalogItem, Fault,
            FaultSolution, FaultReport, Machine, MaintenanceRecord,
            MachineMaintenanceRecord, QRCode, Invoice,
            PeriodicMaintenance, Offer
        ]

        for model in models:
            table_name = model.__tablename__
            columns = {column.name: column for column in model.__table__.columns}
            existing_tables = inspector.get_table_names()

            # Tablo yoksa oluştur
            if table_name not in existing_tables:
                model.__table__.create(db.engine)
                logger.debug(f"Tablo oluşturuldu: {table_name}")
                continue

            # Mevcut sütunları al
            existing_columns = {col['name']: col for col in inspector.get_columns(table_name)}

            # Eksik sütunları ekle
            for col_name, col in columns.items():
                if col_name not in existing_columns:
                    col_type = col.type
                    nullable = "NULL" if col.nullable else "NOT NULL"
                    default = ""

                    # Varsayılan değer kontrolü
                    if col.default is not None:
                        default_value = col.default.arg
                        if isinstance(default_value, bool):
                            default_value = 1 if default_value else 0
                        default = f"DEFAULT {default_value}"

                    # Sütun tipine göre SQL türü
                    if isinstance(col_type, db.Integer):
                        col_type_sql = "INTEGER"
                    elif isinstance(col_type, db.String):
                        col_type_sql = f"VARCHAR({col_type.length})"
                    elif isinstance(col_type, db.Float):
                        col_type_sql = "FLOAT"
                    elif isinstance(col_type, db.DateTime):
                        col_type_sql = "DATETIME"
                    elif isinstance(col_type, db.Boolean):
                        col_type_sql = "BOOLEAN"
                    elif isinstance(col_type, db.Text):
                        col_type_sql = "TEXT"
                    else:
                        col_type_sql = str(col_type)

                    # ALTER TABLE komutu
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type_sql} {nullable} {default}"
                    db.engine.execute(text(sql))
                    logger.debug(f"Sütun eklendi: {table_name}.{col_name}")

            # Yabancı anahtarları kontrol et ve ekle (isteğe bağlı)
            # Not: Yabancı anahtarlar için manuel kontrol gerekebilir

        flash("Veritabanı şeması başarıyla güncellendi!", "success")
    except Exception as e:
        logger.error(f"Veritabanı güncellenirken hata oluştu: {str(e)}")
        flash(f"Veritabanı güncellenirken hata oluştu: {str(e)}", "danger")

    return redirect(url_for("auth.dashboard"))

@periodic_maintenance_bp.route("/periodic_maintenance/download_pdf", methods=["GET", "POST"])
@login_required
def download_pdf():
    if not hasattr(current_user, "permissions") or not current_user.permissions.can_view_periodic_maintenance:
        flash("PDF İNDİRME YETKİNİZ YOK.", "danger")
        return redirect(url_for("auth.dashboard"))

    machine_model = request.form.get("machine_model", request.args.get("machine_model", ""))
    maintenance_interval = request.form.get("maintenance_interval", request.args.get("maintenance_interval", ""))
    filter_type = request.form.get("filter_type", request.args.get("filter_type", ""))

    logger.debug(f"PDF oluşturma - Alınan filtre tipi: {filter_type}")

    # Filtre tipini normalize et (büyük/küçük harf ve Türkçe karakter düzeltmesi)
    if filter_type.upper() in ["ORIJINAL", "ORİJİNAL"]:
        filter_type = "original"
    elif filter_type.upper() in ["MUADIL", "MUADİL"]:
        filter_type = "alternate"

    logger.debug(f"PDF oluşturma - Normalize edilmiş filtre tipi: {filter_type}")

    # Filtre türü kontrolü - daha sıkı validasyon
    if not filter_type or filter_type not in ["original", "alternate"]:
        flash("LÜTFEN FİLTRE TÜRÜNÜ SEÇİN (ORİJİNAL/MUADİL)!", "danger")
        return redirect(url_for("periodic_maintenance.periodic_maintenance", 
                              machine_model=machine_model, 
                              maintenance_interval=maintenance_interval))

    # Form verilerini kontrol et
    required_fields = {
        "first_name": "MÜŞTERİ ADI",
        "last_name": "MÜŞTERİ SOYADI",
        "company_name": "FİRMA ADI",
        "serial_number": "SERİ NUMARASI",
        "phone": "TELEFON",
        "offeror_name": "TEKLİFİ VEREN"
    }

    for field, label in required_fields.items():
        if not request.form.get(field):
            flash(f"{label} ALANI BOŞ BIRAKILAMAZ!", "danger")
            return redirect(url_for("periodic_maintenance.periodic_maintenance", 
                                  machine_model=machine_model, 
                                  maintenance_interval=maintenance_interval))

    # Bakım parçalarını al
    query = PeriodicMaintenance.query.filter_by(
        machine_model=machine_model,
        maintenance_interval=maintenance_interval
    )

    logger.debug(f"PDF için filtre tipi: {filter_type}")
    logger.debug(f"PDF için makine modeli: {machine_model}")
    logger.debug(f"PDF için bakım aralığı: {maintenance_interval}")

    # Tüm parçaları al ve belleğe cache'le
    maintenances = query.all()
    logger.debug(f"PDF için bulunan toplam parça sayısı: {len(maintenances)}")

    # Parça tablosu içeriğini oluştur
    table_content = """
        <tr>
            <th>SIRA NO</th>
            <th>PARÇA NO</th>
            <th>AÇIKLAMA</th>
            <th>ADET</th>
            <th>BİRİM FİYAT (TL)</th>
            <th>TOPLAM (TL)</th>
        </tr>
    """

    row_number = 1
    total_parts_price = 0
    total_oils_price = 0

    # Filtreleri ekle
    for m in maintenances:
        logger.debug(f"İşlenen parça: {m.filter_name}")
        logger.debug(f"Orijinal kod: {m.filter_part_code}, Muadil kod: {m.alternate_part_code}")
        logger.debug(f"Orijinal fiyat: {m.original_price_eur}, Muadil fiyat: {m.alternate_price_eur}")

        if filter_type == "original":
            # Orijinal parça seçildiğinde
            if m.filter_part_code and m.original_price_eur and m.original_price_eur > 0:
                part_code = m.filter_part_code
                price_eur = m.original_price_eur
                logger.debug(f"Orijinal parça seçildi: {part_code} - {price_eur} EUR")

                price_try = price_eur * exchange_rates["EUR"]
                total_parts_price += price_try
                table_content += f"""
                    <tr>
                        <td>{row_number}</td>
                        <td>{part_code}</td>
                        <td>{m.filter_name}</td>
                        <td>1</td>
                        <td>{price_try:,.2f} TL</td>
                        <td>{price_try:,.2f} TL</td>
                    </tr>
                """
                row_number += 1
        else:
            # Muadil parça seçildiğinde
            if m.alternate_part_code and m.alternate_price_eur and m.alternate_price_eur > 0:
                part_code = m.alternate_part_code
                price_eur = m.alternate_price_eur
                logger.debug(f"Muadil parça seçildi: {part_code} - {price_eur} EUR")

                price_try = price_eur * exchange_rates["EUR"]
                total_parts_price += price_try
                table_content += f"""
                    <tr>
                        <td>{row_number}</td>
                        <td>{part_code}</td>
                        <td>{m.filter_name}</td>
                        <td>1</td>
                        <td>{price_try:,.2f} TL</td>
                        <td>{price_try:,.2f} TL</td>
                    </tr>
                """
                row_number += 1
            # Muadil yoksa veya fiyatı yoksa, orijinal parçayı ekle
            elif m.filter_part_code and m.original_price_eur and m.original_price_eur > 0:
                part_code = m.filter_part_code
                price_eur = m.original_price_eur
                filter_name = f"{m.filter_name} (Muadil bulunmadığından orijinal)"
                logger.debug(f"Muadil bulunamadı, orijinal ekleniyor: {part_code} - {price_eur} EUR")

                price_try = price_eur * exchange_rates["EUR"]
                total_parts_price += price_try
                table_content += f"""
                    <tr>
                        <td>{row_number}</td>
                        <td>{part_code}</td>
                        <td>{filter_name}</td>
                        <td>1</td>
                        <td>{price_try:,.2f} TL</td>
                        <td>{price_try:,.2f} TL</td>
                    </tr>
                """
                row_number += 1

    # Yağları ekle
    oils = [
        {"code": "HD90-1", "name": "CER DİŞLİ YAĞI", "price_eur": 6.0},
        {"code": "HLP46", "name": "HİDROLİK YAĞI", "price_eur": 50.0},
        {"code": "15W/40-4", "name": "MOTOR YAĞI", "price_eur": 25.0},
        {"code": "15W/40-5", "name": "MOTOR YAĞI", "price_eur": 30.0}
    ]

    for oil in oils:
        use_key = f"oil_{oil['code']}_use"
        quantity_key = f"oil_{oil['code']}_quantity"
        if request.form.get(use_key) == "1":
            quantity = int(request.form.get(quantity_key, 1))
            if quantity > 0:
                price_try = oil["price_eur"] * exchange_rates["EUR"]
                total_price_try = price_try * quantity
                total_oils_price += total_price_try
                table_content += f"""
                    <tr>
                        <td>{row_number}</td>
                        <td>{oil['code']}</td>
                        <td>{oil['name']}</td>
                        <td>{quantity}</td>
                        <td>{price_try:,.2f} TL</td>
                        <td>{total_price_try:,.2f} TL</td>
                    </tr>
                """
                row_number += 1

    # İşçilik ve yol giderlerini ekle
    labor_cost = float(request.form.get("labor_cost", 0))
    travel_cost = float(request.form.get("travel_cost", 0))

    if labor_cost > 0:
        table_content += f"""
            <tr>
                <td>{row_number}</td>
                <td>CER001</td>
                <td>İŞÇİLİK BEDELİ</td>
                <td>1</td>
                <td>{labor_cost:,.2f} TL</td>
                <td>{labor_cost:,.2f} TL</td>
            </tr>
        """
        row_number += 1

    if travel_cost > 0:
        table_content += f"""
            <tr>
                <td>{row_number}</td>
                <td>CER002</td>
                <td>YOL GİDERİ</td>
                <td>1</td>
                <td>{travel_cost:,.2f} TL</td>
                <td>{travel_cost:,.2f} TL</td>
            </tr>
        """
        row_number += 1

    # Toplamları hesapla
    subtotal = total_parts_price + total_oils_price + labor_cost + travel_cost

    # İskonto hesapla
    discount_amount = 0
    discount_type = request.form.get("discount_type", "none")
    discount_value = float(request.form.get("discount_value", 0))

    if discount_type == "percentage":
        discount_amount = subtotal * (discount_value / 100)
    elif discount_type == "amount":
        discount_amount = discount_value

    # KDV ve genel toplamı hesapla
    discounted_total = subtotal - discount_amount
    kdv = discounted_total * 0.20
    grand_total = discounted_total + kdv

    # Teklif numarası oluşturma: Veritabanındaki mevcut teklif sayısına göre
    current_year = datetime.now().strftime('%Y')
    # En son teklif numarasını bul ve bir sonrakini oluştur
    last_offer = Offer.query.filter(Offer.offer_number.like(f"CERMAK{current_year}-%"))\
        .order_by(Offer.offer_number.desc())\
        .first()

    if last_offer:
        last_number = int(last_offer.offer_number.split('-')[1])
        new_offer_number = last_number + 1
    else:
        new_offer_number = 1

    offer_number = f"CERMAK{current_year}-{new_offer_number:04d}"

    # Benzersizliği kontrol et
    while Offer.query.filter_by(offer_number=offer_number).first() is not None:
        new_offer_number += 1
        offer_number = f"CERMAK{current_year}-{new_offer_number:04d}"

    # Geçerlilik tarihi (1 hafta sonrası)
    validity_date = (datetime.now() + timedelta(days=7)).strftime('%d.%m.%Y')

    # Teklifi Offer tablosuna kaydet
    pdf_path = os.path.join("static", "offers", f"offer_{offer_number}.pdf")
    new_offer = Offer(
        offer_number=offer_number,
        machine_model=machine_model,
        maintenance_interval=maintenance_interval,
        serial_number=serial_number,
        filter_type="Orijinal" if filter_type == "original" else "Muadil",
        customer_first_name=first_name,
        customer_last_name=last_name,
        company_name=company_name,
        phone=phone,
        offeror_name=offeror_name,
        labor_cost=labor_cost / exchange_rates["EUR"],
        travel_cost=travel_cost / exchange_rates["EUR"],
        total_amount=grand_total,  # TL olarak kaydediliyor
        discount_type=discount_type,
        discount_value=discount_value,
        status="Teklif Verildi",
        pdf_file_path=pdf_path,
        created_by=current_user.id,
        created_at=datetime.now(timezone.utc),
        is_active=True  # Varsayılan olarak aktif
    )
    db.session.add(new_offer)
    db.session.commit()

    # Filtre ve yağ tablosu
    table_content = """
        <tr>
            <th>SIRA NO</th>
            <th>PARÇA NO</th>
            <th>AÇIKLAMA</th>
            <th>ADET</th>
            <th>BİRİM FİYAT (TL)</th>
            <th>TOPLAM (TL)</th>
        </tr>
    """
    row_number = 1
    total_parts_try = 0

    # Filtreleri ekle
    for maintenance in maintenances:
        logger.debug(f"PDF için işlenen parça: {maintenance.filter_name}")
        logger.debug(f"PDF için orijinal kod: {maintenance.filter_part_code}, Muadil kod: {maintenance.alternate_part_code}")
        logger.debug(f"PDF için orijinal fiyat: {maintenance.original_price_eur}, Muadil fiyat: {maintenance.alternate_price_eur}")

        part_code = None
        price_eur = None

        if filter_type == "original":
            # Orijinal parça seçildiğinde
            if maintenance.filter_part_code and maintenance.original_price_eur and maintenance.original_price_eur > 0:
                part_code = maintenance.filter_part_code
                price_eur = maintenance.original_price_eur
                logger.debug(f"PDF için orijinal parça ekleniyor: {part_code}")
        else:
            # Muadil parça seçildiğinde
            if maintenance.alternate_part_code and maintenance.alternate_price_eur and maintenance.alternate_price_eur > 0:
                part_code = maintenance.alternate_part_code
                price_eur = maintenance.alternate_price_eur
                logger.debug(f"PDF için muadil parça ekleniyor: {part_code}")
            # Muadil yoksa veya fiyatı yoksa, orijinal parçayı ekle
            elif maintenance.filter_part_code and maintenance.original_price_eur and maintenance.original_price_eur > 0:
                part_code = maintenance.filter_part_code
                price_eur = maintenance.original_price_eur
                maintenance.filter_name = f"{maintenance.filter_name} (Muadil bulunmadığından orijinal)"
                logger.debug(f"PDF için muadil bulunamadı, orijinal ekleniyor: {part_code}")

        if part_code and price_eur:
            price_try = price_eur * exchange_rates["EUR"]
            total_try = price_try
            total_parts_try += total_try

            table_content += f"""
                <tr>
                    <td>{row_number}</td>
                    <td>{part_code}</td>
                    <td>{maintenance.filter_name}</td>
                    <td>1</td>
                    <td>{price_try:,.2f} TL</td>
                    <td>{total_try:,.2f} TL</td>
                </tr>
            """
            row_number += 1

    # Yağları ekle
    if selected_oils:
        for oil in selected_oils:
            price_try = oil["price_eur"] * exchange_rates["EUR"]
            unit_price_try = oil["unit_price_eur"] * exchange_rates["EUR"]
            table_content += f"""
                <tr>
                    <td>{row_number}</td>
                    <td>{oil['code']}</td>
                    <td>{oil['name']}</td>
                    <td>{oil['quantity']}</td>
                    <td>{unit_price_try:,.2f} TL</td>
                    <td>{price_try:,.2f} TL</td>
                </tr>
            """
            row_number += 1

    # İşçilik giderini ekle
    if labor_cost > 0:
        table_content += f"""
            <tr>
                <td>{row_number}</td>
                <td>CER001</td>
                <td>İŞÇİLİK BEDELİ</td>
                <td>1</td>
                <td>{labor_cost:,.2f} TL</td>
                <td>{labor_cost:,.2f} TL</td>
            </tr>
        """
        row_number += 1

    # Yol giderini ekle
    if travel_cost > 0:
        table_content += f"""
            <tr>
                <td>{row_number}</td>
                <td>CER002</td>
                <td>YOL GİDERİ</td>
                <td>1</td>
                <td>{travel_cost:,.2f} TL</td>
                <td>{travel_cost:,.2f} TL</td>
            </tr>
        """
        row_number += 1

    # Toplamları hesapla
    subtotal = total_parts_price + total_oils_price + labor_cost + travel_cost

    # İskonto hesapla
    discount_amount = 0
    discount_type = request.form.get("discount_type", "none")
    discount_value = float(request.form.get("discount_value", 0))

    if discount_type == "percentage":
        discount_amount = subtotal * (discount_value / 100)
    elif discount_type == "amount":
        discount_amount = discount_value

    # KDV ve genel toplamı hesapla
    discounted_total = subtotal - discount_amount
    kdv = discounted_total * 0.20
    grand_total = discounted_total + kdv

    serial_number = request.form.get("serial_number", "")
    first_name = request.form.get("first_name", "")
    last_name = request.form.get("last_name", "")
    company_name = request.form.get("company_name", "")
    phone = request.form.get("phone", "")
    offeror_name = request.form.get("offeror_name", "")
    selected_oils = session.get('selected_oils', [])
    service_total = subtotal
    discount_label = "İSKONTO" if discount_type != "none" else ""
    total_amount_try = grand_total

    # Mevcut download_pdf fonksiyonunun içindeki html_content kısmını güncelliyoruz
    html_content = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Periyodik Bakım Teklifi</title>
    <style>
        @page {{ 
            size: A4; 
            margin: 15mm;
        }}
        body {{ 
            font-family: 'Helvetica', 'Arial', sans-serif; 
            margin: 0; 
            padding: 0; 
            background-color: #FFFFFF; 
            color: #000000; 
            text-transform: uppercase; 
            font-size: 11px; 
        }}
        .container {{ 
            max-width: 900px; 
            margin: 20px auto; 
            padding: 20px; 
            background-color: #FFFFFF; 
            position: relative; 
            border: 2px solid #C8102E; 
            box-shadow: 0 3px 6px rgba(0,0,0,0.1); 
        }}
        h1 {{ 
            color: #C8102E; 
            font-size: 20px; 
            font-weight: bold; 
            text-align: center; 
            margin: 15px 0; 
            border-bottom: 2px solid #C8102E; 
            padding-bottom: 8px; 
        }}
        .offer-details {{ 
            display: flex; 
            justify-content: space-between; 
            margin-bottom: 20px; 
            font-size: 11px; 
        }}
        .offer-details div {{ 
            width: 48%; 
        }}
        .offer-details p {{ 
            margin: 4px 0; 
            line-height: 1.3; 
        }}
        table.items {{ 
            width: 100%; 
            border-collapse: collapse; 
            margin: 20px 0; 
            font-size: 10px; 
        }}
        table.items th, table.items td {{ 
            border: 1px solid #C8102E; 
            padding: 8px; 
            text-align: left; 
        }}
        table.items th {{ 
            background-color: #C8102E; 
            color: #FFFFFF; 
            font-weight: bold; 
        }}
        table.items td {{ 
            background-color: #FFFFFF; 
        }}
        table.items tr:nth-child(even) td {{ 
            background-color: #F9F9F9; 
        }}
        table.items th:nth-child(1), table.items td:nth-child(1) {{ width: 5%; }}  /* SIRA NO */
        table.items th:nth-child(2), table.items td:nth-child(2) {{ width: 20%; }} /* PARÇA NO */
        table.itemsth:nth-child(3), table.items td:nth-child(3) {{ width: 35%; }} /* AÇIKLAMA */
        table.items th:nth-child(4), table.items td:nth-child(4) {{ width: 5%; }}  /* ADET */
        table.items th:nth-child5), table.items td:nth-child(5) {{ width: 15%; }} /* BİRİM FİYAT (TL)        table.items th:nth-child(6), table.items td:nth-child(6) {{ width: 20%; }} /* TOPLAM (TL) */
        table.totals {{ 
            width: 50%;
            margin: 20px 0 20px auto; 
            border-collapse: collapse; 
            font-size: 11px; 
        }}
        table.totals tr {{ 
            margin-bottom: 8px; 
        }}
        table.totals td {{ 
            border: 1px solid #C8102E; 
            padding: 8px; 
            background-color: #F5F5F5; 
            color: #C8102E; 
            font-weight: bold; 
            box-shadow: 0 1px 2px rgba(0,0,0,0.05); 
        }}
        table.totals tr:last-child td {{ 
            border: 2px solid #C8102E; 
            background-color: #FFE6E6; 
        }}
        table.totals td:first-child {{ 
            width: 70%; 
            text-align: left; 
        }}
        table.totals td:last-child {{ 
            width: 30%; 
            text-align: right; 
        }}
        .invoice-number {{            margin-top: 20px; 
            text-align: right; 
            font-size: 12px; 
            color: #C8102E; 
            font-weight: bold; 
        }}
        .notes {{ 
            margin-top: 20px; 
            font-size: 10px; 
            background-color: #F5F5F5; 
            padding: 15px; 
            border-left: 3px solid #C8102E; 
            page-break-before: always;
        }}
        .notes p {{ 
            margin: 6px 0; 
            line-height: 1.3; 
        }}
        .notes ol {{ 
            margin: 0; 
            padding-left: 15px; 
        }}
        .notes li {{ 
            margin-bottom: 6px; 
        }}
        .signatures {{ 
            margin-top: 20px; 
            font-size:10px; 
            text-align: center; 
        }}
        .signatures div {{ 
            width: 50%; 
            margin: 0 auto; 
            border: 1px solid #C8102E; 
            padding: 15px; 
            background-color: #F5F5F5; 
            box-shadow: 0 1px 2px rgba(0,0,0,0.05); 
        }}
        .signatures p {{ 
            margin: 4px 0; 
            line-height: 1.3; 
        }}
        .footer-section {{ 
            margin-top: 20px; 
            background-color: #E0E0E0; 
            padding: 15px; 
            border-top: 2px solid #C8102E; 
            font-size: 10px; 
        }}
        .footer-title {{ 
            text-align: center; 
            font-size: 12px; 
            font-weight: bold; 
            color: #C8102E; 
            margin-bottom: 10px; 
        }}
        .footer-content {{ 
            display: flex; 
            flex-direction: column; 
            gap: 15px; 
        }}
        .bank-info, .company-info {{ 
            width: 100%; 
            text-align: left; 
        }}
        .section-title {{ 
            font-weight: bold; 
            text-decoration: underline; 
            margin-bottom: 8px; 
            color: #C8102E; 
        }}
        .bank-info p, .company-info p {{ 
            margin: 4px 0; 
            line-height: 1.3; 
        }}
        .bank-info span, .company-info span {{ 
            color: #C8102E; 
            font-weight: bold; 
        }}
        .corporate-signature {{ 
            margin-top: 20px; 
            text-align: center; 
            font-size: 10px; 
            color: #333333; 
            padding: 10px; 
            border-top: 1px solid #C8102E; 
        }}
    </style>
</head>
<body>
    <!-- İlk Sayfa: Teklife Özgü Bilgiler -->
    <div class="container">
        <h1>PERİYODİK BAKIM TEKLİFİ</h1>
        <div class="offer-details">
            <div>
                <p><strong>TEKLİF NO:</strong> {offer_number}</p>
                <p><strong>TEKLİF TARİHİ:</strong> {datetime.now().strftime('%d.%m.%Y')}</p>
                <p><strong>GEÇERLİLİK TARİHİ:</strong> {validity_date}</p>
                <p><strong>TEKLİFİ SUNAN:</strong> {offeror_name}</p>
            </div>
            <div>
                <p><strong>MAKİNE SERİ NO:</strong> {serial_number}</p>
                <p><strong>FİLTRE TÜRÜ:</strong> {'ORİJİNAL' if filter_type == 'original' else 'MUADİL'}</p>
                <p><strong>MAKİNE MODELİ:</strong> {machine_model or 'BELİRTİLMEDİ'}</p>
                <p><strong>BAKIM SAATİ:</strong> {maintenance_interval or 'BELİRTİLMEDİ'}</p>
            </div>
        </div>
        <table class="items">
            {table_content}
        </table>
        <table class="totals">
            <tr>
                <td>MAL/HİZMET TUTARI</td>
                <td>{service_total:,.2f} TL</td>
            </tr>
            {"<tr><td>" + discount_label + "</td><td>-" + f"{discount_amount:,.2f} TL" + "</td></tr>" if discount_amount > 0 else ""}
            <tr>
                <td>KDV (%20)</td>
                <td>{kdv:,.2f} TL</td>
            </tr>
            <tr>
                <td>GENEL TOPLAM</td>
                <td>{total_amount_try:,.2f} TL</td>
            </tr>
        </table>
        <!-- Fatura Numarası -->
        {"<div class='invoice-number'>FATURA NUMARASI: " + new_offer.invoice_number.upper() + "</div>" if new_offer.status == "Faturalandırıldı" and new_offer.invoice_number else ""}
        <div class="signatures">
            <div>
                <p><strong>ALICI FİRMA:</strong></p>
                <p>{company_name}</p>
                <p>KAŞE:</p>
                <p>İMZA:</p>
            </div>
        </div>
    </div>
    <!-- İkinci Sayfa: Notlar ve Footer -->
    <div class="container">
        <div class="notes">
            <p><strong>NOTLAR:</strong></p>
            <ol>
                <li>FİYAT OPSİYONUMUZ 7 İŞ GÜNÜDÜR.</li>
                <li>ÖDEME, PEŞİNDIR.</li>
                <li>TEKNİK HATA HARİÇ TEYİT EDİLMİŞ PARÇA İADESİ KABUL EDİLMEZ.</li>
                <li>GARANTİ KULLANICI HATALARI VE SARF KULLANIM HARİÇ 1 YILDIR.</li>
                <li>YURT DIŞI SİPARİŞLERDE TESLİM TARİHİ VERİLMİŞ OLMASINA RAĞMEN GÜMRÜK İŞLEMLERİNDEKİ GECİKMELERDEN CERMAK SERVİS HİÇ BİR SURETLE SORUMLU TUTULAMAZ.</li>
                <li>BU VE BENZERİ SEBEPLERDEN SİPARİŞİN İPTALİ DURUMUNDA ALINAN KAPARO BEDELİ İRAT OLARAK KAYDEDİLİR.</li>
                <li>SİPARİŞİN GEÇERLİ OLABİLMESİ; İLGİLİ TEKLİFİN FİRMA TARAFINDAN KAŞELİ VE YETKİLİ İMZALI OLARAK ALINAN BÖLGE VE/VEYA ŞUBEYE MAİL İLE TEYİTLİ ONAYINIZA MÜTEAKİP DEVREYE ALINIR.</li>
            </ol>
        </div>
        <div class="footer-section">
            <div class="footer-title">
                CERMAK SERVİS HİZMETLERİ VE YEDEK PARÇA LTD.ŞTİ.
            </div>
            <div class="footer-content">
                <div class="bank-info">
                    <p class="section-title">BANKA HESAP BİLGİLERİ:</p>
                    <p><span>BANKA:</span> YAPIKREDİ BANKASI</p>
                    <p><span>ŞUBE:</span> İKİTELLİ ORG. SAN. BÖLGESİ ŞUBESİ</p>
                    <p><span>ŞUBE KODU:</span> 818</p>
                    <p><span>HESAP NO:</span> 37635514</p>
                    <p><span>IBAN:</span> TR54 0006 7010 0000 0037 6355 14</p>
                </div>
                <div class="company-info">
                    <p class="section-title">FİRMA BİLGİLERİ:</p>
                    <p><span>CERMAK SERVİS HİZMETLERİ VE YEDEK PARÇA LTD.ŞTİ.</span></p>
                    <p>İOSB ESENLER SAN.SİT 3. BLOK NO: 5</p>
                    <p>34490 BAŞAKŞEHİR/İSTANBUL</p>
                    <p>TEL: 2126715744 FAKS: 2126715748</p>
                    <p>WEB SITESI: HTTP://WWW.CERENMAKINA.COM/</p>
                    <p>E-POSTA: INFO@CERENMAKINA.COM</p>
                    <p>VERGI DAIRESI: İKİTELLİ</p>
                    <p>VKN: 2060517466</p>
                    <p>MERSIS NO: 0206051746600018</p>
                    <p>TICARET SICIL NO: 517600</p>
                </div>
            </div>
        </div>
        <div class="corporate-signature">
            <p>CEREN MAKİNA İTH.İHR.PAZ.LTD.ŞTİ.</p>
            <p>© 2025 Cermak Servis Teknik Bilgi Sistemi. Tüm hakları saklıdır.</p>
        </div>
    </div>
</body>
</html>
"""

    # HTML içeriğini geçici bir dosyaya kaydet
    temp_html_path = os.path.join("static", "offers", f"temp_{offer_number}.html")
    os.makedirs(os.path.dirname(temp_html_path), exist_ok=True)
    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # PDF oluştur
    pdf_path_absolute = os.path.abspath(pdf_path)
    logger.debug(f"Mutlak PDF yolu: {pdf_path_absolute}")

    # PDF oluşturmadan önce dosyanın varlığını kontrol et
    logger.debug(f"PDF oluşturulmadan önce dosya kontrolü: {os.path.exists(pdf_path_absolute)}")

    try:
        HTML(string=html_content).write_pdf(pdf_path_absolute)
        logger.debug(f"PDF oluşturuldu: {pdf_path_absolute}")
        # Dosyanın tamamen yazıldığından emin olmak için kısa bir gecikme
        time.sleep(0.5)
    except Exception as e:
        logger.error(f"PDF oluşturulurken hata oluştu: {str(e)}")
        flash(f"PDF oluşturulurken hata oluştu: {str(e)}", "danger")
        return redirect(url_for("periodic_maintenance.periodic_maintenance", machine_model=machine_model, maintenance_interval=maintenance_interval))
    finally:
        # Geçici HTML dosyasını sil
        if os.path.exists(temp_html_path):
            try:
                os.remove(temp_html_path)
                logger.debug(f"Geçici HTML dosyası silindi: {temp_html_path}")
            except Exception as e:
                logger.error(f"Geçici HTML dosyası silinirken hata: {str(e)}")

    # PDF dosyasının oluşturulduğunu kontrol et
    logger.debug(f"PDF oluşturulduktan sonra dosya kontrolü: {os.path.exists(pdf_path_absolute)}")
    if os.path.exists(pdf_path_absolute):
        return send_file(pdf_path_absolute, as_attachment=True, download_name=f"Teklif_{offer_number}.pdf")
    else:
        flash("PDF dosyası oluşturulamadı, dosya bulunamadı!", "danger")
        return redirect(url_for("periodic_maintenance.periodic_maintenance", machine_model=machine_model, maintenance_interval=maintenance_interval))

@periodic_maintenance_bp.route("/offer_list", methods=["GET", "POST"])
@login_required
def offer_list():
    if not current_user.permissions.can_view_periodic_maintenance:
        flash("Bu modüle erişim yetkiniz yok!", "danger")
        return redirect(url_for("auth.dashboard"))

    # Makine modellerini al (filtreleme için)
    machine_models = sorted(
        set([row[0] for row in Offer.query.with_entities(Offer.machine_model).distinct().all()])
    )

    # Filtreleme parametrelerini al
    status_filter = request.args.get("status_filter", "")
    machine_model_filter = request.args.get("machine_model_filter", "")
    offer_number_filter = request.args.get("offer_number_filter", "")
    customer_name_filter = request.args.get("customer_name_filter", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    page = request.args.get("page", 1, type=int)

    # Teklifleri sorgula
    query = Offer.query.filter_by(is_active=True)  # Yalnızca aktif teklifler

    if status_filter:
        query = query.filter_by(status=status_filter)
    if machine_model_filter:
        query = query.filter_by(machine_model=machine_model_filter)
    if offer_number_filter:
        query = query.filter(Offer.offer_number.ilike(f"%{offer_number_filter}%"))
    if customer_name_filter:
        query = query.filter(
            (Offer.customer_first_name.ilike(f"%{customer_name_filter}%")) |
            (Offer.customer_last_name.ilike(f"%{customer_name_filter}%")) |
            (Offer.company_name.ilike(f"%{customer_name_filter}%"))
        )
    if date_from:
        try:
            date_from = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Offer.created_at >= date_from)
        except ValueError:
            flash("Geçersiz başlangıç tarihi formatı!", "danger")
    if date_to:
        try:
            date_to = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(Offer.created_at <= date_to)
        except ValueError:
            flash("Geçersiz bitiş tarihi!", "danger")

    # Sayfalama ile teklifleri al (sayfa başına 10 teklif)
    per_page = 10
    pagination = query.order_by(Offer.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    offers = pagination.items

    # Her teklif için parts ve oils alanlarını parse et
    import json
    for offer in offers:
        try:
            offer.parts_list = json.loads(offer.parts) if offer.parts else []
        except Exception:
            offer.parts_list = []
        try:
            offer.oils_list = json.loads(offer.oils) if offer.oils else []
        except Exception:
            offer.oils_list = []

    return render_template(
        "offer_list.html",
        offers=offers,
        pagination=pagination,
        machine_models=machine_models,
        status_filter=status_filter,
        machine_model_filter=machine_model_filter,
        offer_number_filter=offer_number_filter,
        customer_name_filter=customer_name_filter,
        date_from=date_from,
        date_to=date_to
    )

@periodic_maintenance_bp.route("/offer/<int:offer_id>/approve", methods=["POST"])
@login_required
def approve_offer(offer_id):
    if not current_user.permissions.can_view_periodic_maintenance:
        flash("Bu modüle erişim yetkiniz yok!", "danger")
        return redirect(url_for("auth.dashboard"))

    offer = Offer.query.get_or_404(offer_id)
    if offer.status != "Teklif Verildi":
        flash("Bu teklif zaten onaylanmış veya reddedilmiş!", "danger")
        return redirect(url_for("periodic_maintenance.offer_list"))

    offer.status = "Teklif Kabul Edildi"
    db.session.commit()

    # Notify all Depo users
    depo_users = User.query.filter_by(role="Depo").all()
    for user in depo_users:
        notif = Notification(
            user_id=user.id,
            message=f"{offer.offer_number} numaralı teklif onaylandı.",
            url=url_for('periodic_maintenance.offer_detail', offer_id=offer.id)
        )
        db.session.add(notif)
    db.session.commit()

    flash("Teklif onaylandı.", "success")
    return redirect(url_for("periodic_maintenance.offer_list"))

@periodic_maintenance_bp.route("/offer/<int:offer_id>/reject", methods=["POST"])
@login_required
def reject_offer(offer_id):
    if not current_user.permissions.can_view_periodic_maintenance:
        flash("Bu modüle erişim yetkiniz yok!", "danger")
        return redirect(url_for("auth.dashboard"))

    offer = Offer.query.get_or_404(offer_id)
    if offer.status != "Teklif Verildi":
        flash("Bu teklif zaten onaylanmış veya reddedilmiş!", "danger")
        return redirect(url_for("periodic_maintenance.offer_list"))

    offer.status = "Teklif Kabul Edilmedi"
    offer.is_active = False  # Teklif erişime kapanacak
    db.session.commit()
    flash("Teklif reddedildi ve erişime kapatıldı.", "success")
    return redirect(url_for("periodic_maintenance.offer_list"))

@periodic_maintenance_bp.route("/offer/<int:offer_id>/parts_prepared", methods=["POST"])
@login_required
def parts_prepared(offer_id):
    if not current_user.permissions.can_view_periodic_maintenance:
        flash("Bu modüle erişim yetkiniz yok!", "danger")
        return redirect(url_for("auth.dashboard"))

    offer = Offer.query.get_or_404(offer_id)
    if offer.status != "Teklif Kabul Edildi":
        flash("Önce teklif onaylanmalı!", "danger")
        return redirect(url_for("periodic_maintenance.offer_list"))

    offer.status = "Parçalar Hazırlandı"
    db.session.commit()
    flash("Parçalar hazırlandı.", "success")
    return redirect(url_for("periodic_maintenance.offer_list"))

@periodic_maintenance_bp.route("/offer/<int:offer_id>/parts_delivered", methods=["POST"])
@login_required
def parts_delivered(offer_id):
    if not current_user.permissions.can_view_periodic_maintenance:
        flash("Bu modüle erişim yetkiniz yok!", "danger")
        return redirect(url_for("auth.dashboard"))

    offer = Offer.query.get_or_404(offer_id)
    if offer.status != "Parçalar Hazırlandı":
        flash("Önce parçalar hazırlanmalı!", "danger")
        return redirect(url_for("periodic_maintenance.offer_list"))

    offer.status = "Parçalar Teslim Edildi"
    db.session.commit()
    flash("Parçalar servise teslim edildi.", "success")
    return redirect(url_for("periodic_maintenance.offer_list"))

@periodic_maintenance_bp.route("/offer/<int:offer_id>/service_started", methods=["POST"])
@login_required
def service_started(offer_id):
    if not current_user.permissions.can_view_periodic_maintenance:
        flash("Bu modüle erişim yetkiniz yok!", "danger")
        return redirect(url_for("auth.dashboard"))

    offer = Offer.query.get_or_404(offer_id)
    if offer.status != "Parçalar Teslim Edildi":
        flash("Önce parçalar servise teslim edilmeli!", "danger")
        return redirect(url_for("periodic_maintenance.offer_list"))

    offer.status = "Servis Yola Çıktı"
    db.session.commit()
    flash("Servis yola çıktı.", "success")
    return redirect(url_for("periodic_maintenance.offer_list"))

@periodic_maintenance_bp.route("/offer/<int:offer_id>/invoice", methods=["POST"])
@login_required
def invoice_offer(offer_id):
    if not current_user.permissions.can_view_periodic_maintenance:
        flash("Bu modüle erişim yetkiniz yok!", "danger")
        return redirect(url_for("auth.dashboard"))

    offer = Offer.query.get_or_404(offer_id)
    if offer.status != "Servis Yola Çıkmış":
        flash("Önce servis yola çıkmalı!", "danger")
        return redirect(url_for("periodic_maintenance.offer_list"))

    invoice_number = request.form.get("invoice_number")
    if not invoice_number:
        flash("Fatura numarası girilmedi!", "danger")
        return redirect(url_for("periodic_maintenance.offer_list"))

    offer.status = "Faturalandırıldı"
    offer.invoice_number = invoice_number.upper()
    db.session.commit()
    flash("Teklif faturalandırıldı.", "success")
    return redirect(url_for("periodic_maintenance.offer_list"))

@periodic_maintenance_bp.route("/offer/<int:offer_id>/payment_received", methods=["POST"])
@login_required
def payment_received(offer_id):
    if not current_user.permissions.can_view_periodic_maintenance:
        flash("Bu modüle erişim yetkiniz yok!", "danger")
        return redirect(url_for("auth.dashboard"))

    offer = Offer.query.get_or_404(offer_id)
    if offer.status != "Faturalandırıldı":
        flash("Önce faturalandırma yapılmalı!", "danger")
        return redirect(url_for("periodic_maintenance.offer_list"))

    offer.status = "Ödeme Alındı"
    db.session.commit()
    flash("Ödeme alındı.", "success")
    return redirect(url_for("periodic_maintenance.offer_list"))

@periodic_maintenance_bp.route("/bulk_update_offers", methods=["POST"])
@login_required
def bulk_update_offers():
    if not current_user.permissions.can_view_periodic_maintenance:
        flash("Bu modüle erişim yetkiniz yok!", "danger")
        return redirect(url_for("auth.dashboard"))

    offer_ids = request.form.getlist("offer_ids")
    action = request.form.get("action")

    if not offer_ids:
        flash("Lütfen en az bir teklif seçin!", "danger")
        return redirect(url_for("periodic_maintenance.offer_list"))

    if action == "delete":
        try:
            for offer_id in offer_ids:
                offer = Offer.query.get_or_404(offer_id)
                if offer.pdf_file_path and os.path.exists(offer.pdf_file_path):
                    os.remove(offer.pdf_file_path)
                db.session.delete(offer)
            db.session.commit()
            flash("Seçilen teklifler silindi.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Teklifler silinirken hata oluştu: {str(e)}", "danger")
    elif action == "update_status":
        new_status = request.form.get("new_status")
        if new_status:
            try:
                for offer_id in offer_ids:
                    offer = Offer.query.get_or_404(offer_id)
                    old_status = offer.status
                    offer.status = new_status
                    # Teklif reddedildiyse erişime kapat
                    if new_status == "Teklif Kabul Edilmedi":
                        offer.is_active = False
                db.session.commit()
                flash("Seçilen tekliflerin durumu güncellendi.", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"Durum güncellenirken hata oluştu: {str(e)}", "danger")
        else:
            flash("Lütfen bir durum seçin!", "danger")

    return redirect(url_for("periodic_maintenance.offer_list"))

@periodic_maintenance_bp.route("/export_offers", methods=["POST"])
@login_required
def export_offers():
    if not current_user.permissions.can_view_periodic_maintenance:
        flash("Bu modüle erişim yetkiniz yok!", "danger")
        return redirect(url_for("auth.dashboard"))

    export_type = request.form.get("export_type")

    # Filtreleme parametrelerini al (dışa aktarma için mevcut filtreleri kullan)
    status_filter = request.form.get("status_filter", "")
    machine_model_filter = request.form.get("machine_model_filter", "")
    offer_number_filter = request.form.get("offer_number_filter", "")
    customer_name_filter = request.form.get("customer_name_filter", "")
    date_from = request.form.get("date_from", "")
    date_to = request.form.get("date_to", "")

    # Teklifleri sorgula
    query = Offer.query.filter_by(is_active=True)  # Yalnızca aktif teklifler

    if status_filter:
        query = query.filter_by(status=status_filter)
    if machine_model_filter:
        query = query.filter_by(machine_model=machine_model_filter)
    if offer_number_filter:
        query = query.filter(Offer.offer_number.ilike(f"%{offer_number_filter}%"))
    if customer_name_filter:
        query = query.filter(
            (Offer.customer_first_name.ilike(f"%{customer_name_filter}%")) |
            (Offer.customer_last_name.ilike(f"%{customer_name_filter}%")) |
            (Offer.company_name.ilike(f"%{customer_name_filter}%"))
        )
    if date_from:
        try:
            date_from = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Offer.created_at >= date_from)
        except ValueError:
            flash("Geçersiz başlangıç tarihi formatı!", "danger")
    if date_to:
        try:
            date_to = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(Offer.created_at <= date_to)
        except ValueError:
            flash("Geçersiz bitiş tarihi!", "danger")

    offers = query.order_by(Offer.created_at.desc()).all()

    if export_type == "excel":
        # Excel dosyası oluştur
        data = []
        for offer in offers:
            data.append({
                "Teklif Numarası": offer.offer_number,
                "Makine Modeli": offer.machine_model,
                "Makine Seri Numarası": offer.serial_number,
                "Filtre Türü": offer.filter_type,
                "Müşteri Adı Soyadı": f"{offer.customer_first_name} {offer.customer_last_name}",
                "Şirket Adı": offer.company_name,
                "Telefon": offer.phone,
                "Teklif Veren": offer.offeror_name,
                "Toplam Tutar (TL)": offer.total_amount,
                "Durum": offer.status,
                "Fatura Numarası": offer.invoice_number if offer.invoice_number else "-",
                "Oluşturulma Tarihi": offer.created_at.strftime("%d.%m.%Y %H:%M")
            })
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheetname="Teklifler")
        output.seek(0)
        return send_file(
            output,
            download_name="teklifler.xlsx",
            as_attachment=True,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    elif export_type == "pdf":
        # PDF oluştur
        html_content = render_template("export_offers_pdf.html", offers=offers)
        pdf_path = os.path.join("static", "exports", "teklifler.pdf")
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        HTML(string=html_content).write_pdf(pdf_path)
        return send_file(pdf_path, as_attachment=True, download_name="teklifler.pdf")

    flash("Geçersiz dışa aktarma türü!", "danger")
    return redirect(url_for("periodicmaintenance.offer_list"))

@periodic_maintenance_bp.route("/edit_offer/<int:offer_id>", methods=["GET", "POST"])
@login_required
def edit_offer(offer_id):
    if not current_user.permissions.can_view_periodic_maintenance:
        flash("Bu modüle erişim yetkiniz yok!", "danger")
        return redirect(url_for("auth.dashboard"))

    offer = Offer.query.get_or_404(offer_id)

    if request.method == "POST":
        # Formdan gelen verileri al
        offer.serial_number = request.form.get("serial_number", offer.serial_number).upper()
        offer.filter_type = request.form.get("filter_type", offer.filter_type)
        offer.customer_first_name = request.form.get("customer_first_name", offer.customer_first_name).upper()
        offer.customer_last_name = request.form.get("customer_last_name", offer.customer_last_name).upper()
        offer.companyname = request.form.get("company_name", offer.company_name).upper()
        offer.phone = request.form.get("phone", offer.phone).upper()
        offer.offeror_name = request.form.get("offeror_name", offer.offeror_name).upper()

        # İşçilik ve yol giderleri (TL olarak alınıyor, EUR'ya çevrilecek)
        try:
            labor_cost = float(request.form.get("labor_cost", offer.labor_cost))
            travel_cost = float(request.form.get("travel_cost", offer.travel_cost))
            eur_to_try = exchange_rates["EUR"]
            offer.labor_cost = labor_cost / eur_to_try
            offer.travel_cost = travel_cost / eur_to_try
        except ValueError:
            flash("İşçilik veya yol ücreti geçerli bir sayı olmalıdır.", "danger")
            return redirect(url_for("periodic_maintenance.edit_offer", offer_id=offer.id))

        # Toplam tutar (doğrudan EUR olarak alınıyor)
        try:
            offer.total_amount = float(request.form.get("total_amount", offer.total_amount))
        except ValueError:
            flash("Toplam tutar geçerli bir sayı olmalıdır.", "danger")
            return redirect(url_for("periodic_maintenance.edit_offer", offer_id=offer.id))

        # İskonto bilgileri
        offer.discount_type = request.form.get("discount_type", offer.discount_type)
        try:
            offer.discount_value = float(request.form.get("discount_value", offer.discount_value))
        except ValueError:
            flash("İskonto değeri geçerli bir sayı olmalıdır.", "danger")
            return redirect(url_for("periodic_maintenance.edit_offer", offer_id=offer.id))

        #        # Durum
        new_status = request.form.get("status", offer.status)
        offer.status = new_status
        # Teklif reddedildiyse erişime kapat
        if new_status == "Teklif Kabul Edilmedi":
            offer.is_active = False

        # Veritabanına kaydet
        try:
            db.session.commit()
            flash("Teklif başarıyla güncellendi.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Teklif güncellenirken hata oluştu: {str(e)}", "danger")

        return redirect(url_for("periodic_maintenance.offer_list"))

    return render_template("edit_offer.html", offer=offer, exchange_rates={"EUR": exchange_rates["EUR"]})

@periodic_maintenance_bp.route("/generate_offer_pdf/<int:offer_id>")
@login_required
def generate_offer_pdf(offer_id):
    if not current_user.permissions.can_view_periodic_maintenance:
        flash("Bu modüle erişim yetkiniz yok!", "danger")
        return redirect(url_for("auth.dashboard"))

    offer = Offer.query.get_or_404(offer_id)
    
    # PDF dizinini kontrol et ve oluştur
    pdf_directory = os.path.join(current_app.root_path, "static", "offers")
    os.makedirs(pdf_directory, exist_ok=True)
    
    # PDF dosya yolunu güncelle
    pdf_filename = f"offer_{offer.offer_number}.pdf"
    pdf_path = os.path.join(pdf_directory, pdf_filename)
    
    try:
        # Logo dosyasını base64'e çevir
        logo_path = os.path.join(current_app.root_path, "static", "img", "logo.png")
        with open(logo_path, "rb") as image_file:
            logo_base64 = base64.b64encode(image_file.read()).decode()

        # Döviz kurunu al
        eur_to_try = get_current_exchange_rate()
        
        # Yağ kodlarını güncelle
        oil_codes = {
            "CER DİŞLİ YAĞI": "HD90-1",
            "HİDROLİK YAĞI": "HLP46",
            "MOTOR YAĞI 15W/40-4": "15W40-4",
            "MOTOR YAĞI 15W/40-5": "15W40-5"
        }
        
        # Parça ve filtre bilgilerini hazırla
        parts_table_content = ""
        row_number = 1
        total_parts_try = 0
        # Get maintenances for the offer
        maintenances = PeriodicMaintenance.query.filter_by(
            machine_model=offer.machine_model,
            maintenance_interval=offer.maintenance_interval
        ).all()
        for maintenance in maintenances:
            part_code = None
            price_eur = None
            filter_name = maintenance.filter_name
            if offer.filter_type == "original":
                if maintenance.filter_part_code and maintenance.original_price_eur and maintenance.original_price_eur > 0:
                    part_code = maintenance.filter_part_code
                    price_eur = maintenance.original_price_eur
            else:
                if maintenance.alternate_part_code and maintenance.alternate_price_eur and maintenance.alternate_price_eur > 0:
                    part_code = maintenance.alternate_part_code
                    price_eur = maintenance.alternate_price_eur
                elif maintenance.filter_part_code and maintenance.original_price_eur and maintenance.original_price_eur > 0:
                    part_code = maintenance.filter_part_code
                    price_eur = maintenance.original_price_eur
                    filter_name = f"{filter_name} (Muadil bulunmadığından orijinal)"
            if part_code and price_eur:
                price_try = price_eur * eur_to_try
                total_try = price_try
                total_parts_try += total_try

                parts_table_content += f"""
                    <tr>
                        <td>{row_number}</td>
                        <td>{part_code}</td>
                        <td>{filter_name}</td>
                        <td>1</td>
                        <td>{price_try:,.2f} TL</td>
                        <td>{total_try:,.2f} TL</td>
                    </tr>
                """
                row_number += 1
        # Manuel eklenen parçaları ekle
        if offer.parts:
            try:
                parts_data = json.loads(offer.parts) if isinstance(offer.parts, str) else offer.parts
                if isinstance(parts_data, list):
                    for part in parts_data:
                        if not isinstance(part, dict):
                            continue
                        price_eur = float(part.get('price_eur', 0))
                        quantity = int(part.get('quantity', 1))
                        price_try = price_eur * eur_to_try
                        total_try = price_try * quantity
                        total_parts_try += total_try
                        parts_table_content += f"""
                            <tr>
                                <td>{row_number}</td>
                                <td>{part.get('part_code', '-')}</td>
                                <td>{part.get('name', '-')}</td>
                                <td>{quantity}</td>
                                <td>{price_try:,.2f} TL</td>
                                <td>{total_try:,.2f} TL</td>
                            </tr>
                        """
                        row_number += 1
            except Exception as e:
                logger.error(f"Manuel parçalar eklenirken hata: {str(e)}")
                current_app.logger.error(f"Manuel parçalar eklenirken hata: {str(e)}")
        # Oils
        total_oils_try = 0
        if offer.oils:
            try:
                oils_data = json.loads(offer.oils) if isinstance(offer.oils, str) else offer.oils
                for oil in oils_data:
                    oil_name = oil.get('name', '')
                    oil_code = oil_codes.get(oil_name, oil.get('code', '-'))
                    price_eur = oil.get('price_eur', 0)
                    quantity = oil.get('quantity', 1)
                    price_try = price_eur * eur_to_try
                    total_try = price_try * quantity
                    total_oils_try += total_try
                    parts_table_content += f"""
                        <tr>
                            <td>{row_number}</td>
                            <td>{oil_code}</td>
                            <td>{oil_name}</td>
                            <td>{quantity}</td>
                            <td>{price_try:,.2f} TL</td>
                            <td>{total_try:,.2f} TL</td>
                        </tr>
                    """
                    row_number += 1
            except Exception as e:
                logger.error(f"Yağlar eklenirken hata: {str(e)}")
        # Always show oil row, even if zero
        if total_oils_try == 0:
            parts_table_content += f"""
                <tr>
                    <td>{row_number}</td>
                    <td>-</td>
                    <td>Yağlar</td>
                    <td>0</td>
                    <td>0,00 TL</td>
                    <td>0,00 TL</td>
                </tr>
            """
            row_number += 1
        # Labor
        labor_travel_try = 0
        labor_cost_try = offer.labor_cost * eur_to_try if offer.labor_cost else 0
        if labor_cost_try > 0:
            labor_travel_try += labor_cost_try
            parts_table_content += f"""
                <tr>
                    <td>{row_number}</td>
                    <td>CER001</td>
                    <td>İŞÇİLİK BEDELİ</td>
                    <td>1</td>
                    <td>{labor_cost_try:,.2f} TL</td>
                    <td>{labor_cost_try:,.2f} TL</td>
                </tr>
            """
            row_number += 1
        else:
            parts_table_content += f"""
                <tr>
                    <td>{row_number}</td>
                    <td>CER001</td>
                    <td>İŞÇİLİK BEDELİ</td>
                    <td>0</td>
                    <td>0,00 TL</td>
                    <td>0,00 TL</td>
                </tr>
            """
            row_number += 1
        # Travel
        travel_cost_try = offer.travel_cost * eur_to_try if offer.travel_cost else 0
        if travel_cost_try > 0:
            labor_travel_try += travel_cost_try
            parts_table_content += f"""
                <tr>
                    <td>{row_number}</td>
                    <td>CER002</td>
                    <td>YOL GİDERİ</td>
                    <td>1</td>
                    <td>{travel_cost_try:,.2f} TL</td>
                    <td>{travel_cost_try:,.2f} TL</td>
                </tr>
            """
            row_number += 1
        else:
            parts_table_content += f"""
                <tr>
                    <td>{row_number}</td>
                    <td>CER002</td>
                    <td>YOL GİDERİ</td>
                    <td>0</td>
                    <td>0,00 TL</td>
                    <td>0,00 TL</td>
                </tr>
            """
            row_number += 1

        # Toplam tutarları hesapla
        subtotal_try = total_parts_try + total_oils_try + labor_travel_try
        
        # İskonto hesapla
        discount_amount = 0
        if offer.discount_type == "percentage":
            discount_amount = subtotal_try * (offer.discount_value / 100)
        elif offer.discount_type == "amount":
            discount_amount = offer.discount_value
            
        discounted_total = subtotal_try - discount_amount
        kdv = discounted_total * 0.20
        total_amount_try = discounted_total + kdv

        # offer.parts listesini fiyatlarla güncelle
        updated_parts = []
        if offer.parts:
            try:
                parts_data = json.loads(offer.parts) if isinstance(offer.parts, str) else offer.parts
                if isinstance(parts_data, list):
                    for part in parts_data:
                        if not isinstance(part, dict):
                            continue
                            
                        price_eur = float(part.get('price_eur', 0))
                        price_try = price_eur * eur_to_try
                        updated_parts.append({
                            'part_code': part.get('part_code', ''),
                            'name': part.get('name', ''),
                            'quantity': int(part.get('quantity', 1)),
                            'price_eur': price_eur,
                            'price_try': price_try
                        })
            except Exception as e:
                current_app.logger.error(f"Parça fiyatları güncellenirken hata: {str(e)}")
                updated_parts = []
        else:
            updated_parts = []
        
        # HTML şablonunu render et
        html_content = render_template(
            "periodic_maintenance/offer_pdf.html",
            offer=offer,
            logo_base64=logo_base64,
            eur_to_try=eur_to_try,
            parts_table_content=parts_table_content,
            subtotal_try=subtotal_try,
            total_parts_try=total_parts_try,
            total_oils_try=total_oils_try,
            labor_travel_try=labor_travel_try,
            discount_amount=discount_amount,
            discount_label=f"İSKONTO (%{offer.discount_value})" if offer.discount_type == "percentage" else f"İSKONTO ({offer.discount_value} TL)" if offer.discount_type == "amount" else "",
            kdv=kdv,
            total_amount_try=total_amount_try,
            validity_date=(datetime.now() + timedelta(days=7)).strftime('%d.%m.%Y'),
            updated_parts=updated_parts
        )
        
        # PDF oluştur
        HTML(string=html_content).write_pdf(pdf_path)
        
        # Offer modelinde pdf_file_path'i güncelle
        offer.pdf_file_path = os.path.join("static", "offers", pdf_filename)
        db.session.commit()
        
        return send_file(pdf_path, as_attachment=True, download_name=f"Teklif_{offer.offer_number}.pdf")
        
    except Exception as e:
        current_app.logger.error(f"PDF oluşturma hatası: {str(e)}")
        flash(f"PDF oluşturulurken bir hata oluştu: {str(e)}", "danger")
        return redirect(url_for("periodic_maintenance.offer_list"))

@periodic_maintenance_bp.route("/delete_offer/<int:offer_id>")
@login_required
def delete_offer(offer_id):
    if not current_user.permissions.can_view_periodic_maintenance:
        flash("Bu modüle erişim yetkiniz yok!", "danger")
        return redirect(url_for("auth.dashboard"))

    offer = Offer.query.get_or_404(offer_id)
    try:
        if offer.pdf_file_path and os.path.exists(offer.pdf_file_path):
            os.remove(offer.pdf_file_path)
        db.session.delete(offer)
        db.session.commit()
        flash("Teklif silindi.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Teklif silinirken hata oluştu: {str(e)}", "danger")

    return redirect(url_for("periodic_maintenance.offer_list"))

@periodic_maintenance_bp.route('/upload_excel', methods=['POST'])
@login_required
def upload_excel():
    if not hasattr(current_user, 'permissions') or not current_user.permissions.can_view_periodic_maintenance:
        flash('Bu modüle erişim yetkiniz yok!', 'danger')
        return redirect(url_for('periodic_maintenance.periodic_maintenance'))

    if 'excel_file' not in request.files:
        flash('Dosya seçilmedi!', 'danger')
        return redirect(url_for('periodic_maintenance.periodic_maintenance'))

    file = request.files['excel_file']
    if file.filename == '':
        flash('Dosya seçilmedi!', 'danger')
        return redirect(url_for('periodic_maintenance.periodic_maintenance'))

    if file and file.filename.endswith(('.xlsx', '.xls')):
        try:
            df = pd.read_excel(file)

            # Sütun kontrolü
            required_columns = ['machine_model', 'filter_name', 'filter_part_code', 
                              'alternate_part_code', 'original_price_eur', 'alternate_price_eur', 
                              'maintenance_intervals']

            if not all(col in df.columns for col in required_columns):
                flash('Excel dosyasında gerekli sütunlar eksik!', 'danger')
                return redirect(url_for('periodic_maintenance.periodic_maintenance'))

            # Mevcut verileri sil
            PeriodicMaintenance.query.delete()
            db.session.commit()

            # Yeni verileri ekle
            for _, row in df.iterrows():
                # Bakım aralıklarını virgülle ayır ve her biri için ayrı kayıt oluştur
                maintenance_intervals = str(row['maintenance_intervals']).split(',')
                for interval in maintenance_intervals:
                    interval = interval.strip()  # Boşlukları temizle
                    if interval:  # Boş string kontrolü
                        maintenance = PeriodicMaintenance(
                            machine_model=str(row['machine_model']).strip(),
                            filter_name=str(row['filter_name']).strip(),
                            filter_part_code=str(row['filter_part_code']).strip(),
                            alternate_part_code=str(row['alternate_part_code']).strip() if pd.notna(row['alternate_part_code']) else None,
                            original_price_eur=float(row['original_price_eur']) if pd.notna(row['original_price_eur']) else 0.0,
                            alternate_price_eur=float(row['alternate_price_eur']) if pd.notna(row['alternate_price_eur']) else 0.0,
                            maintenance_interval=interval,
                            created_by=current_user.username,
                            created_at=datetime.now(timezone.utc)
                        )
                        db.session.add(maintenance)

            db.session.commit()
            flash('Excel dosyası başarıyla yüklendi!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Dosya yüklenirken hata oluştu: {str(e)}', 'danger')
    else:
        flash('Sadece .xlsx veya .xls dosyaları kabul edilir!', 'danger')

    return redirect(url_for('periodic_maintenance.periodic_maintenance'))

@periodic_maintenance_bp.route('/search_parts', methods=['POST'])
@login_required
def search_parts():
    search_term = request.form.get('search_term')
    parts = Part.query.filter(
        db.or_(
            Part.part_code.ilike(f'%{search_term}%'),
            Part.name.ilike(f'%{search_term}%')
        )
    ).all()
    results = [{
        'id': part.id,
        'part_name': part.name,
        'part_code': part.part_code,
        'price_eur': part.price_eur
    } for part in parts]
    return jsonify(results)

@periodic_maintenance_bp.route("/create_offer", methods=["GET", "POST"])
@login_required
def create_offer():
    if not current_user.permissions.can_view_periodic_maintenance:
        flash("Bu modüle erişim yetkiniz yok!", "danger")
        return redirect(url_for("auth.dashboard"))

    # Makine modellerini PeriodicMaintenance tablosundan al
    machine_models = sorted(
        set([row[0] for row in PeriodicMaintenance.query.with_entities(PeriodicMaintenance.machine_model).distinct().all()])
    )

   

    # Yağları al
    oils = Oil.query.all()
    
    # TCMB kurunu al
    eur_rate = exchange_rates["EUR"]

    if request.method == "POST":
        try:
            # Form verilerini al
            serial_number = request.form.get("serial_number").upper()
            machine_model = request.form.get("machine_model")
            maintenance_interval = request.form.get("maintenance_interval")
            customer_first_name = request.form.get("customer_first_name").title()
            customer_last_name = request.form.get("customer_last_name").title()
            company_name = request.form.get("company_name")
            phone = request.form.get("phone")
            
            # Filtre tipini normalize et
            filter_type = request.form.get("filter_type", "original")
            if filter_type.upper() in ["ORIJINAL", "ORİJİNAL"]:
                filter_type = "original"
            elif filter_type.upper() in ["MUADIL", "MUADİL"]:
                filter_type = "alternate"
            
            labor_cost = float(request.form.get("labor_cost", 0))
            travel_cost = float(request.form.get("travel_cost", 0))
            discount_type = request.form.get("discount_type", "none")
            discount_value = float(request.form.get("discount_value", 0))

            # Yedek parça ekleme adımından gelen parçaları al
            selected_parts_json = request.form.get('selected_parts')
            selected_parts = []
            if selected_parts_json:
                try:
                    selected_parts = json.loads(selected_parts_json)
                    # Her parça için gerekli alanları kontrol et ve düzenle
                    formatted_parts = []
                    for part in selected_parts:
                        if isinstance(part, dict):
                            formatted_part = {
                                'part_code': str(part.get('part_code', '')),
                                'name': str(part.get('name', '')),
                                'quantity': int(part.get('quantity', 1)),
                                'price_eur': float(part.get('price_eur', 0)),
                                'total_eur': float(part.get('price_eur', 0)) * int(part.get('quantity', 1))
                            }
                            formatted_parts.append(formatted_part)
                    selected_parts = formatted_parts
                except Exception as e:
                    current_app.logger.error(f"Parça verileri işlenirken hata: {str(e)}")
                    selected_parts = []

            # Seçilen yağları al
            selected_oils = []
            for key, value in request.form.items():
                if key.startswith("oil_selected_"):
                    oil_id = int(key.split("_")[-1])
                    if value == "on":  # Checkbox seçili
                        quantity = int(request.form.get(f"oil_quantity_{oil_id}", 1))
                        oil = Oil.query.get(oil_id)
                        if oil and quantity > 0:
                            selected_oils.append({
                                "name": oil.name,
                                "quantity": quantity,
                                "price_eur": oil.price_eur,
                                "total_eur": oil.price_eur * quantity
                            })

            # Tüm hesaplamaları TL cinsinden yap
            parts_total_tl = 0
            for part in selected_parts:
                # Önce fiyatı TL'ye çevir
                if 'price_eur' in part and part['price_eur']:
                    # EUR'den TL'ye çevir
                    price_tl = float(part['price_eur']) * eur_rate
                elif 'price_try' in part and part['price_try']:
                    # Zaten TL cinsinden
                    price_tl = float(part['price_try'])
                else:
                    price_tl = 0
                
                quantity = int(part.get('quantity', 1)) or 1
                parts_total_tl += price_tl * quantity
                
                # Part'a TL fiyatını da ekle
                part['price_try'] = price_tl

            # Yağların toplamını hesapla (TL cinsinden)
            oils_total_tl = 0
            for oil in selected_oils:
                price_tl = oil['price_eur'] * eur_rate
                oils_total_tl += price_tl * oil['quantity']
                # Yağa TL fiyatını da ekle
                oil['price_try'] = price_tl

            # Diğer maliyetler (zaten TL cinsinden)
            labor_cost_tl = labor_cost
            travel_cost_tl = travel_cost

            # Ara toplam (TL cinsinden)
            subtotal_tl = parts_total_tl + oils_total_tl + labor_cost_tl + travel_cost_tl

            # İskonto hesapla (TL cinsinden)
            if discount_type == "percentage":
                discount_amount = subtotal_tl * (discount_value / 100)
            elif discount_type == "amount":
                discount_amount = discount_value
            else:
                discount_amount = 0

            # Genel toplam (TL cinsinden)
            grand_total_tl = subtotal_tl - discount_amount
            
            # EUR cinsinden değerleri hesapla (veritabanı için)
            parts_total_eur = parts_total_tl / eur_rate if eur_rate > 0 else 0
            oils_total_eur = oils_total_tl / eur_rate if eur_rate > 0 else 0
            labor_cost_eur = labor_cost_tl / eur_rate if eur_rate > 0 else 0
            travel_cost_eur = travel_cost_tl / eur_rate if eur_rate > 0 else 0
            subtotal_eur = subtotal_tl / eur_rate if eur_rate > 0 else 0

            # Teklif numarası oluşturma: Veritabanındaki mevcut teklif sayısına göre
            current_year = datetime.now().strftime('%Y')
            # En son teklif numarasını bul ve bir sonrakini oluştur
            last_offer = Offer.query.filter(Offer.offer_number.like(f"CERMAK{current_year}-%"))\
                .order_by(Offer.offer_number.desc())\
                .first()

            if last_offer:
                last_number = int(last_offer.offer_number.split('-')[1])
                new_offer_number = last_number + 1
            else:
                new_offer_number = 1

            offer_number = f"CERMAK{current_year}-{new_offer_number:04d}"

            # Benzersizliği kontrol et
            while Offer.query.filter_by(offer_number=offer_number).first() is not None:
                new_offer_number += 1
                offer_number = f"CERMAK{current_year}-{new_offer_number:04d}"

            # Teklif oluştur
            offer = Offer(
                offer_number=offer_number,  # Teklif numarasını ekle
                serial_number=serial_number,
                machine_model=machine_model,
                maintenance_interval=maintenance_interval,
                customer_first_name=customer_first_name,
                customer_last_name=customer_last_name,
                company_name=company_name,
                phone=phone,
                filter_type=filter_type,
                parts=json.dumps(selected_parts),
                oils=json.dumps(selected_oils),
                labor_cost=labor_cost_eur,  # Euro olarak kaydet
                travel_cost=travel_cost_eur,  # Euro olarak kaydet
                discount_type=discount_type,
                discount_value=discount_value,
                discount_amount=discount_amount,
                subtotal=subtotal_eur,  # Euro olarak kaydet
                grand_total=grand_total_tl,  # TL olarak kaydediliyor
                status="Teklif Verildi",
                is_active=True,
                created_by=current_user.id
            )

            db.session.add(offer)
            db.session.commit()

            flash(f"Teklif başarıyla oluşturuldu! Teklif No: {offer_number}", "success")
            return redirect(url_for("periodic_maintenance.offer_list"))

        except Exception as e:
            db.session.rollback()
            flash(f"Teklif oluşturulurken bir hata oluştu: {str(e)}", "danger")
            return redirect(url_for("periodic_maintenance.create_offer"))

    return render_template(
        "create_offer.html",
        machine_models=machine_models,
        oils=oils,
        exchange_rates={"EUR": {"sell": eur_rate}}
    )

@periodic_maintenance_bp.route("/get_maintenance_parts", methods=["GET"])
@login_required
def get_maintenance_parts():
    if not current_user.permissions.can_view_periodic_maintenance:
        return jsonify({"error": "Yetkiniz yok"}), 403

    machine_model = request.args.get("machine_model")
    maintenance_interval = request.args.get("maintenance_interval")
    filter_type = request.args.get("filter_type")

    logger.debug(f"Filtre tipi: {filter_type}")
    logger.debug(f"Makine modeli: {machine_model}")
    logger.debug(f"Bakım aralığı: {maintenance_interval}")

    if not all([machine_model, maintenance_interval, filter_type]):
        return jsonify({"error": "Eksik parametreler"}), 400

    try:
        # TCMB kurunu al
        eur_rate = exchange_rates["EUR"]

        # Periyodik bakım parçalarını al
        maintenances = PeriodicMaintenance.query.filter_by(
            machine_model=machine_model,
            maintenance_interval=maintenance_interval
        ).all()

        logger.debug(f"Bulunan toplam parça sayısı: {len(maintenances)}")

        parts_data = []
        for part in maintenances:
            logger.debug(f"İşlenen parça: {part.filter_name}")
            logger.debug(f"Orijinal kod: {part.filter_part_code}, Muadil kod: {part.alternate_part_code}")
            logger.debug(f"Orijinal fiyat: {part.original_price_eur}, Muadil fiyat: {part.alternate_price_eur}")

            if filter_type == "original":
                # Orijinal parça seçildiğinde
                if part.filter_part_code and part.original_price_eur and part.original_price_eur > 0:
                    parts_data.append({
                        "id": part.id,
                        "part_code": part.filter_part_code,
                        "name": part.filter_name,
                        "price_tl": round(part.original_price_eur * eur_rate, 2),
                        "quantity": 1,
                        "is_alternate": False
                    })
                    logger.debug(f"Orijinal parça eklendi: {part.filter_part_code}")
            else:
                # Muadil parça seçildiğinde
                if part.alternate_part_code and part.alternate_price_eur and part.alternate_price_eur > 0:
                    parts_data.append({
                        "id": part.id,
                        "part_code": part.alternate_part_code,
                        "name": part.filter_name,
                        "price_tl": round(part.alternate_price_eur * eur_rate, 2),
                        "quantity": 1,
                        "is_alternate": True
                    })
                    logger.debug(f"Muadil parça eklendi: {part.alternate_part_code}")
                # Muadil yoksa veya fiyatı yoksa, orijinal parçayı ekle
                elif part.filter_part_code and part.original_price_eur and part.original_price_eur > 0:
                    parts_data.append({
                        "id": part.id,
                        "part_code": part.filter_part_code,
                        "name": f"{part.filter_name} (Muadil bulunmadığından orijinal)",
                        "price_tl": round(part.original_price_eur * eur_rate, 2),
                        "quantity": 1,
                        "is_alternate": False
                    })
                    logger.debug(f"Muadil bulunamadı, orijinal eklendi: {part.filter_part_code}")

        logger.debug(f"Toplam {len(parts_data)} parça bulundu")
        return jsonify({
            "parts": parts_data,
            "eur_rate": eur_rate
        })
    except Exception as e:
        logger.error(f"Parça listesi alınırken hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@periodic_maintenance_bp.route("/offer/<int:offer_id>/update_status", methods=["POST"])
@login_required
def update_offer_status(offer_id):
    if not current_user.permissions.can_view_periodic_maintenance:
        flash("Bu işlem için yetkiniz yok!", "danger")
        return redirect(url_for("auth.dashboard"))

    offer = Offer.query.get_or_404(offer_id)
    new_status = request.form.get("new_status")
    comment = request.form.get("comment", "")
    
    # Durum geçiş kuralları
    valid_transitions = {
        "Teklif Verildi": ["Onaylandı", "Reddedildi", "Revizyon İstendi"],
        "Revizyon İstendi": ["Onaylandı", "Reddedildi"],
        "Onaylandı": ["Parçalar Hazırlanıyor"],
        "Parçalar Hazırlanıyor": ["Parçalar Hazırlandı"],
        "Parçalar Hazırlandı": ["Servise Teslim Edildi"],
        "Servise Teslim Edildi": ["Ödeme Bekleniyor"],
        "Ödeme Bekleniyor": ["Ödeme Alındı"],
        "Ödeme Alındı": ["Faturalandırıldı"],
        "Faturalandırıldı": ["Tamamlandı"]
    }

    if new_status not in valid_transitions.get(offer.status, []):
        flash(f"Geçersiz durum değişikliği! {offer.status} durumundan {new_status} durumuna geçiş yapılamaz.", "danger")
        return redirect(url_for("periodic_maintenance.offer_list"))

    # Özel durum kontrolleri
    if new_status == "Faturalandırıldı":
        invoice_number = request.form.get("invoice_number")
        if not invoice_number:
            flash("Fatura numarası gerekli!", "danger")
            return redirect(url_for("periodic_maintenance.offer_list"))
        offer.invoice_number = invoice_number

    # Durum güncelleme
    old_status = offer.status
    offer.status = new_status
    
    # Durum geçmişi kaydetme
    status_history = {
        "from_status": old_status,
        "to_status": new_status,
        "changed_by": current_user.username,
        "changed_at": datetime.now(timezone.utc).isoformat(),
        "comment": comment
    }
    
    if not hasattr(offer, 'status_history'):
        offer.status_history = []
    offer.status_history.append(status_history)

    try:
        db.session.commit()
        flash(f"Teklif durumu '{new_status}' olarak güncellendi.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Durum güncellenirken hata oluştu: {str(e)}", "danger")

    return redirect(url_for("periodic_maintenance.offer_list"))

@periodic_maintenance_bp.route("/offer/<int:offer_id>/status_history")
@login_required
def get_offer_status_history(offer_id):
    if not current_user.permissions.can_view_periodic_maintenance:
        return jsonify({"error": "Yetkiniz yok"}), 403

    offer = Offer.query.get_or_404(offer_id)
    return jsonify(offer.status_history or [])

@periodic_maintenance_bp.route("/offer/<int:offer_id>/parts")
@login_required
def get_offer_parts(offer_id):
    if not current_user.permissions.can_view_periodic_maintenance:
        return jsonify({"error": "Bu modüle erişim yetkiniz yok!"}), 403

    offer = Offer.query.get_or_404(offer_id)
    
    try:
        parts_data = []
        
        # Manuel eklenen parçaları ekle
        if offer.parts:
            try:
                parts = json.loads(offer.parts) if isinstance(offer.parts, str) else offer.parts
                if isinstance(parts, list):
                    for part in parts:
                        if isinstance(part, dict):
                            price_eur = float(part.get('price_eur', 0))
                            quantity = int(part.get('quantity', 1))
                            parts_data.append({
                                'part_code': part.get('part_code', ''),
                                'name': part.get('name', ''),
                                'quantity': quantity,
                                'price_eur': price_eur,
                                'total_eur': price_eur * quantity
                            })
            except Exception as e:
                current_app.logger.error(f"Parça verileri işlenirken hata: {str(e)}")
        
        return jsonify({
            "parts": parts_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Parçalar getirilirken hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@periodic_maintenance_bp.route('/offer/<int:offer_id>')
@login_required
def offer_detail(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    import json
    # Parçaları ve yağları ayrıştır
    try:
        offer.parts_list = json.loads(offer.parts) if offer.parts else []
    except Exception:
        offer.parts_list = []
    try:
        offer.oils_list = json.loads(offer.oils) if offer.oils else []
    except Exception:
        offer.oils_list = []

    # --- Filtre, yağ, işçilik, yol detaylarını parts_list'e ekle (PDF'deki gibi) ---
    # Filtre ve yağlar
    eur_to_try = get_current_exchange_rate() if 'get_current_exchange_rate' in globals() else 35.0
    # Filtreler (bakım tablosundan)
    from models import PeriodicMaintenance
    filter_rows = []
    maintenances = PeriodicMaintenance.query.filter_by(
        machine_model=offer.machine_model,
        maintenance_interval=offer.maintenance_interval
    ).all() if hasattr(offer, 'machine_model') and hasattr(offer, 'maintenance_interval') else []
    for maintenance in maintenances:
        part_code = None
        price_eur = None
        filter_name = maintenance.filter_name
        if offer.filter_type == "original":
            if maintenance.filter_part_code and maintenance.original_price_eur and maintenance.original_price_eur > 0:
                part_code = maintenance.filter_part_code
                price_eur = maintenance.original_price_eur
        else:
            if maintenance.alternate_part_code and maintenance.alternate_price_eur and maintenance.alternate_price_eur > 0:
                part_code = maintenance.alternate_part_code
                price_eur = maintenance.alternate_price_eur
            elif maintenance.filter_part_code and maintenance.original_price_eur and maintenance.original_price_eur > 0:
                part_code = maintenance.filter_part_code
                price_eur = maintenance.original_price_eur
                filter_name = f"{filter_name} (Muadil bulunmadığından orijinal)"
        if part_code and price_eur:
            price_try = price_eur * eur_to_try
            filter_rows.append({
                'part_code': part_code,
                'name': filter_name,
                'quantity': 1,
                'price_try': price_try
            })
    # Yağlar
    for oil in offer.oils_list:
        oil_name = oil.get('name', '')
        oil_code = oil.get('code', '-')
        price_eur = oil.get('price_eur', 0)
        quantity = oil.get('quantity', 1)
        price_try = price_eur * eur_to_try
        filter_rows.append({
            'part_code': oil_code,
            'name': oil_name,
            'quantity': quantity,
            'price_try': price_try
        })
    # İşçilik ve yol
    if hasattr(offer, 'labor_cost'):
        labor_cost = offer.labor_cost * eur_to_try if offer.labor_cost else 0
        filter_rows.append({
            'part_code': 'CER001',
            'name': 'İŞÇİLİK BEDELİ',
            'quantity': 1 if labor_cost > 0 else 0,
            'price_try': labor_cost
        })
    if hasattr(offer, 'travel_cost'):
        travel_cost = offer.travel_cost * eur_to_try if offer.travel_cost else 0
        filter_rows.append({
            'part_code': 'CER002',
            'name': 'YOL GİDERİ',
            'quantity': 1 if travel_cost > 0 else 0,
            'price_try': travel_cost
        })
    # Manuel eklenen parçalar zaten offer.parts_list'te
    # Hepsini birleştir
    offer.all_parts_list = filter_rows + offer.parts_list
    return render_template('offer_detail.html', offer=offer)