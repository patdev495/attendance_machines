from sqlalchemy import create_engine, Column, Integer, String, Unicode, DateTime, Date, Time, Boolean, Float, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import config

# Main Attendance Database Engine (MIS)
engine = create_engine(
    config.DATABASE_URL, 
    pool_pre_ping=True, 
    pool_recycle=3600,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Meal Tracking Database Engine (NY_VDS_DB)
meal_engine = create_engine(
    config.MEAL_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)
MealSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=meal_engine)

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
    attendance_time = Column(DateTime, nullable=False, index=True)
    machine_ip = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())

class EmployeeMetadata(Base):
    __tablename__ = "EmployeeMetadata"
    employee_id = Column(String(50), primary_key=True)
    emp_name = Column(Unicode(255), nullable=True, index=True)
    department = Column(Unicode(255), nullable=True, index=True)
    group = Column(Unicode(255), nullable=True)
    start_date = Column(Date, nullable=True)
    shift = Column(String(10), nullable=True)  # 'N' or 'D'
    status = Column(String(20), nullable=True) # 'Active' or 'TV'
    full_emp_id = Column(Unicode(50), nullable=True, index=True)
    privilege = Column(Integer, default=0) # 0=User, 14=Admin
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

class EmployeeFingerprint(Base):
    __tablename__ = "EmployeeFingerprints"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), nullable=False, index=True)
    template_id = Column(Integer, nullable=False) # 0-9
    template_data = Column(String, nullable=False) # Store as base64 string
    source_ip = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

# ──────────────────────────────────────────────────────────────────────────────
# v2.0 NEW TABLE — EmployeeLocalRegistry
# Unified employee registry that tracks employees from 3 sources:
#   excel_synced  → imported via Excel sync
#   machine_only  → found on a ZKTeco machine but not in Excel
#   log_only      → found only in AttendanceLogs (old logs, no machine/Excel match)
#
# IMPORTANT: existing tables (ShiftRules, AttendanceLogs, EmployeeMetadata,
# EmployeeFingerprints) are NOT modified. This is an additive-only change.
# ──────────────────────────────────────────────────────────────────────────────
class EmployeeLocalRegistry(Base):
    __tablename__ = "EmployeeLocalRegistry"
    employee_id  = Column(String(50), primary_key=True)
    emp_name     = Column(Unicode(255), nullable=True, index=True)
    department   = Column(Unicode(255), nullable=True, index=True)
    group_name   = Column(Unicode(255), nullable=True)   # "group" is a Python keyword
    start_date   = Column(Date, nullable=True)
    shift        = Column(String(10), nullable=True, index=True)     # 'D' or 'N'
    # source_status: 'excel_synced' | 'machine_only' | 'log_only'
    source_status = Column(String(20), nullable=False, default="log_only", index=True)
    full_emp_id   = Column(Unicode(50), nullable=True, index=True)
    privilege    = Column(Integer, default=0)         # 0=User, 14=Admin
    updated_at   = Column(DateTime, server_default=func.current_timestamp(),
                          onupdate=func.current_timestamp())

# ──────────────────────────────────────────────────────────────────────────────
# v3.0 NEW TABLE — EmployeeDailyShifts
# Stores per-employee, per-day shift codes imported from the monthly Excel grid.
# Codes include: N, D, P, O, T, C, R, 4N4R, 2R6N, 6P6N, etc.
#
# IMPORTANT: existing tables are NOT modified. This is an additive-only change.
# ──────────────────────────────────────────────────────────────────────────────
class EmployeeDailyShifts(Base):
    __tablename__ = "EmployeeDailyShifts"
    employee_id = Column(String(50), primary_key=True)
    work_date   = Column(Date, primary_key=True)
    shift_code  = Column(String(10), nullable=False)  # e.g. 'N', 'D', '4N4R', 'P', '6R6N'

# ──────────────────────────────────────────────────────────────────────────────
# v3.0 NEW TABLE — ShiftDefinitions
# Centralized dictionary for all attendance codes (N, D, P, R, 4N4P, etc.)
# Stores timing rules and payroll/leave logic per code.
# ──────────────────────────────────────────────────────────────────────────────
class ShiftDefinition(Base):
    __tablename__ = "ShiftDefinitions"
    shift_code      = Column(Unicode(50), primary_key=True)
    start_time      = Column(Time, nullable=True)
    end_time        = Column(Time, nullable=True)
    ot_start_time   = Column(Time, nullable=True) # Official start of OT (fallback to end_time)
    is_night_shift  = Column(Boolean, default=False)

    break_hours     = Column(Float, default=0.0)
    work_hours      = Column(Float, default=0.0)


    leave_hours_p   = Column(Float, default=0.0) # Paid Leave (NP)
    leave_hours_r   = Column(Float, default=0.0) # Personal Leave (VR)
    leave_hours_o   = Column(Float, default=0.0) # Other Leave (Om, BHXH...)
    leave_hours_t   = Column(Float, default=0.0) # Funeral Leave (Tang)
    leave_hours_c   = Column(Float, default=0.0) # Wedding Leave (Cuoi)
    leave_hours_k   = Column(Float, default=0.0) # Unexcused Leave (Khong phep)
    
    standard_hours  = Column(Float, default=0.0) # Rounding target (e.g. 8.0, 12.0)
    workday_base    = Column(Float, default=8.0) # Denominator for day calculations (4, 6, 8, 12)
    description     = Column(Unicode(255), nullable=True)
    # shift_category: 'NORMAL' | 'HOLIDAY' | 'ROTATION'
    # Added via migrate_shift_category.py — maps the existing DB column.
    shift_category  = Column(Unicode(50), nullable=True, default="NORMAL")


# ──────────────────────────────────────────────────────────────────────────────
# v4.0 NEW TABLE — MealTrackingHistory
# Stores history of meal verification swipes on canteen machines.
# ──────────────────────────────────────────────────────────────────────────────
class MealTrackingHistory(Base):
    __tablename__ = "MealTrackingHistory"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), nullable=False, index=True) # ID scanned (could be machine ID or EMP_NO)
    emp_name = Column(Unicode(255), nullable=True)
    department = Column(Unicode(255), nullable=True)
    meal_code = Column(String(50), nullable=True)
    meal_name = Column(Unicode(255), nullable=True)
    machine_ip = Column(String(50), nullable=False, index=True)
    swipe_time = Column(DateTime, nullable=False, index=True)
    is_registered = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())


def init_db():
    # create_all is additive — it only creates tables that do not yet exist.
    # Existing tables (ShiftRules, AttendanceLogs, EmployeeMetadata,
    # EmployeeFingerprints) are never altered.
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_meal_db():
    db = MealSessionLocal()
    try:
        yield db
    finally:
        db.close()
