import sys
import os
from datetime import time

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, ShiftDefinition, init_db, engine

def seed_shifts():
    db = SessionLocal()
    try:
        print("Upserting shift definitions...")
        shifts_data = [
            {
                "shift_code": "N",
                "start_time": time(8, 0),
                "end_time": time(17, 0),
                "ot_start_time": None,
                "is_night_shift": False,
                "break_hours": 1.0,
                "work_hours": 8.0,
                "standard_hours": 8.0,
                "description": "Ca ngày 8h"
            },
            {
                "shift_code": "D",
                "start_time": time(20, 0),
                "end_time": time(5, 0),
                "ot_start_time": None,
                "is_night_shift": True,
                "break_hours": 1.0,
                "work_hours": 8.0,
                "standard_hours": 8.0,
                "description": "Ca đêm 8h"
            },
            {
                "shift_code": "N12",
                "start_time": time(8, 0),
                "end_time": time(20, 0),
                "ot_start_time": None,
                "is_night_shift": False,
                "break_hours": 1.0,
                "work_hours": 12.0,
                "standard_hours": 12.0,
                "description": "Ca ngày 12h"
            },
            {
                "shift_code": "D12",
                "start_time": time(20, 0),
                "end_time": time(8, 0),
                "ot_start_time": None,
                "is_night_shift": True,
                "break_hours": 1.0,
                "work_hours": 12.0,
                "standard_hours": 12.0,
                "description": "Ca đêm 12h"
            },
            {
                "shift_code": "4P4N",
                "start_time": time(8, 0),
                "end_time": time(12, 0),
                "ot_start_time": time(17, 0),
                "is_night_shift": False,
                "break_hours": 0.0, 
                "work_hours": 4.0,
                "leave_hours_p": 4.0,
                "standard_hours": 8.0,
                "description": "4h phép, 4h sáng (OT tính sau 17:00)"
            },
            {
                "shift_code": "6P6N",
                "start_time": time(8, 0),
                "end_time": time(20, 0),
                "ot_start_time": None,
                "is_night_shift": False,
                "break_hours": 0.0,
                "work_hours": 6.0,
                "leave_hours_p": 6.0,
                "standard_hours": 12.0,
                "description": "6h phép, 6h ngày (Ca 12h)"
            },
            {"shift_code": "P", "leave_hours_p": 8.0, "standard_hours": 8.0, "description": "Nghỉ phép (8h)"},
            {"shift_code": "R", "leave_hours_r": 8.0, "standard_hours": 8.0, "description": "Việc riêng (8h)"},
            {"shift_code": "O", "leave_hours_o": 8.0, "standard_hours": 8.0, "description": "Nghỉ ốm/BHXH (8h)"},
        ]
        
        for data in shifts_data:
            shift = db.query(ShiftDefinition).filter(ShiftDefinition.shift_code == data["shift_code"]).first()
            if not shift:
                shift = ShiftDefinition(shift_code=data["shift_code"])
                db.add(shift)
            
            for key, value in data.items():
                setattr(shift, key, value)
        
        db.commit()
        print(f"Successfully updated/merged {len(shifts_data)} shift definitions.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_shifts()
