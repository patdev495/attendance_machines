"""
seed_demo.py — Generate realistic demo data for the Time Attendance System.

Creates:
  - 200 employees across 8 departments
  - ShiftDefinitions (N, D, P, R, O, T, C, K, 4N4R, 6P6N, 2R6N)
  - 30 days of attendance logs (~2-4 taps/employee/day)
  - 30 days of daily shift assignments
  - Meal order data for canteen demo
  - Demo machines.txt

Idempotent: Only runs if the database has 0 employees.
"""

import random
import sys
import os
from datetime import date, datetime, timedelta, time
from pathlib import Path

# Ensure the backend/src directory is on sys.path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


# ── Vietnamese name data ──
LAST_NAMES = [
    "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ",
    "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Đinh", "Lâm",
    "Tạ", "Cao", "Trịnh", "Đoàn", "Tô", "Mai", "Châu", "Từ", "Quách", "Tăng",
]

MIDDLE_NAMES_MALE = [
    "Văn", "Hữu", "Đức", "Minh", "Quốc", "Thành", "Hoàng", "Trung",
    "Anh", "Tuấn", "Duy", "Bảo", "Đình", "Quang", "Tấn", "Xuân",
]

MIDDLE_NAMES_FEMALE = [
    "Thị", "Ngọc", "Thanh", "Hoàng", "Phương", "Bảo", "Minh", "Kim",
]

FIRST_NAMES_MALE = [
    "An", "Bình", "Cường", "Dũng", "Đạt", "Giang", "Hải", "Hiếu",
    "Hùng", "Khoa", "Khánh", "Long", "Minh", "Nam", "Nghĩa", "Phong",
    "Phú", "Quân", "Sơn", "Tài", "Thắng", "Thiện", "Toàn", "Trí",
    "Trung", "Tuấn", "Vinh", "Vũ", "Huy", "Đức", "Lộc", "Phát",
]

FIRST_NAMES_FEMALE = [
    "Anh", "Châu", "Diễm", "Dung", "Hà", "Hạnh", "Hương", "Lan",
    "Linh", "Mai", "Ngân", "Nhung", "Nhi", "Oanh", "Phương", "Quỳnh",
    "Thảo", "Thu", "Trang", "Trinh", "Vân", "Vy", "Yến", "Xuân",
    "Hồng", "Giang", "Thy", "Như", "Ngọc", "Thanh", "Trâm", "Huyền",
]

DEPARTMENTS = [
    "Xưởng 1", "Xưởng 2", "Xưởng 3",
    "QC", "Kho", "Hành chính", "Kỹ thuật", "IT",
]

GROUPS = {
    "Xưởng 1": ["Chuyền 1", "Chuyền 2", "Chuyền 3", "Chuyền 4"],
    "Xưởng 2": ["Chuyền A", "Chuyền B", "Chuyền C"],
    "Xưởng 3": ["Chuyền X", "Chuyền Y"],
    "QC": ["QC In", "QC Out", "IQC"],
    "Kho": ["Kho NVL", "Kho TP"],
    "Hành chính": ["HR", "Kế toán", "Lễ tân"],
    "Kỹ thuật": ["Bảo trì", "IE"],
    "IT": ["Dev", "Infra"],
}

DEMO_MACHINES = [
    {"ip": "10.0.0.11", "name": "Cổng chính"},
    {"ip": "10.0.0.12", "name": "Xưởng 1"},
    {"ip": "10.0.0.13", "name": "Xưởng 2"},
    {"ip": "10.0.0.14", "name": "Xưởng 3"},
    {"ip": "10.0.0.15", "name": "Canteen", "is_canteen": True},
]

MEAL_CODES = ["RICE", "NOODLE", "BREAD"]
MEAL_NAMES_VI = {"RICE": "Cơm", "NOODLE": "Phở", "BREAD": "Bánh mì"}
MEAL_NAMES_ZH = {"RICE": "米饭", "NOODLE": "粉面", "BREAD": "面包"}


def generate_vn_name():
    """Generate a realistic Vietnamese name."""
    is_male = random.random() > 0.45  # ~55% male
    last = random.choice(LAST_NAMES)
    if is_male:
        middle = random.choice(MIDDLE_NAMES_MALE)
        first = random.choice(FIRST_NAMES_MALE)
    else:
        middle = random.choice(MIDDLE_NAMES_FEMALE)
        first = random.choice(FIRST_NAMES_FEMALE)
    return f"{last} {middle} {first}"


