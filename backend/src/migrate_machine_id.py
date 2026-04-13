from sqlalchemy import text
from database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    alter_statements = [
        "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('EmployeeMetadata') AND name = 'machine_id') ALTER TABLE EmployeeMetadata ADD machine_id NVARCHAR(50)",
        "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('EmployeeLocalRegistry') AND name = 'machine_id') ALTER TABLE EmployeeLocalRegistry ADD machine_id NVARCHAR(50)"
    ]

    with engine.connect() as conn:
        for stmt in alter_statements:
            logger.info(f"Executing: {stmt}")
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception as e:
                logger.error(f"Error executing statement: {e}")
    logger.info("Schema update complete.")

if __name__ == '__main__':
    migrate()
