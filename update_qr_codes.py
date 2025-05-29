from flask import Flask
from database import db
from models import Machine, QRCode
from config import Config
import os
import qrcode
from datetime import datetime, timezone
from werkzeug.utils import secure_filename

def update_qr_codes():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    
    # QR kod dizinlerini oluştur
    qr_code_folder = os.path.join('static', 'qrcodes')
    os.makedirs(qr_code_folder, exist_ok=True)
    
    with app.app_context():
        # Tüm makineleri al
        machines = Machine.query.all()
        
        for machine in machines:
            # Mevcut QR kodu kontrol et
            existing_qr = QRCode.query.filter_by(machine_id=machine.id, is_used=True).first()
            
            # QR kod içeriği - Makine sorgulama sayfasına yönlendir
            base_url = "https://cermakservis.onrender.com"  # Production URL
            qr_url = f"{base_url}/machines/machine-search?serial_number={machine.serial_number}"  # Seri numarasına göre arama yap
            
            # QR kod oluştur
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            # QR kodu resme dönüştür
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Dosya adı oluştur
            qr_filename = f"qr_code_{machine.serial_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            qr_path = os.path.join(qr_code_folder, secure_filename(qr_filename))
            
            try:
                # QR kodu kaydet
                img.save(qr_path)
                
                # Veritabanını güncelle
                if existing_qr:
                    # Eski QR kod dosyasını sil
                    old_qr_path = os.path.join('static', existing_qr.qr_code_url)
                    if os.path.exists(old_qr_path):
                        os.remove(old_qr_path)
                    
                    # QR kod URL'sini güncelle
                    existing_qr.qr_code_url = os.path.join('qrcodes', qr_filename).replace('\\', '/')
                else:
                    # Yeni QR kod kaydı oluştur
                    new_qr = QRCode(
                        qr_code_url=os.path.join('qrcodes', qr_filename).replace('\\', '/'),
                        machine_id=machine.id,
                        is_used=True,
                        created_at=datetime.now(timezone.utc)
                    )
                    db.session.add(new_qr)
                
                db.session.commit()
                print(f"QR kod güncellendi/oluşturuldu: {machine.serial_number}")
                print(f"QR URL: {qr_url}")
                
            except Exception as e:
                print(f"Hata oluştu ({machine.serial_number}): {str(e)}")
                db.session.rollback()

if __name__ == '__main__':
    update_qr_codes() 