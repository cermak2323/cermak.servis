from database import db
from main import app
from sqlalchemy import text

# SQL sorguları
sql_commands = [
    # Önce mevcut yağları temizle
    "DELETE FROM oils",
    
    # Yeni yağları ekle
    """
    INSERT INTO oils (name, price_eur, created_at, updated_at)
    VALUES 
    ('CER DİŞLİ YAĞI', 6.0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('HİDROLİK YAĞI', 50.0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('MOTOR YAĞI 15W/40-4', 25.0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('MOTOR YAĞI 15W/40-5', 30.0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """
]

def add_oils():
    with app.app_context():
        for sql in sql_commands:
            db.session.execute(text(sql))
        db.session.commit()
        print("Yağlar başarıyla eklendi!")

if __name__ == "__main__":
    add_oils() 