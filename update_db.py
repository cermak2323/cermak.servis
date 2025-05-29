import sqlite3
import os

def update_database():
    db_path = 'inventory_tracker.db'
    
    if not os.path.exists(db_path):
        print(f"Veritabanı bulunamadı: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # is_active alanını ekle
        cursor.execute("""
            ALTER TABLE announcement 
            ADD COLUMN is_active BOOLEAN DEFAULT 1
        """)
        
        conn.commit()
        print("Veritabanı başarıyla güncellendi!")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("is_active alanı zaten mevcut.")
        else:
            print(f"Hata oluştu: {e}")
    except Exception as e:
        print(f"Beklenmeyen bir hata oluştu: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    update_database() 