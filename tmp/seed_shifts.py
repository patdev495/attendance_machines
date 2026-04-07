import sys
import os
from datetime import time

# Ensure we can import from backend.src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.src.database import SessionLocal, ShiftRule, engine, Base

def seed():
    # 1. Create table
    print("Creating ShiftRules table...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 2. Check if already seeded
        if db.query(ShiftRule).count() > 0:
            print("ShiftRules already seeded. Skipping.")
            return

        print("Seeding ShiftRules...")
        rules = [
            # Xuong 1 - Night (D)
            ShiftRule(
                dept_keyword="Xưởng 1", shift_code="D",
                official_start=time(20, 0), official_end=time(8, 0),
                end_next_day=True, max_hours=12.0, standard_hours=12.0,
                deduct_break=False, has_overtime=False
            ),
            # Xuong 1 - Day (N)
            ShiftRule(
                dept_keyword="Xưởng 1", shift_code="N",
                official_start=time(8, 0), official_end=time(20, 0),
                end_next_day=False, max_hours=12.0, standard_hours=12.0,
                deduct_break=False, has_overtime=False
            ),
            # Default - Night (D)
            ShiftRule(
                dept_keyword=None, shift_code="D",
                official_start=time(20, 0), official_end=time(5, 0),
                end_next_day=True, max_hours=None, standard_hours=8.0,
                deduct_break=True, has_overtime=True
            ),
            # Default - Day (N)
            ShiftRule(
                dept_keyword=None, shift_code="N",
                official_start=time(8, 0), official_end=time(17, 0),
                end_next_day=False, max_hours=None, standard_hours=8.0,
                deduct_break=True, has_overtime=True
            )
        ]
        db.add_all(rules)
        db.commit()
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
