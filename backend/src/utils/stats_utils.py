from datetime import datetime, timedelta
from utils.shift_utils import get_shift_rules

def compute_day_stats(first, last, w_date, department, shift, rules_pool=None):
    """Return (work_hours, hours_standard, hours_ot, minutes_late, minutes_early)."""
    rules = get_shift_rules(department, shift, rules_pool=rules_pool)
    official_start_dt = datetime.combine(w_date, rules['official_start'])
    official_end_dt   = (datetime.combine(w_date + timedelta(days=1), rules['official_end'])
                         if rules['end_next_day']
                         else datetime.combine(w_date, rules['official_end']))

    # 1. Basic Stats: Late Arrival and Early Leave (relative to official window)
    minutes_late  = max(0, int((first - official_start_dt).total_seconds() / 60))
    minutes_early = max(0, int((official_end_dt - last).total_seconds() / 60))

    # 2. Total Work Hours Calculation (including 1h break deduction)
    # Total Duration = from actual in (clamped to start) to actual out
    effective_in  = max(first, official_start_dt)
    effective_out = last
    total_secs    = max(0.0, (effective_out - effective_in).total_seconds())

    if rules['deduct_break'] and total_secs > 3600:
        work_hours = round((total_secs - 3600) / 3600, 2)
    else:
        work_hours = round(total_secs / 3600, 2)

    # Apply cap if max_hours is set
    if rules['max_hours'] is not None:
        work_hours = min(work_hours, rules['max_hours'])

    # 3. Overtime (OT) Logic
    # New Rule: 12h shifts (Std=12) have 0 OT.
    # 8h shifts (Std=8) calculation OT = duration after official_end.
    is_12h = rules['standard_hours'] >= 12.0
    
    if rules['has_overtime'] and not is_12h:
        # OT is only counted if leaving AFTER the official end
        ot_secs = max(0, (last - official_end_dt).total_seconds())
        hours_ot = round(ot_secs / 3600, 2)
        
        # Standard hours is the remainder (capped by work_hours)
        hours_standard = max(0, round(work_hours - hours_ot, 2))
    else:
        # 12-hour shifts or shifts without OT
        hours_standard = work_hours
        hours_ot = 0.0

    return work_hours, hours_standard, hours_ot, minutes_late, minutes_early
