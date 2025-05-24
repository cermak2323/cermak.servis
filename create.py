from flask import Flask
from database import db
from models import *  # Tüm modellerinizi içe aktarın

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:/Users/rsade/Desktop/Yeni klasör (2)/InventoryTracker/inventory_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()  # Tüm tabloları oluşturur
    print("Tüm tablolar oluşturuldu.")