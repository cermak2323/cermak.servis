import sqlite3
import json
import os
from datetime import datetime

class Database:
    def __init__(self):
        self.db_path = 'parts_system.db'
        self.initialize()
    
    def initialize(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create parts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS parts (
                    part_code TEXT PRIMARY KEY,
                    name TEXT,
                    price_eur REAL,
                    last_updated DATETIME
                )
            ''')
            
            # Create search history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY,
                    part_code TEXT,
                    search_date DATETIME,
                    user TEXT
                )
            ''')
            
            # Create price history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY,
                    part_code TEXT,
                    price_eur REAL,
                    price_try REAL,
                    exchange_rate REAL,
                    date DATETIME
                )
            ''')
            
            conn.commit()
    
    def import_parts_from_json(self, json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                parts_data = json.load(f)
                
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for part in parts_data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO parts 
                        (part_code, name, price_eur, last_updated)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        part['Parça Kodu'],
                        part['Parça Adı'],
                        part['Geliş Fiyat (EUR)'],
                        datetime.now()
                    ))
                conn.commit()
            return True
        except Exception as e:
            print(f"Error importing parts: {e}")
            return False
    
    def save_search_history(self, part_code, user):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO search_history (part_code, search_date, user)
                VALUES (?, ?, ?)
            ''', (part_code, datetime.now(), user))
            conn.commit()
    
    def get_part_details(self, part_code):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM parts WHERE part_code = ?
            ''', (part_code,))
            return cursor.fetchone()
    
    def save_price_history(self, part_code, price_eur, price_try, exchange_rate):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO price_history 
                (part_code, price_eur, price_try, exchange_rate, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (part_code, price_eur, price_try, exchange_rate, datetime.now()))
            conn.commit()

def initialize_database():
    db = Database()
    if os.path.exists('parcalar.json'):
        db.import_parts_from_json('parcalar.json')
