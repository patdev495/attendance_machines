import os
import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from database import SessionLocal, EmployeeLocalRegistry
from sqlalchemy import text

def check_registry():
    db = SessionLocal()
    try:
        print("Checking for IDs 1, 2, 3, 4, 5...")
        target_ids = ['1', '2', '3', '4', '5']
        found = db.query(EmployeeLocalRegistry).filter(EmployeeLocalRegistry.employee_id.in_(target_ids)).all()
        for u in found:
            print(f"FOUND ID: {u.employee_id}, Source: {u.source_status}")
            
        total_count = db.query(EmployeeLocalRegistry).count()
        print(f"Total records in EmployeeLocalRegistry: {total_count}")
        
        machine_only_count = db.query(EmployeeLocalRegistry).filter(EmployeeLocalRegistry.source_status == 'machine_only').count()
        print(f"Total machine_only records: {machine_only_count}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_registry()
