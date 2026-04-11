import os
import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from database import SessionLocal, AttendanceLog, EmployeeLocalRegistry, EmployeeMetadata
from sqlalchemy import func

def check():
    db = SessionLocal()
    try:
        print("Checking first 5 AttendanceLogs...")
        logs = db.query(AttendanceLog.employee_id).limit(5).all()
        for l in logs:
            print(f"Log EmpID: '{l.employee_id}' (len: {len(l.employee_id)})")
            
        print("\nChecking matching Registry entries for those IDs...")
        for l in logs:
            reg = db.query(EmployeeLocalRegistry).filter(EmployeeLocalRegistry.employee_id == l.employee_id).first()
            if reg:
                print(f"Match found for '{l.employee_id}': '{reg.emp_name}'")
            else:
                # Try trim
                reg_trim = db.query(EmployeeLocalRegistry).filter(func.trim(EmployeeLocalRegistry.employee_id) == l.employee_id.strip()).first()
                if reg_trim:
                    print(f"Match found with TRIM for '{l.employee_id}': '{reg_trim.emp_name}'")
                else:
                    print(f"No match for '{l.employee_id}'")
                    
    finally:
        db.close()

if __name__ == "__main__":
    check()
