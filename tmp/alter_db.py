from sqlalchemy import text
from db import SessionLocal

def alter_table():
    db = SessionLocal()
    try:
        # Add new columns (ignore errors if they already exist, by doing basic try-excepts or using IF NOT EXISTS)
        # SQL Server doesn't support IF NOT EXISTS in ALTER TABLE directly except via complex queries or newer versions.
        # So we just run them one by one.
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
