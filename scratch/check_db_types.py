import os
import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from database import engine
from sqlalchemy import text

def check_types():
    with engine.connect() as conn:
        print("Checking column types for AttendanceLogs...")
        # MSSQL specific
        res = conn.execute(text("SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'AttendanceLogs' AND COLUMN_NAME = 'employee_id'"))
        for r in res:
            print(f"AttendanceLogs.employee_id: {r}")
            
        print("\nChecking column types for EmployeeLocalRegistry...")
        res = conn.execute(text("SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'EmployeeLocalRegistry' AND COLUMN_NAME = 'employee_id'"))
        for r in res:
            print(f"EmployeeLocalRegistry.employee_id: {r}")

        print("\nChecking a few actual values for spaces...")
        res = conn.execute(text("SELECT TOP 5 employee_id FROM AttendanceLogs"))
        for r in res:
            val = r[0]
            print(f"AL Value: '{val}' (len: {len(val)})")
            
        res = conn.execute(text("SELECT TOP 5 employee_id FROM EmployeeLocalRegistry"))
        for r in res:
            val = r[0]
            print(f"Reg Value: '{val}' (len: {len(val)})")

if __name__ == "__main__":
    check_types()
