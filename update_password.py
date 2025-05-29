from flask import Flask
from database import db
from models import User
from werkzeug.security import generate_password_hash
from config import Config

def update_admin_password():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    
    with app.app_context():
        admin = User.query.filter_by(username='admin1').first()
        if admin:
            new_password = 'Admin2024!'
            admin.password_hash = generate_password_hash(new_password)
            try:
                db.session.commit()
                print(f"Admin şifresi başarıyla güncellendi!")
                print(f"Kullanıcı adı: admin1")
                print(f"Yeni şifre: {new_password}")
            except Exception as e:
                db.session.rollback()
                print(f"Hata oluştu: {str(e)}")
        else:
            print("admin1 kullanıcısı bulunamadı!")

if __name__ == '__main__':
    update_admin_password() 