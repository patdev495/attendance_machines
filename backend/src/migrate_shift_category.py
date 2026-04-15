from sqlalchemy import text
from database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    with engine.connect() as conn:
        # Check and Add shift_category to ShiftDefinitions
        stmt = "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('ShiftDefinitions') AND name = 'shift_category') ALTER TABLE ShiftDefinitions ADD shift_category NVARCHAR(50) NULL DEFAULT 'NORMAL'"
        
        logger.info(f"Executing: {stmt}")
        try:
            conn.execute(text(stmt))
            conn.commit()
            logger.info("Column shift_category added/verified in ShiftDefinitions.")
        except Exception as e:
            logger.error(f"Error executing statement: {e}")
                
    logger.info("Schema update (shift_category) complete.")

if __name__ == '__main__':
    migrate()
