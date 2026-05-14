"""
migrate_to_sqlite.py — Copy real data from MSSQL to SQLite for Demo Deployment

This script connects to your local MSSQL servers (MIS and NY_VDS_DB), 
reads all the current real data, and saves it into the SQLite database (`demo_data/attendance.db`).
You only need to run this once before pushing to GitHub.
"""

import sys
import os
from pathlib import Path

# Disable DEMO_MODE so we can connect to MSSQL first
os.environ["DEMO_MODE"] = "false"

# Ensure the backend/src directory is on sys.path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
import pandas as pd
from config import config

def run_migration():
    print("=== STARTING MSSQL -> SQLITE DATA MIGRATION ===")
    
    # 1. Connect to Real MSSQL Databases
    print("1. Connecting to local MSSQL databases...")
    mssql_engine = create_engine(config.DATABASE_URL)
    mssql_meal_engine = create_engine(config.MEAL_DATABASE_URL)
    
    # 2. Connect to local SQLite Database
    sqlite_path = src_dir.parent.parent / "demo_data" / "attendance.db"
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    sqlite_url = f"sqlite:///{sqlite_path}"
    
    # Delete old sqlite db if exists to start fresh
    if sqlite_path.exists():
        sqlite_path.unlink()
        print(f"   [Deleted old {sqlite_path.name}]")
        
    sqlite_engine = create_engine(sqlite_url)
    
    # Initialize SQLite schema
    print("2. Initializing SQLite Schema...")
    os.environ["DEMO_MODE"] = "true"  # Trick database.py to create SQLite schema
    import database
    database.init_db()
    print("   [Schema Created]")
    
    from datetime import datetime, timedelta
    cutoff_date = datetime.now() - timedelta(days=30)
    
    print("\n3. Loading and Filtering Data (this might take a minute)...")
    
    # 3.1: Get Shift Definitions
    for table in ["ShiftRules", "ShiftDefinitions"]:
        try:
            print(f"   -> Copying {table}...")
            df = pd.read_sql_table(table, con=mssql_engine)
            df.to_sql(table, con=sqlite_engine, if_exists="append", index=False)
        except Exception as e:
            print(f"      [Skipped {table}: {e}]")
            
    # 3.2: Get Employees (Max 200)
    print("   -> Fetching and sampling 200 Employees...")
    emp_df = pd.read_sql_table("EmployeeLocalRegistry", con=mssql_engine)
    if len(emp_df) > 200:
        emp_df = emp_df.sample(200, random_state=42)
    demo_emp_ids = emp_df["employee_id"].astype(str).tolist()
    
    # SQLite strict date format parsing (YYYY-MM-DD) for SQLAlchemy
    if "start_date" in emp_df.columns:
        emp_df["start_date"] = pd.to_datetime(emp_df["start_date"]).dt.strftime('%Y-%m-%d')
        
    emp_df.to_sql("EmployeeLocalRegistry", con=sqlite_engine, if_exists="append", index=False)
    print(f"      [Copied {len(emp_df)} Employees]")
    
    # 3.3: Filter and Copy other tables
    tables_to_filter = [
        # (DB, Engine, Table, Emp ID Column)
        ("MIS", mssql_engine, "EmployeeMetadata", "employee_id"),
        ("MIS", mssql_engine, "EmployeeFingerprints", "employee_id"),
        ("MIS", mssql_engine, "EmployeeDailyShifts", "employee_id"),
        ("MIS", mssql_engine, "AttendanceLogs", "employee_id"),
        ("MIS", mssql_engine, "MealTrackingHistory", "employee_id"),
        ("NY_VDS_DB", mssql_meal_engine, "HR_MEAL_ORDER", "emp_no"),
        ("NY_VDS_DB", mssql_meal_engine, "HR_MEAL_PICKUP_LOG", "emp_no"),
    ]
    
    for db_name, engine, table, emp_col in tables_to_filter:
        print(f"   -> Copying {table} from {db_name} (filtered)...", end="", flush=True)
        try:
            # We construct a SQL query to filter at the DB level for efficiency
            if not demo_emp_ids:
                continue
                
            # Format IDs for SQL IN clause
            id_list_str = ",".join([f"'{eid}'" for eid in demo_emp_ids])
            
            query = f"SELECT * FROM {table} WHERE {emp_col} IN ({id_list_str})"
                
            df = pd.read_sql_query(query, con=engine)
            if df.empty:
                print(" [0 rows, skipped]")
                continue
            
            # SQLite strict date format parsing (YYYY-MM-DD) for SQLAlchemy
            for col in ["start_date", "work_date", "attendance_date", "order_date"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d')
                
            df.to_sql(table, con=sqlite_engine, if_exists="append", index=False)
            print(f" [Copied {len(df)} rows]")
        except Exception as e:
            if "not found" in str(e).lower() or "doesn't exist" in str(e).lower() or "invalid object name" in str(e).lower():
                 print(" [Table not found, skipped]")
            else:
                 print(f" [ERROR: {e}]")

    print("\n=== MIGRATION COMPLETE ===")
    print(f"Data saved to: {sqlite_path.resolve()}")
    print("You can now run `uv run python backend/src/main.py` with DEMO_MODE=true to use your REAL data!")

if __name__ == "__main__":
    run_migration()
