# Uygulama yapılandırma ayarlarını içeren sınıf
class Config:
    # Flask için gizli anahtar (güvenlik için rastgele bir değer kullanılmalı)
    SECRET_KEY = "46916e3cd93b553e938b0a9af309a961530c4b05a22f9b14"

    import os

    # Proje kök dizini
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # SQLite veritabanı bağlantı URI'si (dinamik yol)
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'inventory_tracker.db')}"

    # SQLAlchemy izleme özelliğini devre dışı bırak (performans için)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SQLite bağlantı havuzu ayarları
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30
    }

    # Dosya yükleme ve QR kod klasörleri
    UPLOAD_FOLDER = "static/uploads/"
    QR_CODE_FOLDER = "static/qrcodes/"

    # Flask-Mail yapılandırması
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'your-email@gmail.com'  # Kendi e-posta adresinizi girin
    MAIL_PASSWORD = 'your-app-password'  # Gmail için uygulama şifresi
    MAIL_DEFAULT_SENDER = 'your-email@gmail.com'  # Gönderici e-posta adresi