def generate_shift_definitions():
    """Return a list of ShiftDefinition dicts matching the production schema."""
    return [
        {"shift_code": "N", "start_time": time(6, 0), "end_time": time(14, 0),
         "is_night_shift": False, "break_hours": 0.5, "work_hours": 8.0,
         "standard_hours": 8.0, "workday_base": 8.0, "shift_category": "NORMAL",
         "description": "Ca sáng 6:00 - 14:00"},
        {"shift_code": "D", "start_time": time(22, 0), "end_time": time(6, 0),
         "is_night_shift": True, "break_hours": 0.5, "work_hours": 8.0,
         "standard_hours": 8.0, "workday_base": 8.0, "shift_category": "NORMAL",
         "description": "Ca đêm 22:00 - 06:00"},
        {"shift_code": "P", "start_time": None, "end_time": None,
         "is_night_shift": False, "break_hours": 0.0, "work_hours": 0.0,
         "leave_hours_p": 8.0, "standard_hours": 8.0, "workday_base": 8.0,
         "shift_category": "NORMAL", "description": "Nghỉ phép"},
        {"shift_code": "R", "start_time": None, "end_time": None,
         "is_night_shift": False, "break_hours": 0.0, "work_hours": 0.0,
         "leave_hours_r": 8.0, "standard_hours": 8.0, "workday_base": 8.0,
         "shift_category": "NORMAL", "description": "Việc riêng"},
        {"shift_code": "O", "start_time": None, "end_time": None,
         "is_night_shift": False, "break_hours": 0.0, "work_hours": 0.0,
         "leave_hours_o": 8.0, "standard_hours": 8.0, "workday_base": 8.0,
         "shift_category": "NORMAL", "description": "Nghỉ ốm / BHXH"},
        {"shift_code": "T", "start_time": None, "end_time": None,
         "is_night_shift": False, "break_hours": 0.0, "work_hours": 0.0,
         "leave_hours_t": 8.0, "standard_hours": 8.0, "workday_base": 8.0,
         "shift_category": "NORMAL", "description": "Nghỉ tang"},
        {"shift_code": "C", "start_time": None, "end_time": None,
         "is_night_shift": False, "break_hours": 0.0, "work_hours": 0.0,
         "leave_hours_c": 8.0, "standard_hours": 8.0, "workday_base": 8.0,
         "shift_category": "NORMAL", "description": "Nghỉ cưới"},
        {"shift_code": "K", "start_time": None, "end_time": None,
         "is_night_shift": False, "break_hours": 0.0, "work_hours": 0.0,
         "leave_hours_k": 8.0, "standard_hours": 8.0, "workday_base": 8.0,
         "shift_category": "NORMAL", "description": "Không phép"},
        {"shift_code": "4N4R", "start_time": time(6, 0), "end_time": time(10, 0),
         "is_night_shift": False, "break_hours": 0.0, "work_hours": 4.0,
         "leave_hours_r": 4.0, "standard_hours": 8.0, "workday_base": 8.0,
         "shift_category": "NORMAL", "description": "4h sáng + 4h việc riêng"},
        {"shift_code": "6P6N", "start_time": time(6, 0), "end_time": time(12, 0),
         "is_night_shift": False, "break_hours": 0.0, "work_hours": 6.0,
         "leave_hours_p": 2.0, "standard_hours": 8.0, "workday_base": 8.0,
         "shift_category": "NORMAL", "description": "6h sáng + 2h phép"},
        {"shift_code": "2R6N", "start_time": time(8, 0), "end_time": time(14, 0),
         "is_night_shift": False, "break_hours": 0.0, "work_hours": 6.0,
         "leave_hours_r": 2.0, "standard_hours": 8.0, "workday_base": 8.0,
         "shift_category": "NORMAL", "description": "2h việc riêng + 6h sáng"},
        {"shift_code": "NA", "start_time": time(6, 0), "end_time": time(14, 0),
         "is_night_shift": False, "break_hours": 0.5, "work_hours": 8.0,
         "standard_hours": 8.0, "workday_base": 8.0, "shift_category": "NORMAL",
         "description": "Chưa phân ca"},
    ]


