import sys
import os
from pathlib import Path
from sqlalchemy import text

SRC_PATH = str(Path(__file__).resolve().parent.parent / "src")
if SRC_PATH not in sys.path:
    sys.path.append(SRC_PATH)
from database import SessionLocal

def alter_table():
    db = SessionLocal()
    try:
        commands = [
            "ALTER TABLE EmployeeMetadata ADD emp_name NVARCHAR(MAX);",
            "ALTER TABLE EmployeeMetadata ADD department NVARCHAR(MAX);",
            "ALTER TABLE EmployeeMetadata ADD [group] NVARCHAR(MAX);",
            "ALTER TABLE EmployeeMetadata ADD start_date DATE;"
        ]
        
        for cmd in commands:
            try:
                db.execute(text(cmd))
                db.commit()
                print(f"Executed: {cmd}")
            except Exception as e:
                print(f"Skipped (probably exists): {cmd}")
                db.rollback()
                
    finally:
        db.close()

if __name__ == "__main__":
    alter_table()
