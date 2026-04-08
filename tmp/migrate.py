from backend.src.database import engine
from sqlalchemy import text

def run_migration():
    print("Starting migration...")
    with engine.connect() as conn:
        # Add source_ip
        try:
            conn.execute(text("ALTER TABLE EmployeeFingerprints ADD source_ip NVARCHAR(50)"))
            print("Added source_ip column.")
        except Exception as e:
            if "already exists" in str(e).lower() or "Duplicate column name" in str(e) or "Column names in each table must be unique" in str(e):
                print("source_ip column already exists.")
            else:
                print(f"Error adding source_ip: {e}")
        
        # Add created_at
        try:
            conn.execute(text("ALTER TABLE EmployeeFingerprints ADD created_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
            print("Added created_at column.")
        except Exception as e:
            if "already exists" in str(e).lower() or "Duplicate column name" in str(e) or "Column names in each table must be unique" in str(e):
                print("created_at column already exists.")
            else:
                print(f"Error adding created_at: {e}")
        
        conn.commit()
    print("Migration complete.")

if __name__ == "__main__":
    run_migration()
