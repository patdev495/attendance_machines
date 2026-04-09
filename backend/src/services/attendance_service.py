from typing import List, Dict, Any, Optional
from datetime import date
from sqlalchemy.orm import Session
from utils.stats_utils import compute_day_stats

class AttendanceService:
    @staticmethod
    def process_summary_rows(results: List[Any], rules_pool: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """
        Transform raw grouped SQLAlchemy rows into a list of summary dictionaries.
        Each row is expected to have: first_tap, last_tap, tap_count, work_date, shift, department.
        If rules_pool is not provided, it will be fetched once inside this function.
        """
        if rules_pool is None:
            from database import SessionLocal, ShiftRule
            db = SessionLocal()
            try:
                rules_pool = db.query(ShiftRule).all()
            finally:
                db.close()

        summary_items = []
        for row in results:
            first      = row.first_tap
            last       = row.last_tap
            count      = row.tap_count
            w_date     = row.work_date
            row_shift  = row.shift
            department = row.department

            work_hours       = 0.0
            minutes_late     = None
            minutes_early_lv = None
            note = ""

            if count > 1 and first != last:
                work_hours, _, _, minutes_late, minutes_early_lv = compute_day_stats(
                    first, last, w_date, department, row_shift, rules_pool=rules_pool
                )
            else:
                note = "Missing Check-in/out (Only 1 tap)"

            summary_items.append({
                "employee_id": row.employee_id,
                "attendance_date": w_date,
                "first_tap": first,
                "last_tap": last,
                "tap_count": count,
                "work_hours": work_hours,
                "shift": row_shift or "N/A",
                "status": row.status or "Active",
                "note": note,
                "minutes_late": minutes_late,
                "minutes_early_leave": minutes_early_lv,
            })
        return summary_items
