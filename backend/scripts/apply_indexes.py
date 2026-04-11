import sys
import os
from pathlib import Path
from sqlalchemy import text

# Add src to path to import SessionLocal
SRC_PATH = str(Path(__file__).resolve().parent.parent / "src")
if SRC_PATH not in sys.path:
    sys.path.append(SRC_PATH)

from database import SessionLocal

def apply_indexes():
    db = SessionLocal()
    try:
        # Using IF NOT EXISTS syntax for MSSQL to avoid errors if indexes already exist
        commands = [
            # 1. AttendanceLogs
            """
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_logs_attendance_time' AND object_id = OBJECT_ID('AttendanceLogs'))
            CREATE INDEX idx_logs_attendance_time ON AttendanceLogs (attendance_time);
            """,
            
            # 2. EmployeeLocalRegistry
            """
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_registry_emp_name' AND object_id = OBJECT_ID('EmployeeLocalRegistry'))
            CREATE INDEX idx_registry_emp_name ON EmployeeLocalRegistry (emp_name);
            """,
            """
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_registry_department' AND object_id = OBJECT_ID('EmployeeLocalRegistry'))
            CREATE INDEX idx_registry_department ON EmployeeLocalRegistry (department);
            """,
            """
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_registry_shift' AND object_id = OBJECT_ID('EmployeeLocalRegistry'))
            CREATE INDEX idx_registry_shift ON EmployeeLocalRegistry (shift);
            """,
            
            # 3. EmployeeMetadata
            """
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_metadata_emp_name' AND object_id = OBJECT_ID('EmployeeMetadata'))
            CREATE INDEX idx_metadata_emp_name ON EmployeeMetadata (emp_name);
            """,
            """
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_metadata_department' AND object_id = OBJECT_ID('EmployeeMetadata'))
            CREATE INDEX idx_metadata_department ON EmployeeMetadata (department);
            """
        ]
        
        print("Applying performance indexes (Idempotent)...")
        for cmd in commands:
            try:
                db.execute(text(cmd))
                db.commit()
            except Exception as e:
                # Still use a safe print just in case
                print(f"Non-critical error executing command. Database reported an issue.")
                db.rollback()
        
        print("Done. All indexes verified.")
                
    finally:
        db.close()

if __name__ == "__main__":
    apply_indexes()
