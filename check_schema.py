import sqlite3

def check_permission_schema():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('PRAGMA table_info(permission)')
    columns = cursor.fetchall()
    
    print("Permission table columns:")
    for col in columns:
        print(f"Column {col[1]}: {col[2]}")
    
    conn.close()

if __name__ == '__main__':
    check_permission_schema() 