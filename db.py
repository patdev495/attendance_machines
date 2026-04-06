from sqlalchemy import create_engine, Column, Integer, String, DateTime, Date, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import urllib.parse

# MSSQL 2008 Connection Settings
DB_SERVER = "192.168.209.18"
DB_NAME = "MIS"
DB_USER = "mis01"
DB_PASS = "mis01"

# Using the connection string format provided by the user
DATABASE_URL = f"mssql+pyodbc://{DB_USER}:{DB_PASS}@{DB_SERVER}/{DB_NAME}?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AttendanceLog(Base):
    __tablename__ = "AttendanceLogs"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), nullable=False, index=True)
    attendance_date = Column(Date, nullable=False, index=True)
    attendance_time = Column(DateTime, nullable=False)
    machine_ip = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
