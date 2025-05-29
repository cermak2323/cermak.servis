from flask import Flask
from models import db, Announcement
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def check_db_schema():
    with app.app_context():
        # Veritabanı bağlantısını kontrol et
        try:
            connection = db.engine.connect()
            print("Veritabanı bağlantısı başarılı!")
            
            # Announcement modelinin tablo adını ve sütunlarını göster
            print("\nAnnouncement tablosu bilgileri:")
            print(f"Tablo adı: {Announcement.__tablename__}")
            print("\nSütunlar:")
            for column in Announcement.__table__.columns:
                print(f"- {column.name}: {column.type}")
                
            # Veritabanındaki mevcut kayıtları kontrol et
            announcements = Announcement.query.all()
            print(f"\nToplam kayıt sayısı: {len(announcements)}")
            
        except Exception as e:
            print(f"Hata oluştu: {e}")
        finally:
            if 'connection' in locals():
                connection.close()

if __name__ == "__main__":
    check_db_schema() 