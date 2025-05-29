import os
import pandas as pd
from flask import Flask
from database import db
from models import (
    User, Permission, Part, Catalog, CatalogItem, Fault, FaultSolution,
    FaultReport, Machine, MaintenanceRecord, MachineMaintenanceRecord,
    QRCode, Invoice, PeriodicMaintenance, Offer, MaintenanceReminderSettings
)
from werkzeug.security import generate_password_hash
from datetime import datetime, timezone

app = Flask(__name__)
app.config.from_object('config.Config')

# Mutlak dosya yolu kullanarak veritabanı URI'sini ayarla
db_path = os.path.abspath(os.path.join(os.getcwd(), 'inventory_tracker.db'))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Veritabanını başlat
db.init_app(app)

def populate_db():
    with app.app_context():
        try:
            # 1. User
            if not User.query.first():
                users = [
                    User(
                        username="admin1",
                        password=generate_password_hash("password123", method='pbkdf2:sha256'),
                        role="admin",
                        created_at=datetime.now(timezone.utc)
                    ),
                    User(
                        username="servis1",
                        password=generate_password_hash("Cermak.2025", method='pbkdf2:sha256'),
                        role="servis",
                        created_at=datetime.now(timezone.utc)
                    ),
                    User(
                        username="muhendis1",
                        password=generate_password_hash("Cermak.2025", method='pbkdf2:sha256'),
                        role="muhendis",
                        created_at=datetime.now(timezone.utc)
                    ),
                    User(
                        username="guest_musteri",
                        password=generate_password_hash("guest_password", method='pbkdf2:sha256'),
                        role="musteri",
                        created_at=datetime.now(timezone.utc)
                    )
                ]
                db.session.add_all(users)
                db.session.commit()
                print("User tablosuna veriler eklendi.")
            else:
                print("User tablosu zaten dolu.")

            # 2. Permission
            if not Permission.query.first():
                admin_user = User.query.filter_by(username="admin1").first()
                if not admin_user:
                    raise ValueError("admin1 kullanıcısı bulunamadı!")
                servis_user = User.query.filter_by(username="servis1").first()
                if not servis_user:
                    raise ValueError("servis1 kullanıcısı bulunamadı!")
                muhendis_user = User.query.filter_by(username="muhendis1").first()
                if not muhendis_user:
                    raise ValueError("muhendis1 kullanıcısı bulunamadı!")
                musteri_user = User.query.filter_by(username="guest_musteri").first()
                if not musteri_user:
                    raise ValueError("guest_musteri kullanıcısı bulunamadı!")

                permissions = [
                    Permission(
                        user_id=admin_user.id,
                        can_view_parts=True, can_edit_parts=True, can_view_faults=True,
                        can_add_fault_solutions=True, can_view_catalogs=True, can_view_maintenance=True,
                        can_edit_maintenance=True, can_view_contact=True, can_view_purchase_prices=True,
                        can_view_warranty=True, can_view_accounting=True, can_view_periodic_maintenance=True
                    ),
                    Permission(
                        user_id=servis_user.id,
                        can_view_parts=True, can_view_faults=True, can_view_contact=True
                    ),
                    Permission(
                        user_id=muhendis_user.id,
                        can_view_parts=True, can_view_faults=True, can_add_fault_solutions=True,
                        can_view_catalogs=True, can_view_maintenance=True, can_view_contact=True,
                        can_view_warranty=True, can_view_accounting=True, can_view_periodic_maintenance=True
                    ),
                    Permission(
                        user_id=musteri_user.id,
                        can_view_parts=True, can_view_faults=True, can_view_contact=True
                    )
                ]
                db.session.add_all(permissions)
                db.session.commit()
                print("Permission tablosuna veriler eklendi.")
            else:
                print("Permission tablosu zaten dolu.")

            # 3. Part
            if not Part.query.first():
                parts = [
                    Part(part_code="PC001", name="Filtre", alternate_part_code="PC001-C", price_eur=10.0),
                    Part(part_code="PC002", name="Yağ Pompası", alternate_part_code="PC002-C", price_eur=20.0),
                    Part(part_code="119305-35150", name="Motor Yağ Filtresi", alternate_part_code="119305-35150-C", price_eur=14.0),
                    Part(part_code="Y129004-55801", name="Yakıt Filtresi", alternate_part_code="Y129004-55801-C", price_eur=15.0)
                ]
                db.session.add_all(parts)
                db.session.commit()
                print("Part tablosuna veriler eklendi.")
            else:
                print("Part tablosu zaten dolu.")

            # 4. Catalog
            if not Catalog.query.first():
                catalogs = [
                    Catalog(name="Ekskavatörler", slug="excavators"),
                    Catalog(name="TL Loader", slug="tl-loader")
                ]
                db.session.add_all(catalogs)
                db.session.commit()
                print("Catalog tablosuna veriler eklendi.")
            else:
                print("Catalog tablosu zaten dolu.")

            # 5. CatalogItem
            if not CatalogItem.query.first():
                excavators = Catalog.query.filter_by(slug="excavators").first()
                if not excavators:
                    raise ValueError("excavators kataloğu bulunamadı!")
                catalog_items = [
                    CatalogItem(
                        catalog_id=excavators.id,
                        name="TB215R",
                        motor_pdf_url="Uploads/motor_tb215r.pdf",
                        yedek_parca_pdf_url="Uploads/yedek_parca_tb215r.pdf",
                        operator_pdf_url="Uploads/operator_tb215r.pdf",
                        service_pdf_url="Uploads/service_tb215r.pdf"
                    ),
                    CatalogItem(
                        catalog_id=excavators.id,
                        name="TB260",
                        motor_pdf_url="Uploads/motor_tb260.pdf",
                        yedek_parca_pdf_url="Uploads/yedek_parca_tb260.pdf",
                        operator_pdf_url="Uploads/operator_tb260.pdf",
                        service_pdf_url="Uploads/service_tb260.pdf"
                    )
                ]
                db.session.add_all(catalog_items)
                db.session.commit()
                print("CatalogItem tablosuna veriler eklendi.")
            else:
                print("CatalogItem tablosu zaten dolu.")

            # 6. Fault
            if not Fault.query.first():
                tb215r = CatalogItem.query.filter_by(name="TB215R").first()
                if not tb215r:
                    raise ValueError("TB215R catalog_item bulunamadı!")
                admin_user = User.query.filter_by(username="admin1").first()
                if not admin_user:
                    raise ValueError("admin1 kullanıcısı bulunamadı!")
                faults = [
                    Fault(
                        catalog_item_id=tb215r.id,
                        fault_code="F001",
                        description="Hidrolstick hidrolik arıza",
                        solution="Hidrolik hortumu değiştirin.",
                        created_by=admin_user.id,
                        created_at=datetime.now(timezone.utc)
                    ),
                    Fault(
                        catalog_item_id=tb215r.id,
                        fault_code="F002",
                        description="Motor çalışmıyor",
                        solution="Aküyü kontrol edin.",
                        created_by=admin_user.id,
                        created_at=datetime.now(timezone.utc)
                    )
                ]
                db.session.add_all(faults)
                db.session.commit()
                print("Fault tablosuna veriler eklendi.")
            else:
                print("Fault tablosu zaten dolu.")

            # 7. FaultSolution
            if not FaultSolution.query.first():
                fault = Fault.query.filter_by(fault_code="F001").first()
                if not fault:
                    raise ValueError("F001 fault_code bulunamadı!")
                muhendis_user = User.query.filter_by(username="muhendis1").first()
                if not muhendis_user:
                    raise ValueError("muhendis1 kullanıcısı bulunamadı!")
                solutions = [
                    FaultSolution(
                        fault_id=fault.id,
                        solution="Hortum değiştirildi, sistem test edildi.",
                        created_by=muhendis_user.id,
                        created_at=datetime.now(timezone.utc)
                    )
                ]
                db.session.add_all(solutions)
                db.session.commit()
                print("FaultSolution tablosuna veriler eklendi.")
            else:
                print("FaultSolution tablosu zaten dolu.")

            # 8. FaultReport
            if not FaultReport.query.first():
                fault = Fault.query.filter_by(fault_code="F001").first()
                if not fault:
                    raise ValueError("F001 fault_code bulunamadı!")
                servis_user = User.query.filter_by(username="servis1").first()
                if not servis_user:
                    raise ValueError("servis1 kullanıcısı bulunamadı!")
                reports = [
                    FaultReport(
                        fault_id=fault.id,
                        report_description="Müşteri hidrolik arıza bildirdi.",
                        reported_by=servis_user.id,
                        reported_at=datetime.now(timezone.utc)
                    )
                ]
                db.session.add_all(reports)
                db.session.commit()
                print("FaultReport tablosuna veriler eklendi.")
            else:
                print("FaultReport tablosu zaten dolu.")

            # 9. Machine
            if not Machine.query.first():
                machines = [
                    Machine(
                        serial_number="SN12345",
                        model="TB215R",
                        owner_name="Ahmet Yılmaz",
                        address="İstanbul, Türkiye",
                        responsible_service="Servis1"
                    ),
                    Machine(
                        serial_number="SN67890",
                        model="TB260",
                        owner_name="Ayşe Demir",
                        address="Ankara, Türkiye",
                        responsible_service="Servis1"
                    )
                ]
                db.session.add_all(machines)
                db.session.commit()
                print("Machine tablosuna veriler eklendi.")
            else:
                print("Machine tablosu zaten dolu.")

            # 10. MaintenanceRecord
            if not MaintenanceRecord.query.first():
                tb215r = CatalogItem.query.filter_by(name="TB215R").first()
                if not tb215r:
                    raise ValueError("TB215R catalog_item bulunamadı!")
                records = [
                    MaintenanceRecord(
                        catalog_item_id=tb215r.id,
                        maintenance_date=datetime.now(timezone.utc),
                        description="Yağ değişimi yapıldı.",
                        invoice_file="Uploads/invoice_tb215r.pdf",
                        image_file="Uploads/image_tb215r.jpg"
                    )
                ]
                db.session.add_all(records)
                db.session.commit()
                print("MaintenanceRecord tablosuna veriler eklendi.")
            else:
                print("MaintenanceRecord tablosu zaten dolu.")

            # 11. MachineMaintenanceRecord
            if not MachineMaintenanceRecord.query.first():
                machine = Machine.query.filter_by(serial_number="SN12345").first()
                if not machine:
                    raise ValueError("SN12345 serial_number bulunamadı!")
                records = [
                    MachineMaintenanceRecord(
                        machine_id=machine.id,
                        action_type="Bakım",
                        action_date=datetime.now(timezone.utc),
                        description="Yağ ve filtre değişimi",
                        invoice_file="Uploads/invoice_sn12345.pdf",
                        part_image="Uploads/part_sn12345.jpg"
                    )
                ]
                db.session.add_all(records)
                db.session.commit()
                print("MachineMaintenanceRecord tablosuna veriler eklendi.")
            else:
                print("MachineMaintenanceRecord tablosu zaten dolu.")

            # 12. QRCode
            if not QRCode.query.first():
                machine = Machine.query.filter_by(serial_number="SN12345").first()
                if not machine:
                    raise ValueError("SN12345 serial_number bulunamadı!")
                qr_codes = [
                    QRCode(
                        qr_code_url="qrcodes/qr_1.png",
                        machine_id=machine.id,
                        is_used=True,
                        created_at=datetime.now(timezone.utc)
                    ),
                    QRCode(
                        qr_code_url="qrcodes/qr_2.png",
                        is_used=False,
                        created_at=datetime.now(timezone.utc)
                    )
                ]
                db.session.add_all(qr_codes)
                db.session.commit()
                print("QRCode tablosuna veriler eklendi.")
            else:
                print("QRCode tablosu zaten dolu.")

            # 13. Warranty section - Bu bölüm şu an aktif değil
            # Warranty tablosu kullanılmıyor, o yüzden atlıyoruz

            # 14. Invoice
            if not Invoice.query.first():
                machine = Machine.query.filter_by(serial_number="SN12345").first()
                if not machine:
                    raise ValueError("SN12345 serial_number bulunamadı!")
                maintenance_record = MachineMaintenanceRecord.query.filter_by(machine_id=machine.id).first()
                if not maintenance_record:
                    raise ValueError("MachineMaintenanceRecord kaydı bulunamadı!")
                admin_user = User.query.filter_by(username="admin1").first()
                if not admin_user:
                    raise ValueError("admin1 kullanıcısı bulunamadı!")
                invoices = [
                    Invoice(
                        invoice_number="INV001",
                        machine_id=machine.id,
                        service_id=maintenance_record.id,
                        amount_eur=150.0,
                        issue_date=datetime.now(timezone.utc),
                        document_url="Uploads/invoice_inv001.pdf",
                        description="Yağ değişimi faturası",
                        created_by=admin_user.id,
                        created_at=datetime.now(timezone.utc)
                    )
                ]
                db.session.add_all(invoices)
                db.session.commit()
                print("Invoice tablosuna veriler eklendi.")
            else:
                print("Invoice tablosu zaten dolu.")

            # 15. PeriodicMaintenance
            if not PeriodicMaintenance.query.first():
                # Excel dosyasını oku
                excel_path = r"C:\Users\rsade\Desktop\Yeni klasör (2)\InventoryTracker\periodic_maintenance_data.xlsx"
                df = pd.read_excel(excel_path)

                maintenance_data = []
                for _, row in df.iterrows():
                    maintenance_data.append(PeriodicMaintenance(
                        machine_model=str(row['machine_model']).strip(),
                        filter_name=str(row['filter_name']).strip(),
                        filter_part_code=str(row['part_code']).strip(),
                        alternate_part_code=str(row['alternate_part_code']).strip() if pd.notna(row['alternate_part_code']) else None,
                        original_price_eur=float(row['original_price']) if pd.notna(row['original_price']) else 0.0,
                        alternate_price_eur=float(row['alternate_price']) if pd.notna(row['alternate_price']) else 0.0,
                        maintenance_interval=str(row['maintenance_interval']).strip(),
                        created_by="admin1",
                        created_at=datetime.now(timezone.utc)
                    ))
                db.session.add_all(maintenance_data)
                db.session.commit()
                print("PeriodicMaintenance tablosuna veriler eklendi.")
            else:
                print("PeriodicMaintenance tablosu zaten dolu.")

            # 16. Offer
            if not Offer.query.first():
                admin_user = User.query.filter_by(username="admin1").first()
                if not admin_user:
                    raise ValueError("admin1 kullanıcısı bulunamadı!")
                offers = [
                    Offer(
                        offer_number="OFR001",
                        machine_model="TB215R",
                        maintenance_interval="500 Saatlik Bakım",
                        serial_number="SN12345",
                        filter_type="Yağ Filtresi",
                        customer_first_name="Ahmet",
                        customer_last_name="Yılmaz",
                        company_name="Yılmaz İnşaat",
                        phone="+905551234567",
                        offeror_name="Servis1",
                        labor_cost=50.0,
                        travel_cost=20.0,
                        total_amount=85.0,
                        discount_type="none",
                        discount_value=0.0,
                        status="Teklif Verildi",
                        invoice_number="INV001",
                        pdf_file_path="Uploads/offer_ofr001.pdf",
                        created_by=admin_user.id,
                        created_at=datetime.now(timezone.utc)
                    )
                ]
                db.session.add_all(offers)
                db.session.commit()
                print("Offer tablosuna veriler eklendi.")
            else:
                print("Offer tablosu zaten dolu.")
            
            # Bakım ayarlarını ekle
            if not MaintenanceReminderSettings.query.first():
                machine_types = ['TB215R', 'TB216', 'TB217R', 'TB235-2', 'TB240-2', 'TB260-2', 'TB290-2', 'TL8R-2']
                for machine_type in machine_types:
                    setting = MaintenanceReminderSettings(
                        machine_type=machine_type,
                        first_maintenance_hours=50 if machine_type in ['TB215R', 'TB216', 'TB217R'] else 250,
                        hours_interval=250,
                        is_active=True
                    )
                    db.session.add(setting)
                db.session.commit()
                print("MaintenanceReminderSettings tablosuna veriler eklendi.")

        except Exception as e:
            db.session.rollback()
            print(f"Veri ekleme hatası: {e}")

if __name__ == "__main__":
    print("Veritabanına örnek veriler ekleniyor...")
    populate_db()
    print("Veri ekleme işlemi tamamlandı.")