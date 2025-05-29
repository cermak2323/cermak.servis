from flask import Flask
from models import db, Announcement
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def recreate_database():
    with app.app_context():
        try:
            # Tüm tabloları sil ve yeniden oluştur
            db.drop_all()
            db.create_all()
            print("Veritabanı başarıyla yeniden oluşturuldu!")
            
        except Exception as e:
            print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    recreate_database() 