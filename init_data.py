from database import db
from models import MachineType, City, MachineModel

def init_machine_types():
    types = [
        {"name": "Mini Ekskavatör", "description": "0-8 ton arası mini ekskavatörler"},
        {"name": "Mini Yükleyici", "description": "Kompakt mini yükleyiciler"},
    ]
    
    type_map = {}  # To store type IDs for model initialization
    for type_data in types:
        machine_type = MachineType.query.filter_by(name=type_data["name"]).first()
        if not machine_type:
            machine_type = MachineType(**type_data)
            db.session.add(machine_type)
            db.session.flush()  # To get the ID
        type_map[machine_type.name] = machine_type.id
    
    return type_map

def init_machine_models(type_map):
    models = [
        # Mini Ekskavatör modelleri
        {"name": "TB215R", "machine_type_id": type_map["Mini Ekskavatör"], "description": "1.5 ton mini ekskavatör"},
        {"name": "TB216", "machine_type_id": type_map["Mini Ekskavatör"], "description": "1.6 ton mini ekskavatör"},
        {"name": "TB217R", "machine_type_id": type_map["Mini Ekskavatör"], "description": "1.7 ton mini ekskavatör"},
        {"name": "TB325R", "machine_type_id": type_map["Mini Ekskavatör"], "description": "2.5 ton mini ekskavatör"},
        {"name": "TB235-C", "machine_type_id": type_map["Mini Ekskavatör"], "description": "3.5 ton mini ekskavatör"},
        {"name": "TB240-C", "machine_type_id": type_map["Mini Ekskavatör"], "description": "4.0 ton mini ekskavatör"},
        {"name": "TB260-C", "machine_type_id": type_map["Mini Ekskavatör"], "description": "6.0 ton mini ekskavatör"},
        {"name": "TB290-C", "machine_type_id": type_map["Mini Ekskavatör"], "description": "9.0 ton mini ekskavatör"},
        
        # Mini Yükleyici modeli
        {"name": "TL8R2", "machine_type_id": type_map["Mini Yükleyici"], "description": "Kompakt mini yükleyici"},
    ]
    
    # Önce mevcut modelleri temizle
    MachineModel.query.delete()
    
    # Yeni modelleri ekle
    for model_data in models:
        machine_model = MachineModel(**model_data)
        db.session.add(machine_model)

TURKISH_CITIES = [
    'Adana', 'Adıyaman', 'Afyonkarahisar', 'Ağrı', 'Amasya', 'Ankara', 'Antalya', 'Artvin', 'Aydın', 'Balıkesir',
    'Bilecik', 'Bingöl', 'Bitlis', 'Bolu', 'Burdur', 'Bursa', 'Çanakkale', 'Çankırı', 'Çorum', 'Denizli',
    'Diyarbakır', 'Edirne', 'Elazığ', 'Erzincan', 'Erzurum', 'Eskişehir', 'Gaziantep', 'Giresun', 'Gümüşhane', 'Hakkari',
    'Hatay', 'Isparta', 'Mersin', 'İstanbul', 'İzmir', 'Kars', 'Kastamonu', 'Kayseri', 'Kırklareli', 'Kırşehir',
    'Kocaeli', 'Konya', 'Kütahya', 'Malatya', 'Manisa', 'Kahramanmaraş', 'Mardin', 'Muğla', 'Muş', 'Nevşehir',
    'Niğde', 'Ordu', 'Rize', 'Sakarya', 'Samsun', 'Siirt', 'Sinop', 'Sivas', 'Tekirdağ', 'Tokat',
    'Trabzon', 'Tunceli', 'Şanlıurfa', 'Uşak', 'Van', 'Yozgat', 'Zonguldak', 'Aksaray', 'Bayburt', 'Karaman',
    'Kırıkkale', 'Batman', 'Şırnak', 'Bartın', 'Ardahan', 'Iğdır', 'Yalova', 'Karabük', 'Kilis', 'Osmaniye',
    'Düzce'
]

def initialize_cities():
    # Check if cities already exist
    if City.query.count() > 0:
        print("Cities already exist in the database.")
        return

    # Add all Turkish cities
    for city_name in TURKISH_CITIES:
        city = City(name=city_name)
        db.session.add(city)
    
    try:
        db.session.commit()
        print("Successfully initialized cities.")
    except Exception as e:
        print(f"Error initializing cities: {str(e)}")
        db.session.rollback()

def initialize_data():
    # Önce mevcut verileri temizle
    MachineModel.query.delete()
    MachineType.query.delete()
    
    # Yeni verileri ekle
    type_map = init_machine_types()
    init_machine_models(type_map)
    initialize_cities()
    db.session.commit()

if __name__ == "__main__":
    from main import app
    with app.app_context():
        initialize_data()
        print("Başlangıç verileri başarıyla eklendi.") 