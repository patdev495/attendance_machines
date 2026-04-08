from datetime import datetime, timedelta
from .shift_utils import get_shift_rules

def compute_day_stats(first, last, w_date, department, shift, rules_pool=None):
    """Return (work_hours, hours_standard, hours_ot, minutes_late, minutes_early)."""
    rules = get_shift_rules(department, shift, rules_pool=rules_pool)
    official_start_dt = datetime.combine(w_date, rules['official_start'])
    official_end_dt   = (datetime.combine(w_date + timedelta(days=1), rules['official_end'])
                         if rules['end_next_day']
                         else datetime.combine(w_date, rules['official_end']))

    minutes_late  = max(0, int((first - official_start_dt).total_seconds() / 60))
    minutes_early = max(0, int((official_end_dt - last).total_seconds() / 60))

    effective_in  = max(first, official_start_dt)
    effective_out = min(last, official_end_dt) if not rules['has_overtime'] else last
    total_secs    = max(0.0, (effective_out - effective_in).total_seconds())

    if rules['deduct_break']:
        work_hours = round((total_secs - 3600) / 3600, 2) if total_secs > 3600 else round(total_secs / 3600, 2)
    else:
        work_hours = round(total_secs / 3600, 2)

    if rules['max_hours'] is not None:
        work_hours = min(work_hours, rules['max_hours'])

    if rules['has_overtime'] and work_hours >= rules['standard_hours']:
        hours_standard = rules['standard_hours']
        hours_ot       = round(work_hours - rules['standard_hours'], 2)
    else:
        hours_standard = work_hours
        hours_ot       = 0.0

    return work_hours, hours_standard, hours_ot, minutes_late, minutes_early
