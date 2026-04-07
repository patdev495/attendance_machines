from sqlalchemy import create_engine, Column, Integer, String, Unicode, DateTime, Date, Time, Boolean, Float, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import config

# Using the connection string format from central config
engine = create_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ShiftRule(Base):
    __tablename__ = "ShiftRules"
    id = Column(Integer, primary_key=True, index=True)
    dept_keyword = Column(Unicode(255), nullable=True) # e.g. "Xưởng 1"
    shift_code = Column(String(10), nullable=False)   # e.g. "D" or "N"
    official_start = Column(Time, nullable=False)
    official_end = Column(Time, nullable=False)
    end_next_day = Column(Boolean, default=False)
    max_hours = Column(Float, nullable=True)
    standard_hours = Column(Float, default=8.0)
    deduct_break = Column(Boolean, default=True)
    has_overtime = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())

class AttendanceLog(Base):
    __tablename__ = "AttendanceLogs"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), nullable=False, index=True)
    attendance_date = Column(Date, nullable=False, index=True)
    attendance_time = Column(DateTime, nullable=False)
    machine_ip = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())

class EmployeeMetadata(Base):
    __tablename__ = "EmployeeMetadata"
    employee_id = Column(String(50), primary_key=True)
    emp_name = Column(Unicode(255), nullable=True)
    department = Column(Unicode(255), nullable=True)
    group = Column(Unicode(255), nullable=True)
    start_date = Column(Date, nullable=True)
    shift = Column(String(10), nullable=True)  # 'N' or 'D'
    status = Column(String(20), nullable=True) # 'Active' or 'TV'
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
