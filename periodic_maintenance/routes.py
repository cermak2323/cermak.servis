from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import login_required, current_user
from database import db
from models import PeriodicMaintenance, Offer, Part
from datetime import datetime, timezone, timedelta
import os
import time
from weasyprint import HTML
import logging
from utils import exchange_rates  # Dinamik döviz kurlarını utils modülünden al
from flask_mail import Message
import pandas as pd  # Excel işlemleri için
from sqlalchemy import inspect
from sqlalchemy.sql import text

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
            m.maintenance_interval = m.maintenance_interval.replace("SAATLİK BAKIM", "Saatlik Bakım")
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

    # Excel yükleme işlemi
    if request.method == "POST" and 'excel_file' in request.files:
        if current_user.role != 'admin':
            flash("Excel yükleme yetkiniz yok!", "danger")
            return redirect(url_for("periodic_maintenance.periodic_maintenance", machine_model=machine_model, maintenance_interval=maintenance_interval))

        file = request.files['excel_file']
        if file.filename == '':
            flash("Dosya seçilmedi!", "danger")
            return redirect(url_for("periodic_maintenance.periodic_maintenance", machine_model=machine_model, maintenance_interval=maintenance_interval))

        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            try:
                # Excel dosyasını oku
                df = pd.read_excel(file)

                # Excel sütun isimlerini düzelt ve küçük harfe çevir
                df.columns = df.columns.str.strip().str.lower()

                # Sütun isimlerini kontrol et
                expected_columns = {
                    'machine_model',
                    'filter_name',
                    'filter_part_code',
                    'alternate_part_code',
                    'original_price_eur',
                    'alternate_price_eur',
                    'maintenance_interval'
                }

                current_columns = set(df.columns)
                if not expected_columns.issubset(current_columns):
                    missing_cols = expected_columns - current_columns
                    flash(f"Excel dosyasında şu sütunlar eksik: {', '.join(missing_cols)}", "danger")
                    return redirect(url_for("periodic_maintenance.periodic_maintenance"))

                # Sütun isimlerini kontrol et
                if not all(col in df.columns for col in required_columns):
                    missing_cols = [col for col in required_columns if col not in df.columns]
                    flash(f"Excel dosyasında şu sütunlar eksik: {', '.join(missing_cols)}", "danger")
                    return redirect(url_for("periodic_maintenance.periodic_maintenance"))

                # Boş değerleri temizle
                df = df.fillna('')

                # maintenance_interval sütununu string'e çevir
                df['maintenance_interval'] = df['maintenance_interval'].astype(str)
                return redirect(url_for("periodic_maintenance.periodic_maintenance", machine_model=machine_model, maintenance_interval=maintenance_interval))

                # Mevcut verileri sil (opsiyonel, eğer tüm veriyi güncellemek istiyorsanız)
                PeriodicMaintenance.query.delete()
                db.session.commit()

                # Yeni verileri ekle
                maintenance_data = []
                for _, row in df.iterrows():
                    # Bakım aralıklarını virgülle ayır ve normalize et
                    intervals = [interval.strip() for interval in str(row['maintenance_interval']).split(',')]
                    normalized_intervals = []

                    for interval in intervals:
                        # Bakım saatlerini standartlaştır
                        interval = interval.replace("saatlik", "Saatlik")
                        interval = interval.replace("SAATLİK", "Saatlik")
                        if not interval.endswith("Bakım"):
                            interval += " Bakım"
                        normalized_intervals.append(interval)

                    # Her bir bakım aralığı için ayrı kayıt oluştur
                    for interval in normalized_intervals:
                        if interval:  # Boş olmayan bakım aralıkları için
                            maintenance_data.append(PeriodicMaintenance(
                                machine_model=str(row['machine_model']).strip(),
                                filter_name=str(row['filter_name']).strip(),
                                filter_part_code=str(row['filter_part_code']).strip(),
                                alternate_part_code=str(row['alternate_part_code']).strip() if pd.notna(row['alternate_part_code']) else None,
                                original_price_eur=float(row['original_price_eur']) if pd.notna(row['original_price_eur']) else 0.0,
                                alternate_price_eur=float(row['alternate_price_eur']) if pd.notna(row['alternate_price_eur']) else 0.0,
                                maintenance_interval=interval,
                                created_by=current_user.username,
                                created_at=datetime.now(timezone.utc)
                            ))
                db.session.add_all(maintenance_data)
                db.session.commit()
                flash("Excel verileri başarıyla yüklendi!", "success")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Excel yükleme hatası: {str(e)}")
                flash(f"Excel yüklenirken hata oluştu: {str(e)}", "danger")
        else:
            flash("Geçersiz dosya formatı! Sadece .xlsx veya .xls dosyaları kabul edilir.", "danger")

        return redirect(url_for("periodic_maintenance.periodic_maintenance", machine_model=machine_model, maintenance_interval=maintenance_interval))

    # Normal sorgulama işlemi
    maintenances = query_maintenances(machine_model, maintenance_interval)

    # Benzersiz machine_model değerlerini al
    machine_models = sorted(
        set([row[0] for row in PeriodicMaintenance.query.with_entities(PeriodicMaintenance.machine_model).distinct().all()])
    )
    valid_intervals = [
        "50 Saatlik Bakım", "250 Saatlik Bakım", "500 Saatlik Bakım",
        "750 Saatlik Bakım", "1000 Saatlik Bakım", "1250 Saatlik Bakım",
        "1500 Saatlik Bakım", "1750 Saatlik Bakım", "2000 Saatlik Bakım"
    ]

    return render_template(
        "periodic_maintenance_view.html",
        maintenances=maintenances,
        machine_models=machine_models,
        maintenance_intervals=valid_intervals,
        selected_model=machine_model,
        selected_interval=maintenance_interval,
        exchange_rates={"EUR": {"sell": exchange_rates["EUR"]}}
    )

