from main import app
from database import db
from models import Permission
from sqlalchemy import create_engine, text
from sqlalchemy.schema import CreateTable

def update_permission_table():
    with app.app_context():
        # Get the engine from the db session
        engine = db.get_engine()
        
        # Get the current table definition
        inspector = db.inspect(engine)
        existing_columns = {col['name'] for col in inspector.get_columns('permission')}
        
        # Get the desired table definition from the model
        desired_table = CreateTable(Permission.__table__)
        
        # Extract column definitions from the model
        model_columns = {col.name: col for col in Permission.__table__.columns}
        
        # Add missing columns
        for col_name, col in model_columns.items():
            if col_name not in existing_columns and col_name not in ['id', 'user_id']:
                col_type = col.type.compile(engine.dialect)
                nullable = "NULL" if col.nullable else "NOT NULL"
                default = f"DEFAULT {col.default.arg}" if col.default is not None else ""
                
                sql = f"ALTER TABLE permission ADD COLUMN {col_name} {col_type} {nullable} {default}"
                try:
                    with engine.connect() as conn:
                        conn.execute(text(sql))
                        conn.commit()
                    print(f"Added column: {col_name}")
                except Exception as e:
                    print(f"Error adding column {col_name}: {e}")
        
        print("Schema update completed")

if __name__ == '__main__':
    update_permission_table() 