def seed_if_empty():
    """Seed demo data only if the DB is empty."""
    from database import SessionLocal, EmployeeLocalRegistry, AttendanceLog, ShiftDefinition, \
        EmployeeDailyShifts, EmployeeMetadata, MealTrackingHistory
    
    db = SessionLocal()
    try:
        count = db.query(EmployeeLocalRegistry).count()
        if count > 0:
            print(f"[SEED] Database already has {count} employees — skipping seed.")
            return
        
        print("[SEED] Empty database detected — seeding 200 employees + 30 days data...")
        
        # 1. Seed Shift Definitions
        existing_shifts = db.query(ShiftDefinition.shift_code).all()
        existing_shift_codes = {r[0] for r in existing_shifts}
        
        for sd in generate_shift_definitions():
            if sd["shift_code"] not in existing_shift_codes:
                obj = ShiftDefinition(**sd)
                db.add(obj)
        db.commit()
        print("[SEED] OK Shift definitions seeded")
        
        # 2. Generate 200 employees
        employees = []
        used_names = set()
        today = date.today()
        
        for i in range(200):
            emp_id = str(100 + i)
            
            # Generate unique name
            name = generate_vn_name()
            while name in used_names:
                name = generate_vn_name()
            used_names.add(name)
            
            dept = random.choice(DEPARTMENTS)
            group = random.choice(GROUPS[dept])
            shift = random.choice(["N", "N", "N", "D"])  # 75% day shift
            start_dt = today - timedelta(days=random.randint(30, 1800))
            full_id = f"NY{emp_id}"
            
            emp = EmployeeLocalRegistry(
                employee_id=emp_id,
                emp_name=name,
                department=dept,
                group_name=group,
                start_date=start_dt,
                shift=shift,
                source_status="excel_synced",
                full_emp_id=full_id,
                privilege=14 if i < 3 else 0,  # First 3 are admins
            )
            db.add(emp)
            
            # Also add to EmployeeMetadata for consistency
            meta = EmployeeMetadata(
                employee_id=emp_id,
                emp_name=name,
                department=dept,
                group=group,
                start_date=start_dt,
                shift=shift,
                status="Active",
                full_emp_id=full_id,
                privilege=14 if i < 3 else 0,
            )
            db.add(meta)
            
            employees.append({
                "id": emp_id, "name": name, "dept": dept,
                "group": group, "shift": shift, "full_id": full_id,
            })
        
        db.commit()
        print("[SEED] OK 200 employees seeded")
        
        # 3. Generate 30 days of attendance logs + daily shifts
        machine_ips = [m["ip"] for m in DEMO_MACHINES if not m.get("is_canteen")]
        canteen_ip = next(m["ip"] for m in DEMO_MACHINES if m.get("is_canteen"))
        
        log_count = 0
        shift_count = 0
        
        for day_offset in range(30):
            work_date = today - timedelta(days=29 - day_offset)
            is_weekend = work_date.weekday() >= 5  # Sat/Sun
            
            for emp in employees:
                # Determine daily shift code
                if is_weekend:
                    # 80% chance of day off on weekends
                    if random.random() < 0.80:
                        daily_shift = random.choice(["P", "R"])
                    else:
                        daily_shift = emp["shift"]  # OT on weekends
                else:
                    # 92% normal shift, 5% leave, 3% special
                    r = random.random()
                    if r < 0.92:
                        daily_shift = emp["shift"]
                    elif r < 0.97:
                        daily_shift = random.choice(["P", "R", "O"])
                    else:
                        daily_shift = random.choice(["4N4R", "6P6N", "2R6N"])
                
                # Save daily shift
                ds = EmployeeDailyShifts(
                    employee_id=emp["id"],
                    work_date=work_date,
                    shift_code=daily_shift,
                )
                db.add(ds)
                shift_count += 1
                
                # Generate attendance logs only for working shifts
                if daily_shift in ("P", "R", "O", "T", "C", "K"):
                    # Leave day — 10% chance of accidental tap
                    if random.random() < 0.10:
                        tap_time = datetime.combine(work_date, time(7, random.randint(0, 59)))
                        db.add(AttendanceLog(
                            employee_id=emp["id"],
                            attendance_date=work_date,
                            attendance_time=tap_time,
                            machine_ip=random.choice(machine_ips),
                        ))
                        log_count += 1
                    continue
                
                # Working day — generate check-in and check-out
                if daily_shift == "D":
                    # Night shift: check-in ~21:30-22:15, check-out ~05:30-06:30
                    ci_hour = 21 + (1 if random.random() > 0.5 else 0)
                    ci_min = random.randint(30, 59) if ci_hour == 21 else random.randint(0, 15)
                    check_in = datetime.combine(work_date, time(ci_hour, ci_min))
                    
                    co_hour = random.choice([5, 6])
                    co_min = random.randint(0, 30) if co_hour == 6 else random.randint(30, 59)
                    check_out = datetime.combine(work_date + timedelta(days=1), time(co_hour, co_min))
                elif daily_shift in ("4N4R", "6P6N", "2R6N"):
                    # Half-day shifts
                    ci_hour = 6 if "6" in daily_shift else 8
                    ci_min = random.randint(0, 10)
                    check_in = datetime.combine(work_date, time(ci_hour, ci_min))
                    
                    co_hour = ci_hour + (4 if "4N" in daily_shift else 6)
                    co_min = random.randint(0, 15)
                    check_out = datetime.combine(work_date, time(co_hour, co_min))
                else:
                    # Day shift (N): check-in ~5:40-6:15, check-out ~13:30-14:30
                    ci_hour = 5 if random.random() < 0.3 else 6
                    ci_min = random.randint(40, 59) if ci_hour == 5 else random.randint(0, 15)
                    check_in = datetime.combine(work_date, time(ci_hour, ci_min))
                    
                    # 15% chance of OT (check-out later)
                    has_ot = random.random() < 0.15
                    co_hour = random.choice([15, 16, 17]) if has_ot else random.choice([13, 14])
                    co_min = random.randint(0, 59) if has_ot else random.randint(30, 59) if co_hour == 13 else random.randint(0, 30)
                    check_out = datetime.combine(work_date, time(co_hour, co_min))
                
                # Add late arrivals (5% chance)
                if random.random() < 0.05 and daily_shift not in ("D",):
                    check_in = check_in + timedelta(minutes=random.randint(10, 45))
                
                # 3% chance of missing check-out (single tap)
                is_missing_out = random.random() < 0.03
                
                machine = random.choice(machine_ips)
                
                # Check-in log
                db.add(AttendanceLog(
                    employee_id=emp["id"],
                    attendance_date=check_in.date(),
                    attendance_time=check_in,
                    machine_ip=machine,
                ))
                log_count += 1
                
                # Check-out log (if not missing)
                if not is_missing_out:
                    db.add(AttendanceLog(
                        employee_id=emp["id"],
                        attendance_date=check_out.date(),
                        attendance_time=check_out,
                        machine_ip=machine,
                    ))
                    log_count += 1
                
                # Batch commit every ~2000 records
                if log_count % 2000 == 0:
                    db.commit()
        
        db.commit()
        print(f"[SEED] ✓ {log_count} attendance logs seeded")
        print(f"[SEED] ✓ {shift_count} daily shift assignments seeded")
        
        # 4. Seed meal order data (for canteen demo)
        meal_count = 0
        for day_offset in range(30):
            work_date = today - timedelta(days=29 - day_offset)
            mfg_day = work_date.strftime("%Y%m%d")
            is_weekend = work_date.weekday() >= 5
            
            if is_weekend:
                continue  # No meals on weekends
            
            for emp in employees:
                # 85% of employees register for meals on workdays
                if random.random() > 0.85:
                    continue
                
                meal_code = random.choice(MEAL_CODES)
                from database import Base
                # Use raw SQL insert since the model might not be available
                db.execute(
                    Base.metadata.tables["HR_MEAL_ORDER"].insert().values(
                        EMP_NO=emp["full_id"],
                        EMP_NAME=emp["name"],
                        DEPARTMENT=emp["dept"],
                        AREA="A",
                        MEAL_CODE=meal_code,
                        MEAL_NAME_VI=MEAL_NAMES_VI[meal_code],
                        MEAL_NAME_ZH=MEAL_NAMES_ZH[meal_code],
                        MFG_DAY=mfg_day,
                    )
                )
                meal_count += 1
                
                if meal_count % 1000 == 0:
                    db.commit()
        
        db.commit()
        print(f"[SEED] ✓ {meal_count} meal orders seeded")
        
        # 5. Write demo machines.txt
        from config import config
        machines_path = config.MACHINES_FILE
        with open(machines_path, "w") as f:
            for m in DEMO_MACHINES:
                line = m["ip"]
                tags = []
                if m.get("is_canteen"):
                    tags.append("canteen")
                tags.append("nolive")  # Don't try to connect to hardware in demo
                if tags:
                    line += " # " + " # ".join(tags)
                f.write(line + "\n")
        print(f"[SEED] ✓ machines.txt written ({len(DEMO_MACHINES)} machines)")
        
        print(f"[SEED] ═══ Seeding complete! ═══")
        print(f"[SEED]   Employees: 200")
        print(f"[SEED]   Logs: {log_count}")
        print(f"[SEED]   Daily Shifts: {shift_count}")
        print(f"[SEED]   Meal Orders: {meal_count}")
        
    except Exception as e:
        print(f"[SEED] ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    os.environ["DEMO_MODE"] = "true"
    seed_if_empty()
