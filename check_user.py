from flask import Flask
from database import db
from models import User
from config import Config
import sqlite3

def check_database():
    # SQLite veritabanını doğrudan kontrol et
    try:
        conn = sqlite3.connect('cermak.db')
        cursor = conn.cursor()
        
        # Tablo yapısını kontrol et
        cursor.execute("SELECT * FROM sqlite_master WHERE type='table' AND name='users'")
        table_info = cursor.fetchone()
        if table_info:
            print("Users tablosu yapısı:")
            print(table_info[4])  # CREATE TABLE statement
        
        # Kullanıcıları listele
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        print("\nKullanıcı listesi:")
        for user in users:
            print(f"ID: {user[0]}")
            print(f"Username: {user[1]}")
            print(f"Email: {user[2]}")
            print(f"Password field: {user[3]}")
            print(f"Role: {user[4]}")
            print("-" * 50)
        
        conn.close()
    except Exception as e:
        print(f"SQLite hatası: {str(e)}")

    # Flask-SQLAlchemy ile kontrol et
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    
    with app.app_context():
        print("\nFlask-SQLAlchemy ile kullanıcı kontrolü:")
        admin = User.query.filter_by(username='admin1').first()
        if admin:
            print(f"Kullanıcı bulundu:")
            print(f"ID: {admin.id}")
            print(f"Username: {admin.username}")
            print(f"Email: {admin.email}")
            print(f"Password field: {admin.password if hasattr(admin, 'password') else 'password_hash' if hasattr(admin, 'password_hash') else 'not found'}")
            print(f"Role: {admin.role}")
        else:
            print("admin1 kullanıcısı bulunamadı!")

if __name__ == '__main__':
    check_database() 