def send_status_update_email(offer, new_status, recipient_emails):
    msg = Message(
        subject=f"Teklif Durumu Güncellendi: {offer.offer_number}",
        recipients=recipient_emails,
        body=f"""
Merhaba,

Teklif numarası {offer.offer_number} olan teklifin durumu güncellendi.

**Yeni Durum:** {new_status}
**Makine Modeli:** {offer.machine_model}
**Müşteri:** {offer.customer_first_name} {offer.customer_last_name}
**Şirket Adı:** {offer.company_name}
**Toplam Tutar:** {offer.total_amount} TL

Detayları görüntülemek için lütfen sisteme giriş yapın.

Saygılar,
Cermak Servis Hizmetleri
"""
    )
    try:
        mail.send(msg)
        logger.debug(f"E-posta gönderildi: {recipient_emails}")
    except Exception as e:
        logger.error(f"E-posta gönderilirken hata oluştu: {str(e)}")

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
            MachineMaintenanceRecord, QRCode, Warranty, Invoice,
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

    # Log form parameters to debug
    logger.debug("FORM PARAMETRELERİ: MACHINE_MODEL=%s, MAINTENANCE_INTERVAL=%s", machine_model, maintenance_interval)

    # Bakım saati doğrulama - Yeni format
    valid_intervals = [
        "50 Saatlik Bakım", "250 Saatlik Bakım", "500 Saatlik Bakım",
        "750 Saatlik Bakım", "1000 Saatlik Bakım", "1250 Saatlik Bakım",
        "1500 Saatlik Bakım", "1750 Saatlik Bakım", "2000 Saatlik Bakım"
    ]
    if maintenance_interval and maintenance_interval not in valid_intervals:
        # Eski formatta olabilir, kontrol et ve çevir
        old_format = maintenance_interval.replace("Saatlik Bakım", "SAATLİK BAKIM")
        if old_format in ["50 SAATLİK BAKIM", "250 SAATLİK BAKIM", "500 SAATLİK BAKIM",
                          "1000 SAATLİK BAKIM", "1250 SAATLİK BAKIM", "1500 SAATLİK BAKIM",
                          "1750 SAATLİK BAKIM", "2000 SAATLİK BAKIM"]:
            maintenance_interval = maintenance_interval.replace("SAATLİK BAKIM", "Saatlik Bakım")
        else:
            flash(f"GEÇERSİZ BAKIM SAATİ: {maintenance_interval}. LÜTFEN DOĞRU BAKIM SAATİ SEÇİN: {', '.join(valid_intervals)}", "danger")
            return redirect(url_for("periodic_maintenance.periodic_maintenance", machine_model=machine_model, maintenance_interval=maintenance_interval))

    maintenances = query_maintenances(machine_model, maintenance_interval)

    # Log queried maintenances
    logger.debug("SORGULANAN MAINTENANCES: %s", [(m.machine_model, m.maintenance_interval, m.filter_name) for m in maintenances])

    if request.method == "POST":
        first_name = request.form.get("first_name", "").upper()
        last_name = request.form.get("last_name", "").upper()
        company_name = request.form.get("company_name", "").upper()
        serial_number = request.form.get("serial_number", "").upper()
        phone = request.form.get("phone", "").upper()
        offeror_name = request.form.get("offeror_name", "").upper()
        filter_type = request.form.get("filter_type", "original")
        discount_type = request.form.get("discount_type", "none")  # none, percentage, amount
        discount_value = request.form.get("discount_value", "0")

        logger.debug(
            "FORM VERİLERİ: FIRST_NAME=%s, LAST_NAME=%s, COMPANY_NAME=%s, SERIAL_NUMBER=%s, PHONE=%s, OFFEROR_NAME=%s, FILTER_TYPE=%s, DISCOUNT_TYPE=%s, DISCOUNT_VALUE=%s",
            first_name, last_name, company_name, serial_number, phone, offeror_name, filter_type, discount_type, discount_value
        )

        if not all([first_name, last_name, company_name, serial_number, phone, offeror_name]):
            flash("LÜTFEN TÜM ZORUNLU ALANLARI DOLDURUN.", "danger")
            logger.error("ZORUNLU ALANLAR EKSİK: %s %s %s %s %s %s", first_name, last_name, company_name, serial_number, phone, offeror_name)
            return redirect(url_for("periodic_maintenance.periodic_maintenance", machine_model=machine_model, maintenance_interval=maintenance_interval))

        # Yağlar
        oils = [
            {"code": "HP90-1", "name": "CER DİŞLİ YAĞI", "price_eur": 6.0},
            {"code": "HLP46", "name": "HİDROLİK YAĞI", "price_eur": 50.0},
            {"code": "15W/40-4", "name": "MOTOR YAĞI", "price_eur": 25.0},
            {"code": "15W/40-5", "name": "MOTOR YAĞI", "price_eur": 30.0}
        ]
        selected_oils = []
        total_oil_price_eur = 0.0
        for oil in oils:
            use_key = f"oil_{oil['code']}_use"
            quantity_key = f"oil_{oil['code']}_quantity"
            if request.form.get(use_key) == "1":
                try:
                    quantity = int(request.form.get(quantity_key, 0))
                    if quantity <= 0:
                        flash(f"{oil['name']} İÇİN GEÇERLİ BİR ADET GİRİN.", "danger")
                        return redirect(url_for("periodic_maintenance.periodic_maintenance", machine_model=machine_model, maintenance_interval=maintenance_interval))
                    oil_price_eur = oil["price_eur"] * quantity
                    total_oil_price_eur += oil_price_eur
                    selected_oils.append({
                        "code": oil["code"],
                        "name": oil["name"],
                        "quantity": quantity,
                        "price_eur": oil_price_eur,
                        "unit_price_eur": oil["price_eur"]
                    })
                except ValueError:
                    flash(f"{oil['name']} İÇİN GEÇERLİ BİR SAYI GİRİN.", "danger")
                    return redirect(url_for("periodic_maintenance.periodic_maintenance", machine_model=machine_model, maintenance_interval=maintenance_interval))

        # İşçilik ve yol giderleri (TL olarak alındığı için EUR'ya çevirelim)
        try:
            labor_cost = float(request.form.get("labor_cost", 0.0)) if request.form.get("labor_cost") else 0.0
            travel_cost = float(request.form.get("travel_cost", 0.0)) if request.form.get("travel_cost") else 0.0
            eur_to_try = exchange_rates["EUR"]
            labor_cost_eur = labor_cost / eur_to_try
            travel_cost_eur = travel_cost / eur_to_try
        except ValueError:
            flash("İşçilik veya yol ücreti geçerli bir sayı olmalıdır.", "danger")
            return redirect(url_for("periodic_maintenance.periodic_maintenance", machine_model=machine_model, maintenance_interval=maintenance_interval))

        # Seçilen parçaları al
        selected_parts_data = []
        total_filter_price_eur = 0.0

        # Form'dan gelen seçili parçaları işle
        selected_parts = request.form.getlist('selected_parts[][id]')
        for i, part_id in enumerate(selected_parts):
            part_code = request.form.getlist('selected_parts[][part_code]')[i]
            part_name = request.form.getlist('selected_parts[][part_name]')[i]
            price_eur = float(request.form.getlist('selected_parts[][price_eur]')[i])
            # Satış fiyatı için 3 katını al
            sales_price_eur = price_eur * 3

            selected_parts_data.append({
                "filter_name": part_name,
                "part_code": part_code,
                "price_eur": sales_price_eur,
                "unit_price_eur": sales_price_eur,
                "is_alternate": False
            })
            total_filter_price_eur += sales_price_eur

        valid_maintenances = selected_parts_data

        for m in maintenances:
            price_eur = 0.0
            unit_price_eur = 0.0
            part_code = ""
            use_alternate = False

            # Muadil parça seçilmiş ve varsa kullan, yoksa orijinali kullan
            if filter_type == "alternate" and hasattr(m, 'alternate_price_eur') and hasattr(m, 'alternate_part_code') and m.alternate_price_eur is not None and m.alternate_part_code is not None and m.alternate_price_eur > 0:
                price_eur = m.alternate_price_eur
                unit_price_eur = price_eur
                part_code = m.alternate_part_code
                use_alternate = True
            else:
                # Orijinal parça bilgilerini kullan
                price_eur = m.original_price_eur
                unit_price_eur = price_eur
                part_code = m.filter_part_code
                use_alternate = False

            # Fiyat kontrolü
            if price_eur == 0.0:
                logger.warning(
                    "Fiyat 0.00 olarak hesaplandı: %s, Original Price EUR: %s, Alternate Price EUR: %s",
                    m.filter_name, m.original_price_eur, m.alternate_price_eur
                )
                continue  # Fiyatı 0 olan parçaları listeye ekleme

            # Parçanın daha önce eklenip eklenmediğini kontrol et
            if not any(vm["filter_name"] == m.filter_name for vm in valid_maintenances):
                total_filter_price_eur += price_eur
                valid_maintenances.append({
                    "filter_name": m.filter_name,
                    "part_code": part_code,
                    "price_eur": price_eur,
                    "unit_price_eur": unit_price_eur,
                    "is_alternate": use_alternate
                })

        # Log valid_maintenances to debug
        logger.debug(
            "VALID_MAINTENANCES: %s",
            [(m["filter_name"], m["part_code"], m["price_eur"], "Muadil" if m["is_alternate"] else "Orijinal") for m in valid_maintenances]
        )

        # Döviz kuru ile TL'ye çevir
        eur_to_try = exchange_rates["EUR"]
        total_filter_price_try = total_filter_price_eur * eur_to_try
        total_oil_price_try = total_oil_price_eur * eur_to_try

        # Toplamlar (TL cinsinden)
        service_total = total_filter_price_try + total_oil_price_try + labor_cost + travel_cost  # Mal/Hizmet Tutarı

        # İskonto Hesaplama
        discount_amount = 0.0
        discount_label = ""
        try:
            discount_value = float(discount_value) if discount_value else 0.0
            if discount_type == "percentage" and discount_value > 0:
                discount_amount = service_total * (discount_value / 100)
                discount_label = f"İSKONTO (%{discount_value})"
            elif discount_type == "amount" and discount_value > 0:
                discount_amount = discount_value
                discount_label = f"İSKONTO ({discount_value} TL)"
        except ValueError:
            flash("İSKONTO DEĞERİ GEÇERLİ BİR SAYI OLMALIDIR.", "danger")
            return redirect(url_for("periodic_maintenance.periodic_maintenance", machine_model=machine_model, maintenance_interval=maintenance_interval))

        # İskontoyu uygula
        discounted_total = service_total - discount_amount
        kdv_rate = 0.20
        kdv = discounted_total * kdv_rate
        total_amount_try = discounted_total + kdv

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
            labor_cost=labor_cost_eur,
            travel_cost=travel_cost_eur,
            total_amount=total_amount_try,  # TL olarak kaydediliyor
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

        # Filtreleri ekle
        if valid_maintenances:
            for maintenance in valid_maintenances:
                if not isinstance(maintenance, dict):
                    continue

                price_eur = maintenance.get("price_eur", 0)
                unit_price_eur = maintenance.get("unit_price_eur", price_eur)

                if price_eur > 0:
                    price_try = price_eur * eur_to_try
                    unit_price_try = unit_price_eur * eur_to_try

                    table_content += f"""
                        <tr>
                            <td>{row_number}</td>
                            <td>{maintenance.get('part_code', '-')}</td>
                            <td>{maintenance.get('filter_name', '-')}</td>
                            <td>1</td>
                            <td>{unit_price_try:,.2f} TL</td>
                            <td>{price_try:,.2f} TL</td>
                        </tr>
                    """
                    row_number += 1
        else:
            table_content += """
                <tr>
                    <td colspan="6" style="text-align: center; color: #C8102E; font-weight: bold;">
                        SEÇİLEN KRİTERLERE UYGUN FİLTRE BULUNAMADI.
                    </td>
                </tr>
            """

        # Yağları ekle
        if selected_oils:
            for oil in selected_oils:
                price_try = oil["price_eur"] * eur_to_try
                unit_price_try = oil["unit_price_eur"] * eur_to_try
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
        table.items th:nth-child5), table.items td:nth-child(5) {{ width: 15%; }} /* BİRİM FİYAT (TL) */
        table.items th:nth-child(6), table.items td:nth-child(6) {{ width: 20%; }} /* TOPLAM (TL) */
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

        # Seçilen parçaları ve filtre bilgilerini ekle
        total_parts = []

        # Manuel eklenen parçaları ekle
        for part in selected_parts_data:
            total_parts.append({
                "code": part["part_code"],
                "name": part["filter_name"],
                "quantity": 1,
                "unit_price_try": part["price_eur"] * eur_to_try,
                "total_price_try": part["price_eur"] * eur_to_try
            })

        # Bakım filtrelerini ekle    
        for maintenance in valid_maintenances:
            if maintenance["price_eur"] > 0:
                total_parts.append({
                    "code": maintenance["part_code"],
                    "name": maintenance["filter_name"],
                    "quantity": 1,
                    "unit_price_try": maintenance["price_eur"] * eur_to_try,
                    "total_price_try": maintenance["price_eur"] * eur_to_try
                })

        # Parts table content for PDF
        parts_table_content = ""
        for idx, part in enumerate(total_parts, 1):
            parts_table_content += f"""
                <tr>
                    <td>{idx}</td>
                    <td>{part['code']}</td>
                    <td>{part['name']}</td>
                    <td>1</td>
                    <td>{part['unit_price_try']:,.2f} TL</td>
                    <td>{part['total_price_try']:,.2f} TL</td>
                </tr>
            """

        html_content = html_content.replace("{table_content}", parts_table_content)

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

    # POST dışı istekler için yönlendirme (örneğin, GET isteği)
    return redirect(url_for("periodic_maintenance.periodic_maintenance", machine_model=machine_model, maintenance_interval=maintenance_interval))

