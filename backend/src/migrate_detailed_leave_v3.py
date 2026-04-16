from sqlalchemy import text
from database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    columns = [
        ("leave_hours_t", "FLOAT DEFAULT 0.0"),
        ("leave_hours_c", "FLOAT DEFAULT 0.0"),
        ("leave_hours_k", "FLOAT DEFAULT 0.0"),
        ("workday_base", "FLOAT DEFAULT 8.0")
    ]
    
    with engine.connect() as conn:
        for col_name, col_type in columns:
            stmt = f"""
            IF NOT EXISTS (
                SELECT * FROM sys.columns 
                WHERE object_id = OBJECT_ID('ShiftDefinitions') 
                AND name = '{col_name}'
            )
            ALTER TABLE ShiftDefinitions ADD {col_name} {col_type}
            """
            logger.info(f"Checking/Adding column: {col_name}")
            try:
                conn.execute(text(stmt))
                conn.commit()
                logger.info(f"Finished check/add for {col_name}.")
            except Exception as e:
                logger.error(f"Error for column {col_name}: {e}")
                
    logger.info("Schema update (detailed leave & workday_base) complete.")

if __name__ == '__main__':
    migrate()
