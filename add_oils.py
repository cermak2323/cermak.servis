from database import db
from models import Oil
from main import app

# Yağ listesi ve Euro fiyatları
oils = [
    {"name": "CER DİŞLİ YAĞI", "price_eur": 6.0},
    {"name": "HİDROLİK YAĞI", "price_eur": 50.0},
    {"name": "MOTOR YAĞI 15W/40-4", "price_eur": 25.0},
    {"name": "MOTOR YAĞI 15W/40-5", "price_eur": 30.0}
]

def add_oils():
    with app.app_context():
        # Mevcut yağları temizle
        Oil.query.delete()
        
        # Yeni yağları ekle
        for oil_data in oils:
            oil = Oil(name=oil_data["name"], price_eur=oil_data["price_eur"])
            db.session.add(oil)
        
        db.session.commit()
        print("Yağlar başarıyla eklendi!")

if __name__ == "__main__":
    add_oils() 