import io
import pandas as pd
from flask import send_file
from weasyprint import HTML
from datetime import datetime
from flask_login import login_required, current_user

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
            flash("Geçersiz bitiş tarihi formatı!", "danger")

    # Sayfalama ile teklifleri al (sayfa başına 10 teklif)
    per_page = 10
    pagination = query.order_by(Offer.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    offers = pagination.items

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
    # Depocuya e-posta bildirimi gönder
    recipient_emails = ["depo@example.com"]
    send_status_update_email(offer, "Teklif Kabul Edildi", recipient_emails)
    db.session.commit()
    flash("Teklif onaylandı. Depo ekibine bildirim gönderildi.", "success")
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
    recipient_emails = ["admin@example.com"]
    send_status_update_email(offer, "Teklif Kabul Edilmedi", recipient_emails)
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
    recipient_emails = ["servis@example.com"]
    send_status_update_email(offer, "Parçalar Hazırlandı", recipient_emails)
    db.session.commit()
    flash("Parçalar hazırlandı. Servis ekibine bildirim gönderildi.", "success")
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
    recipient_emails = ["servis@example.com"]
    send_status_update_email(offer, "Parçalar Teslim Edildi", recipient_emails)
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
    recipient_emails = ["admin@example.com"]
    send_status_update_email(offer, "Servis Yola Çıktı", recipient_emails)
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
    if offer.status != "Servis Yola Çıktı":
        flash("Önce servis yola çıkmalı!", "danger")
        return redirect(url_for("periodic_maintenance.offer_list"))

    invoice_number = request.form.get("invoice_number")
    if not invoice_number:
        flash("Fatura numarası girilmedi!", "danger")
        return redirect(url_for("periodic_maintenance.offer_list"))

    offer.status = "Faturalandırıldı"
    offer.invoice_number = invoice_number.upper()
    recipient_emails = ["admin@example.com"]
    send_status_update_email(offer, "Faturalandırıldı", recipient_emails)
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
    recipient_emails = ["admin@example.com"]
    send_status_update_email(offer, "Ödeme Alındı", recipient_emails)
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
                    # E-posta bildirimi gönder
                    recipient_emails = ["depo@example.com", "servis@example.com", "admin@example.com"]
                    send_status_update_email(offer, new_status, recipient_emails)
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
            flash("Geçersiz bitiş tarihi formatı!", "danger")

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
    return redirect(url_for("periodic_maintenance.offer_list"))

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
    if not offer.pdf_file_path or not os.path.exists(offer.pdf_file_path):
        flash("PDF dosyası bulunamadı!", "danger")
        return redirect(url_for("periodic_maintenance.offer_list"))

    return send_file(offer.pdf_file_path, as_attachment=True, download_name=f"Teklif_{offer.offer_number}.pdf")

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