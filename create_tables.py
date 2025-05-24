from main import app
from database import db
from models import User, Permission, Announcement, Catalog, CatalogItem, Fault, FaultSolution, FaultReport
from models import Machine, MaintenanceRecord, MachineMaintenanceRecord, QRCode, PeriodicMaintenance
from models import Oil, Offer, MaintenanceReminder, MaintenanceReminderSettings, MachineType, City

def create_tables():
    with app.app_context():
        # Tüm tabloları oluştur
        db.create_all()
        print("Veritabanı tabloları başarıyla oluşturuldu.")

if __name__ == "__main__":
    create_tables()