import sqlite3
import os

db_path = r"C:\Users\rsade\Desktop\Yeni klasör (3)\InventoryTracker\inventory_tracker.db"

def create_tables_manual():
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS permission (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        can_view_parts BOOLEAN DEFAULT FALSE,
        can_edit_parts BOOLEAN DEFAULT FALSE,
        can_view_faults BOOLEAN DEFAULT FALSE,
        can_add_solutions BOOLEAN DEFAULT FALSE,
        can_view_catalogs BOOLEAN DEFAULT FALSE,
        can_view_maintenance BOOLEAN DEFAULT FALSE,
        can_edit_maintenance BOOLEAN DEFAULT FALSE,
        can_view_contact BOOLEAN DEFAULT FALSE,
        can_view_purchase_prices BOOLEAN DEFAULT FALSE,
        can_view_warranty BOOLEAN DEFAULT FALSE,
        can_view_accounting BOOLEAN DEFAULT FALSE,
        can_view_periodic_maintenance BOOLEAN DEFAULT FALSE,
        can_view_admin_panel BOOLEAN DEFAULT FALSE,
        can_create_offers BOOLEAN DEFAULT FALSE,
        can_upload_excel BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (user_id) REFERENCES user(id)
    );
    
    CREATE TABLE IF NOT EXISTS announcement (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        FOREIGN KEY (created_by) REFERENCES user(id)
    );

    CREATE TABLE IF NOT EXISTS catalog (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS catalog_item (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        catalog_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        motor_pdf_url TEXT,
        yedek_parca_pdf_url TEXT,
        operator_pdf_url TEXT,
        service_pdf_url TEXT,
        FOREIGN KEY (catalog_id) REFERENCES catalog(id)
    );

    CREATE TABLE IF NOT EXISTS fault (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        catalog_item_id INTEGER NOT NULL,
        fault_code TEXT NOT NULL,
        description TEXT NOT NULL,
        solution TEXT,
        created_by INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (catalog_item_id) REFERENCES catalog_item(id),
        FOREIGN KEY (created_by) REFERENCES user(id)
    );

    CREATE TABLE IF NOT EXISTS fault_solution (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fault_id INTEGER NOT NULL,
        solution TEXT NOT NULL,
        created_by INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (fault_id) REFERENCES fault(id),
        FOREIGN KEY (created_by) REFERENCES user(id)
    );

    CREATE TABLE IF NOT EXISTS fault_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fault_id INTEGER NOT NULL,
        report_description TEXT NOT NULL,
        reported_by INTEGER NOT NULL,
        reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (fault_id) REFERENCES fault(id),
        FOREIGN KEY (reported_by) REFERENCES user(id)
    );

    CREATE TABLE IF NOT EXISTS machine (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        serial_number TEXT NOT NULL UNIQUE,
        model TEXT NOT NULL,
        owner_name TEXT NOT NULL,
        address TEXT NOT NULL,
        responsible_service TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS maintenance_record (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        catalog_item_id INTEGER NOT NULL,
        maintenance_date TIMESTAMP NOT NULL,
        description TEXT NOT NULL,
        invoice_file TEXT,
        image_file TEXT,
        FOREIGN KEY (catalog_item_id) REFERENCES catalog_item(id)
    );

    CREATE TABLE IF NOT EXISTS machine_maintenance_record (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id INTEGER NOT NULL,
        action_type TEXT NOT NULL,
        action_date TIMESTAMP NOT NULL,
        description TEXT NOT NULL,
        invoice_file TEXT,
        part_image TEXT,
        FOREIGN KEY (machine_id) REFERENCES machine(id)
    );

    CREATE TABLE IF NOT EXISTS qr_code (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        qr_code_url TEXT NOT NULL UNIQUE,
        machine_id INTEGER,
        is_used BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (machine_id) REFERENCES machine(id)
    );

    CREATE TABLE IF NOT EXISTS warranty (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id INTEGER NOT NULL,
        serial_number TEXT NOT NULL,
        start_date TIMESTAMP NOT NULL,
        end_date TIMESTAMP NOT NULL,
        description TEXT NOT NULL,
        document_url TEXT,
        created_by INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (machine_id) REFERENCES machine(id),
        FOREIGN KEY (created_by) REFERENCES user(id)
    );

    CREATE TABLE IF NOT EXISTS invoice (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT NOT NULL UNIQUE,
        machine_id INTEGER NOT NULL,
        service_id INTEGER NOT NULL,
        amount_eur REAL NOT NULL,
        issue_date TIMESTAMP NOT NULL,
        document_url TEXT,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'Onay Bekliyor',
        created_by INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (machine_id) REFERENCES machine(id),
        FOREIGN KEY (service_id) REFERENCES machine_maintenance_record(id),
        FOREIGN KEY (created_by) REFERENCES user(id)
    );

    CREATE TABLE IF NOT EXISTS invoice_approval (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        approved BOOLEAN DEFAULT FALSE,
        approved_at TIMESTAMP,
        comment TEXT,
        FOREIGN KEY (invoice_id) REFERENCES invoice(id),
        FOREIGN KEY (user_id) REFERENCES user(id)
    );

    CREATE TABLE IF NOT EXISTS periodic_maintenance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_model TEXT NOT NULL,
        filter_name TEXT NOT NULL,
        filter_part_code TEXT NOT NULL,
        alternate_part_code TEXT,
        original_price_eur REAL NOT NULL,
        alternate_price_eur REAL,
        maintenance_interval TEXT NOT NULL,
        created_by TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS offer (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        offer_number TEXT NOT NULL UNIQUE,
        machine_model TEXT NOT NULL,
        maintenance_interval TEXT NOT NULL,
        serial_number TEXT,
        filter_type TEXT,
        customer_first_name TEXT,
        customer_last_name TEXT,
        company_name TEXT,
        phone TEXT,
        offeror_name TEXT,
        labor_cost REAL,
        travel_cost REAL,
        total_amount REAL,
        discount_type TEXT,
        discount_value REAL,
        status TEXT,
        invoice_number TEXT,
        pdf_file_path TEXT,
        created_by INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES user(id)
    );
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_tables_manual()