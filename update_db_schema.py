from main import app
from database import db
from sqlalchemy import text
import logging
from datetime import datetime
import requests

# Logging ayarları
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_exchange_rate():
    try:
        response = requests.get('https://api.exchangerate-api.com/v4/latest/EUR')
        data = response.json()
        rate = data['rates']['TRY']
        logger.info(f'Güncel EUR döviz satış kuru alındı: {rate}')
        return rate
    except Exception as e:
        logger.error(f'Döviz kuru alınamadı: {str(e)}')
        return 43.9456  # Varsayılan kur

def update_schema():
    with app.app_context():
        try:
            # Yeni kolonları ekle
            new_columns = [
                # Arıza Çözüm Sistemi
                ('can_view_faults', 'BOOLEAN DEFAULT 0'),
                ('can_add_faults', 'BOOLEAN DEFAULT 0'),
                ('can_edit_faults', 'BOOLEAN DEFAULT 0'),
                ('can_delete_faults', 'BOOLEAN DEFAULT 0'),
                ('can_assign_faults', 'BOOLEAN DEFAULT 0'),
                ('can_resolve_faults', 'BOOLEAN DEFAULT 0'),
                ('can_add_fault_solutions', 'BOOLEAN DEFAULT 0'),
                ('can_view_fault_history', 'BOOLEAN DEFAULT 0'),
                ('can_manage_fault_categories', 'BOOLEAN DEFAULT 0'),
                ('can_export_fault_reports', 'BOOLEAN DEFAULT 0'),
                
                # Periyodik Bakım
                ('can_manage_periodic_maintenance', 'BOOLEAN DEFAULT 0'),
                ('can_view_periodic_maintenance', 'BOOLEAN DEFAULT 0'),
                
                # Teklif Yönetimi
                ('can_approve_offers', 'BOOLEAN DEFAULT 0'),
                ('can_reject_offers', 'BOOLEAN DEFAULT 0'),
                ('can_create_offers', 'BOOLEAN DEFAULT 0'),
                ('can_edit_offers', 'BOOLEAN DEFAULT 0'),
                ('can_delete_offers', 'BOOLEAN DEFAULT 0'),
                ('can_view_offers', 'BOOLEAN DEFAULT 0'),
                
                # Ekipman Yönetimi
                ('can_manage_equipment_status', 'BOOLEAN DEFAULT 0'),
                ('can_edit_equipment', 'BOOLEAN DEFAULT 0'),
                ('can_delete_equipment', 'BOOLEAN DEFAULT 0'),
                ('can_view_equipment', 'BOOLEAN DEFAULT 0')
            ]
            
            # Her bir kolonu kontrol et ve yoksa ekle
            for column_name, column_type in new_columns:
                try:
                    sql = f"ALTER TABLE permissions ADD COLUMN {column_name} {column_type}"
                    db.session.execute(text(sql))
                    print(f"Added column: {column_name}")
                except Exception as e:
                    if "duplicate column name" in str(e).lower():
                        print(f"Column {column_name} already exists")
                    else:
                        print(f"Error adding column {column_name}: {e}")

            # Varsayılan yetkileri güncelle
            update_sql = text("""
                UPDATE permissions
                SET can_view_faults = CASE
                        WHEN user_id IN (SELECT id FROM users WHERE role IN ('admin', 'muhendis', 'servis', 'musteri')) THEN 1
                        ELSE 0
                    END,
                    can_add_faults = CASE
                        WHEN user_id IN (SELECT id FROM users WHERE role IN ('admin', 'muhendis', 'servis', 'musteri')) THEN 1
                        ELSE 0
                    END,
                    can_edit_faults = CASE
                        WHEN user_id IN (SELECT id FROM users WHERE role IN ('admin', 'muhendis', 'servis')) THEN 1
                        ELSE 0
                    END,
                    can_delete_faults = CASE
                        WHEN user_id IN (SELECT id FROM users WHERE role = 'admin') THEN 1
                        ELSE 0
                    END,
                    can_assign_faults = CASE
                        WHEN user_id IN (SELECT id FROM users WHERE role IN ('admin', 'muhendis')) THEN 1
                        ELSE 0
                    END,
                    can_resolve_faults = CASE
                        WHEN user_id IN (SELECT id FROM users WHERE role IN ('admin', 'muhendis', 'servis')) THEN 1
                        ELSE 0
                    END,
                    can_add_fault_solutions = CASE
                        WHEN user_id IN (SELECT id FROM users WHERE role IN ('admin', 'muhendis', 'servis')) THEN 1
                        ELSE 0
                    END,
                    can_view_fault_history = CASE
                        WHEN user_id IN (SELECT id FROM users WHERE role IN ('admin', 'muhendis', 'servis', 'musteri')) THEN 1
                        ELSE 0
                    END,
                    can_manage_fault_categories = CASE
                        WHEN user_id IN (SELECT id FROM users WHERE role = 'admin') THEN 1
                        ELSE 0
                    END,
                    can_export_fault_reports = CASE
                        WHEN user_id IN (SELECT id FROM users WHERE role = 'admin') THEN 1
                        ELSE 0
                    END
            """)
            db.session.execute(update_sql)
            db.session.commit()
            print("Schema update completed successfully")
            
        except Exception as e:
            logger.error(f'Şema güncellenirken hata oluştu: {str(e)}')
            db.session.rollback()
            raise

if __name__ == '__main__':
    print('er starts')
    logger.info('Uygulama başlatılıyor...')
    update_schema() 