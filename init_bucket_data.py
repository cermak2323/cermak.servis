from flask import Flask
from models import db, BucketType, BucketSize
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def init_bucket_data():
    with app.app_context():
        # Kova tiplerini ekle
        bucket_types = [
            {"name": "Yükleme", "description": "Standart yükleme kovası"},
            {"name": "Tesviye", "description": "Zemin tesviye kovası"},
            {"name": "Kanal", "description": "Kanal açma kovası"},
            {"name": "Tırmık", "description": "Standart tırmık kovası"},
            {"name": "Taş Tırmık", "description": "Taş toplama tırmık kovası"}
        ]

        for bucket_type in bucket_types:
            if not BucketType.query.filter_by(name=bucket_type["name"]).first():
                new_type = BucketType(
                    name=bucket_type["name"],
                    description=bucket_type["description"]
                )
                db.session.add(new_type)
        
        # Kova boyutlarını ekle
        bucket_sizes = [20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160]
        
        for size in bucket_sizes:
            if not BucketSize.query.filter_by(size=size).first():
                new_size = BucketSize(size=size)
                db.session.add(new_size)

        try:
            db.session.commit()
            print("Kova tipleri ve boyutları başarıyla eklendi!")
        except Exception as e:
            db.session.rollback()
            print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    init_bucket_data() 