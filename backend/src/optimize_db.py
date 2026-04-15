import logging
from sqlalchemy import text
from database import SessionLocal, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB_OPTIMIZE")

def optimize():
    db = SessionLocal()
    try:
        # 1. Sanitize IDs in all tables (Critical if we remove LTRIM/RTRIM from Joins)
        logger.info("Sanitizing Employee IDs in all tables...")
        tables_to_clean = [
            "AttendanceLogs", 
            "EmployeeMetadata", 
            "EmployeeLocalRegistry", 
            "EmployeeDailyShifts", 
            "EmployeeFingerprints"
        ]
        
        for table in tables_to_clean:
            logger.info(f"Cleaning {table}...")
            # For MSSQL, we use LTRIM(RTRIM(...)) for updates
            db.execute(text(f"UPDATE {table} SET employee_id = LTRIM(RTRIM(employee_id))"))
        db.commit()

        # 2. Create Composite Indexes for Performance
        logger.info("Creating composite indexes...")
        
        # AttendanceLogs: Optimize date-range lookups and joins
        try:
            db.execute(text("""
                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_attendance_logs_lookup' AND object_id = OBJECT_ID('AttendanceLogs'))
                BEGIN
                    CREATE INDEX idx_attendance_logs_lookup ON AttendanceLogs (employee_id, attendance_date, attendance_time)
                END
            """))
            logger.info("Index idx_attendance_logs_lookup created/verified.")
        except Exception as e:
            logger.warning(f"Could not create idx_attendance_logs_lookup: {e}")

        # EmployeeDailyShifts: Optimize roster joins
        try:
            db.execute(text("""
                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_daily_shifts_lookup' AND object_id = OBJECT_ID('EmployeeDailyShifts'))
                BEGIN
                    CREATE INDEX idx_daily_shifts_lookup ON EmployeeDailyShifts (employee_id, work_date, shift_code)
                END
            """))
            logger.info("Index idx_daily_shifts_lookup created/verified.")
        except Exception as e:
            logger.warning(f"Could not create idx_daily_shifts_lookup: {e}")

        # EmployeeLocalRegistry: Optimize metadata retrieval and department filtering
        try:
            db.execute(text("""
                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_registry_lookup' AND object_id = OBJECT_ID('EmployeeLocalRegistry'))
                BEGIN
                    CREATE INDEX idx_registry_lookup ON EmployeeLocalRegistry (employee_id, shift, department)
                END
            """))
            logger.info("Index idx_registry_lookup created/verified.")
        except Exception as e:
            logger.warning(f"Could not create idx_registry_lookup: {e}")

        db.commit()
        logger.info("Database optimization complete.")

    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    optimize()
