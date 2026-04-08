import os
from pathlib import Path
from dotenv import load_dotenv

# d:/Workspace/Time_Attendance_Machine/backend/src/config.py
# .parent -> d:/Workspace/Time_Attendance_Machine/backend/src
# .parent.parent -> d:/Workspace/Time_Attendance_Machine/backend
# .parent.parent.parent -> d:/Workspace/Time_Attendance_Machine
import sys
if getattr(sys, 'frozen', False):
    # The application is running as a frozen executable
    # sys.executable is the path to the .exe file
    # We want BASE_DIR to be the folder containing the .exe
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    # The application is running as a script
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env from the backend directory
load_dotenv(BASE_DIR / "backend" / ".env")

class Config:
    # DB Settings
    DB_SERVER = os.getenv("DB_SERVER", "192.168.209.18")
    DB_NAME = os.getenv("DB_NAME", "MIS")
    DB_USER = os.getenv("DB_USER", "mis01")
    DB_PASS = os.getenv("DB_PASS", "mis01")
    
    # Connection String Template
    @property
    def DATABASE_URL(self):
        # We need to escape special characters if in connection string, but f-string is usually fine here
        return f"mssql+pyodbc://{self.DB_USER}:{self.DB_PASS}@{self.DB_SERVER}/{self.DB_NAME}?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"

    # Directory settings
    BACKEND_DIR = BASE_DIR / "backend"
    STATIC_DIR = BACKEND_DIR / "static"
    LOGS_DIR = BACKEND_DIR / "logs"
    
    # Data Files (in Root, as requested)
    MACHINES_FILE = BASE_DIR / "machines.txt"
    EXCEL_FILE = BASE_DIR / "employee_work_shift.xlsx"

config = Config()
