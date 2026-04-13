from sqlalchemy import text
from database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    # Final Standardized Logic:
    # 1. Ensure full_emp_id exists. 
    # 2. If machine_id exists (from my previous mistake), we can rename or drop it.
    
    with engine.connect() as conn:
        # Check and Add full_emp_id
        statements = [
            "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('EmployeeMetadata') AND name = 'full_emp_id') ALTER TABLE EmployeeMetadata ADD full_emp_id NVARCHAR(50)",
            "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('EmployeeLocalRegistry') AND name = 'full_emp_id') ALTER TABLE EmployeeLocalRegistry ADD full_emp_id NVARCHAR(50)",
            # Cleanup previous temporary machine_id if it exists
            "IF EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('EmployeeMetadata') AND name = 'machine_id') ALTER TABLE EmployeeMetadata DROP COLUMN machine_id",
            "IF EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('EmployeeLocalRegistry') AND name = 'machine_id') ALTER TABLE EmployeeLocalRegistry DROP COLUMN machine_id"
        ]
        
        for stmt in statements:
            logger.info(f"Executing: {stmt}")
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception as e:
                logger.error(f"Error executing statement: {e}")
                
    logger.info("Schema update (full_emp_id) complete.")

if __name__ == '__main__':
    migrate()
