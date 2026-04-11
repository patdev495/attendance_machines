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
        print("--- Contents of EmployeeLocalRegistry ---")
        users = db.query(EmployeeLocalRegistry).all()
        for u in users:
            print(f"ID: {u.employee_id}, Name: {u.emp_name}, Source: {u.source_status}")
        print(f"Total: {len(users)}")
        
        print("\n--- Check with raw SQL ---")
        result = db.execute(text("SELECT employee_id, emp_name, source_status FROM EmployeeLocalRegistry")).all()
        for r in result:
            print(f"ID: {r[0]}, Name: {r[1]}, Source: {r[2]}")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_registry()
