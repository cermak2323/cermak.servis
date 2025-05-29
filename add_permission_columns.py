import sqlite3
import os

def add_permission_columns():
    # Connect to the database
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # List of columns to add with their SQL definitions
    new_columns = [
        # Machine Management
        ('can_delete_machines', 'BOOLEAN DEFAULT 0'),
        ('can_export_machines', 'BOOLEAN DEFAULT 0'),
        
        # Maintenance Management
        ('can_delete_maintenance', 'BOOLEAN DEFAULT 0'),
        ('can_view_maintenance_history', 'BOOLEAN DEFAULT 0'),
        ('can_manage_maintenance_schedules', 'BOOLEAN DEFAULT 0'),
        
        # Equipment Management
        ('can_add_equipment', 'BOOLEAN DEFAULT 0'),
        ('can_edit_equipment', 'BOOLEAN DEFAULT 0'),
        ('can_delete_equipment', 'BOOLEAN DEFAULT 0'),
        ('can_manage_equipment_status', 'BOOLEAN DEFAULT 0'),
        
        # Parts and Catalog Management
        ('can_manage_catalogs', 'BOOLEAN DEFAULT 0'),
        
        # Fault Management
        ('can_add_faults', 'BOOLEAN DEFAULT 0'),
        ('can_edit_faults', 'BOOLEAN DEFAULT 0'),
        ('can_delete_faults', 'BOOLEAN DEFAULT 0'),
        
        # Offer Management
        ('can_edit_offers', 'BOOLEAN DEFAULT 0'),
        ('can_delete_offers', 'BOOLEAN DEFAULT 0'),
        
        # Warranty and Accounting
        ('can_manage_warranty', 'BOOLEAN DEFAULT 0'),
        ('can_manage_accounting', 'BOOLEAN DEFAULT 0'),
        
        # System Management
        ('can_manage_roles', 'BOOLEAN DEFAULT 0'),
        ('can_manage_system_settings', 'BOOLEAN DEFAULT 0'),
        ('can_view_logs', 'BOOLEAN DEFAULT 0'),
        
        # Reporting
        ('can_view_reports', 'BOOLEAN DEFAULT 0'),
        ('can_create_reports', 'BOOLEAN DEFAULT 0'),
        ('can_export_reports', 'BOOLEAN DEFAULT 0'),
        ('can_view_statistics', 'BOOLEAN DEFAULT 0'),
        
        # File Management
        ('can_delete_files', 'BOOLEAN DEFAULT 0'),
        
        # Communication and Notifications
        ('can_send_notifications', 'BOOLEAN DEFAULT 0'),
        ('can_manage_announcements', 'BOOLEAN DEFAULT 0')
    ]
    
    # Add each column
    for column_name, column_def in new_columns:
        try:
            cursor.execute(f'ALTER TABLE permission ADD COLUMN {column_name} {column_def}')
            print(f'Added column: {column_name}')
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e):
                print(f'Column {column_name} already exists')
            else:
                print(f'Error adding column {column_name}: {e}')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    print('Finished adding columns')

if __name__ == '__main__':
    add_permission_columns() 