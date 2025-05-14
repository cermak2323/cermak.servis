import os

class Config:
    SECRET_KEY = "46916e3cd93b553e938b0a9af309a961530c4b05a22f9b14"
    
    # Proje kök dizini
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # SQLite veritabanı bağlantı URI'si (migrations klasörüyle aynı seviyede)
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'inventory_tracker.db').replace(os.sep, '/')}"
    
    # Dosya yükleme klasörleri
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads').replace(os.sep, '/')
    QR_CODE_FOLDER = os.path.join(BASE_DIR, 'static', 'qrcodes').replace(os.sep, '/')
    
    # SQLAlchemy ayarları
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # E-posta ayarları
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'your-email@gmail.com'
    MAIL_PASSWORD = 'your-app-password'
    MAIL_DEFAULT_SENDER = 'your-email@gmail.com'