from flask import Flask
from database import db
from models import User, Permission
from werkzeug.security import generate_password_hash
from config import Config

def create_admin_user():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    
    with app.app_context():
        try:
            # Önce mevcut admin kullanıcısını ve yetkilerini sil
            admin = User.query.filter_by(username='admin1').first()
            if admin:
                # Önce yetkileri sil
                Permission.query.filter_by(user_id=admin.id).delete()
                db.session.commit()
                # Sonra kullanıcıyı sil
                db.session.delete(admin)
                db.session.commit()
            
            # Yeni admin kullanıcısı oluştur
            admin = User(
                username='admin1',
                password='Admin2024!',
                email='admin@example.com',
                role='admin'
            )
            
            # Önce kullanıcıyı kaydet
            db.session.add(admin)
            db.session.commit()
            
            # Sonra yetkilerini ver
            permissions = Permission(user_id=admin.id)
            for field in permissions.__dict__:
                if field.startswith('can_'):
                    setattr(permissions, field, True)
            
            db.session.add(permissions)
            db.session.commit()
            
            print("Yeni admin kullanıcısı başarıyla oluşturuldu!")
            print("Kullanıcı adı: admin1")
            print("Şifre: Admin2024!")
            print("Tüm yetkiler verildi.")
        except Exception as e:
            db.session.rollback()
            print(f"Hata oluştu: {str(e)}")

if __name__ == '__main__':
    create_admin_user() 