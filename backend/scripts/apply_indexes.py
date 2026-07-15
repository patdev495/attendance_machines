import sys
from pathlib import Path
from sqlalchemy import text

# Add src to path to import SessionLocal
SRC_PATH = str(Path(__file__).resolve().parent.parent / "src")
if SRC_PATH not in sys.path:
    sys.path.append(SRC_PATH)

from database import SessionLocal

MSSQL_INDEX_COMMANDS = [
    # AttendanceLogs: newest-log pagination and date-range browsing.
    """
    IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_logs_attendance_time' AND object_id = OBJECT_ID('AttendanceLogs'))
    CREATE INDEX idx_logs_attendance_time ON AttendanceLogs (attendance_time);
    """,
    # AttendanceLogs: Hanvon sync duplicate checks by Attendance Machine and day.
    """
    IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_attendance_logs_machine_date_employee_time' AND object_id = OBJECT_ID('AttendanceLogs'))
    CREATE INDEX idx_attendance_logs_machine_date_employee_time ON AttendanceLogs (machine_ip, attendance_date, employee_id, attendance_time);
    """,
    # EmployeeLocalRegistry
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
    # EmployeeMetadata
    """
    IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_metadata_emp_name' AND object_id = OBJECT_ID('EmployeeMetadata'))
    CREATE INDEX idx_metadata_emp_name ON EmployeeMetadata (emp_name);
    """,
    """
    IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_metadata_department' AND object_id = OBJECT_ID('EmployeeMetadata'))
    CREATE INDEX idx_metadata_department ON EmployeeMetadata (department);
    """,
]

SQLITE_INDEX_COMMANDS = [
    "CREATE INDEX IF NOT EXISTS idx_logs_attendance_time ON AttendanceLogs (attendance_time);",
    "CREATE INDEX IF NOT EXISTS idx_attendance_logs_machine_date_employee_time ON AttendanceLogs (machine_ip, attendance_date, employee_id, attendance_time);",
    "CREATE INDEX IF NOT EXISTS idx_registry_emp_name ON EmployeeLocalRegistry (emp_name);",
    "CREATE INDEX IF NOT EXISTS idx_registry_department ON EmployeeLocalRegistry (department);",
    "CREATE INDEX IF NOT EXISTS idx_registry_shift ON EmployeeLocalRegistry (shift);",
    "CREATE INDEX IF NOT EXISTS idx_metadata_emp_name ON EmployeeMetadata (emp_name);",
    "CREATE INDEX IF NOT EXISTS idx_metadata_department ON EmployeeMetadata (department);",
]


def index_commands_for_dialect(dialect_name: str) -> list[str]:
    if dialect_name == "sqlite":
        return SQLITE_INDEX_COMMANDS
    return MSSQL_INDEX_COMMANDS

def apply_indexes():
    db = SessionLocal()
    try:
        commands = index_commands_for_dialect(db.bind.dialect.name)
        
        print("Applying performance indexes (Idempotent)...")
        for cmd in commands:
            try:
                db.execute(text(cmd))
                db.commit()
            except Exception as e:
                error_text = str(e).encode("ascii", errors="replace").decode("ascii")
                print(f"Non-critical error executing index command: {error_text}")
                db.rollback()
        
        print("Done. Index commands processed.")
                
    finally:
        db.close()

if __name__ == "__main__":
    apply_indexes()
