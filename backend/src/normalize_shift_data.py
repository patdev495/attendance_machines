import sys
import os

# Add the current directory to sys.path to find database.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def normalize():
    updates = [
        "UPDATE ShiftDefinitions SET leave_hours_t = 0.0 WHERE leave_hours_t IS NULL",
        "UPDATE ShiftDefinitions SET leave_hours_c = 0.0 WHERE leave_hours_c IS NULL",
        "UPDATE ShiftDefinitions SET leave_hours_k = 0.0 WHERE leave_hours_k IS NULL",
        "UPDATE ShiftDefinitions SET workday_base = 8.0 WHERE workday_base IS NULL"
    ]
    
    with engine.connect() as conn:
        for stmt in updates:
            logger.info(f"Executing: {stmt}")
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception as e:
                logger.error(f"Error executing statement: {e}")
                
    logger.info("Data normalization complete.")

if __name__ == '__main__':
    normalize()
