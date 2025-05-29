import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///cermak.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    # Base URL ayarı (production için gerçek domain adresini kullan)
    BASE_URL = os.environ.get('BASE_URL', 'https://cermakservis.onrender.com')
    
    # Proje kök dizini
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Dosya yükleme ayarları
    if os.environ.get('RENDER'):
        # Render.com için dosya yolları
        UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
        DOCUMENTS_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'documents')
        PHOTOS_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'photos')
        QR_CODES_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'qr_codes')
        QR_CODE_FOLDER = os.path.join(BASE_DIR, 'static', 'qrcodes')
    else:
        # Lokal geliştirme için
        UPLOAD_FOLDER = os.path.join('static', 'uploads')
        DOCUMENTS_FOLDER = os.path.join(UPLOAD_FOLDER, 'documents')
        PHOTOS_FOLDER = os.path.join(UPLOAD_FOLDER, 'photos')
        QR_CODES_FOLDER = os.path.join(UPLOAD_FOLDER, 'qr_codes')
        QR_CODE_FOLDER = os.path.join('static', 'qrcodes')
    
    # Klasörleri oluştur (sadece lokal geliştirme için)
    if not os.environ.get('RENDER'):
        for folder in [UPLOAD_FOLDER, DOCUMENTS_FOLDER, PHOTOS_FOLDER, QR_CODES_FOLDER, QR_CODE_FOLDER]:
            os.makedirs(folder, exist_ok=True)
    
    # İzin verilen dosya uzantıları
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    
    # SQLite veritabanı bağlantı URI'si
    if os.environ.get('RENDER'):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"
    
    # E-posta ayarları
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'your-email@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'your-app-password')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'your-email@gmail.com')