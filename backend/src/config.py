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
    # sys._MEIPASS is the path to the internal bundled files
    # Path(sys.executable).resolve().parent is the folder containing the .exe
    INTERNAL_DIR = Path(sys._MEIPASS).resolve()
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    # The application is running as a script
    INTERNAL_DIR = Path(__file__).resolve().parent.parent.parent
    BASE_DIR = INTERNAL_DIR

# Load .env from the backend directory
load_dotenv(BASE_DIR / "backend" / ".env")

class Config:
    # DB Settings
    DB_SERVER = os.getenv("DB_SERVER", "192.168.209.18")
    DB_NAME = os.getenv("DB_NAME", "MIS")
    DB_USER = os.getenv("DB_USER", "mis01")
    DB_PASS = os.getenv("DB_PASS", "mis01")
    DB_NAME_MEAL = os.getenv("DB_NAME_MEAL", "NY_VDS_DB")
    
    # Connection String Templates
    @property
    def DATABASE_URL(self):
        return f"mssql+pyodbc://{self.DB_USER}:{self.DB_PASS}@{self.DB_SERVER}/{self.DB_NAME}?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes&Encrypt=no"

    @property
    def MEAL_DATABASE_URL(self):
        return f"mssql+pyodbc://{self.DB_USER}:{self.DB_PASS}@{self.DB_SERVER}/{self.DB_NAME_MEAL}?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes&Encrypt=no"

    # Directory settings
    BACKEND_DIR = INTERNAL_DIR / "backend"
    STATIC_DIR = BACKEND_DIR / "static"
    LOGS_DIR = BACKEND_DIR / "logs"
    
    # Data Files (in Root, as requested)
    MACHINES_FILE = BASE_DIR / "machines.txt"
    EXCEL_FILE = BASE_DIR / "employee_work_shift.xlsx"

config = Config()
