import re
from datetime import datetime, timedelta, time
from typing import Optional, List, Any

# ── Full-day leave/absence codes (Legacy fallback) ──────────────────────────
# These are used if the code is not found in the ShiftDefinitions table.
FULL_DAY_LEAVE_CODES = {'P', 'O', 'T', 'C', 'R', 'K', 'X'}

def parse_shift_window(shift_code, department, rules_pool: Optional[List[Any]] = None):
    """
    Parse a daily shift code into an effective work window using the 
    ShiftDefinitions table (passed via rules_pool).
    """
    code = (shift_code or 'N').strip().upper()

    # Find the rule in the pool (rules_pool is now List[ShiftDefinition])
    matching_rule = None
    if rules_pool:
        matching_rule = next((r for r in rules_pool if r.shift_code == code), None)

    if matching_rule:
        return {
            'is_leave': matching_rule.leave_hours_p > 0 or matching_rule.leave_hours_r > 0 or matching_rule.leave_hours_o > 0,
            'leave_hours_p': matching_rule.leave_hours_p,
            'leave_hours_r': matching_rule.leave_hours_r,
            'leave_hours_o': matching_rule.leave_hours_o,
            'official_start': matching_rule.start_time or time(8, 0),
            'official_end': matching_rule.end_time or time(17, 0),
            'ot_start_time': matching_rule.ot_start_time,
            'end_next_day': matching_rule.is_night_shift,
            'work_hours_expected': matching_rule.work_hours,

            'break_hours': matching_rule.break_hours,
            'has_overtime': True, # Overtime is allowed for all defined shifts unless capped
            'max_hours': None,
            'standard_hours': matching_rule.standard_hours,
        }

    # ── Fallback logic for undefined codes ──
    is_leave = code in FULL_DAY_LEAVE_CODES
    return {
        'is_leave': is_leave,
        'leave_hours_p': 8.0 if code == 'P' else 0.0,
        'leave_hours_r': 8.0 if code == 'R' else 0.0,
        'leave_hours_o': 8.0 if code in ('O', 'T', 'C') else 0.0,
        'official_start': time(8, 0),
        'official_end': time(17, 0),
        'end_next_day': code == 'D', # Legacy D was overnight
        'work_hours_expected': 0.0 if is_leave else 8.0,
        'break_hours': 1.0 if not is_leave else 0.0,
        'has_overtime': not is_leave,
        'max_hours': None,
        'standard_hours': 0.0 if is_leave else 8.0,
    }


def compute_day_stats(first, last, w_date, department, shift_code, rules_pool=None):
    """
    Return (work_hours, hours_standard, hours_ot, minutes_late, minutes_early, hours_p, hours_r, hours_o).
    """
    window = parse_shift_window(shift_code, department, rules_pool=rules_pool)

    # Values for the day
    hours_p = window.get('leave_hours_p', 0.0)
    hours_r = window.get('leave_hours_r', 0.0)
    hours_o = window.get('leave_hours_o', 0.0)

    # ── Full-day leave: return leave hours and zeros for work ─────────────────
    if first == last and window['is_leave']:
        return 0.0, 0.0, 0.0, 0, 0, hours_p, hours_r, hours_o

    # ── Build effective datetime window ──────────────────────────────────────
    official_start_dt = datetime.combine(w_date, window['official_start'])
    if window['end_next_day']:
        official_end_dt = datetime.combine(w_date + timedelta(days=1), window['official_end'])
    else:
        official_end_dt = datetime.combine(w_date, window['official_end'])

    # 1. Late / Early
    minutes_late  = max(0, int((first - official_start_dt).total_seconds() / 60))
    minutes_early = max(0, int((official_end_dt - last).total_seconds() / 60))

    # 2. Work hours
    effective_in  = max(first, official_start_dt)
    effective_out = last
    total_secs    = max(0.0, (effective_out - effective_in).total_seconds())

    # Break Deduction (Simplified blanket deduction based on user feedback)
    break_secs = window.get('break_hours', 0.0) * 3600.0
    raw_work_hours = (total_secs - break_secs) / 3600.0
    if raw_work_hours < 0: raw_work_hours = 0.0

    # 3. OT logic - Use custom OT anchor if provided, otherwise fallback to official_end
    if window.get('ot_start_time'):
        if window['end_next_day']:
            actual_ot_threshold = datetime.combine(w_date + timedelta(days=1), window['ot_start_time'])
        else:
            actual_ot_threshold = datetime.combine(w_date, window['ot_start_time'])
    else:
        actual_ot_threshold = official_end_dt
    
    if last > actual_ot_threshold:
        ot_secs = (last - actual_ot_threshold).total_seconds()
    else:
        ot_secs = 0.0


    hours_ot = round(ot_secs / 3600.0, 2)
    
    # Standard hours
    raw_std_hours = max(0.0, raw_work_hours - (ot_secs / 3600.0))

    # Cap standard hours at the expected duration
    raw_std_hours = min(raw_std_hours, float(window['work_hours_expected']))

    # Final Rounding
    work_hours = round(raw_work_hours, 2)
    hours_standard = round(raw_std_hours, 2)
    
    # Protection Rule: If neither late nor early, force standard hours to expected
    if minutes_late == 0 and minutes_early <= 5: 
        hours_standard = float(window['work_hours_expected'])

    return work_hours, hours_standard, hours_ot, minutes_late, minutes_early, hours_p, hours_r, hours_o
