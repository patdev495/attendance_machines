from datetime import datetime, timedelta, time
from typing import Optional, List, Any
import math


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
            'is_leave': (matching_rule.leave_hours_p > 0 or matching_rule.leave_hours_r > 0 or 
                        matching_rule.leave_hours_o > 0 or matching_rule.leave_hours_t > 0 or 
                        matching_rule.leave_hours_c > 0 or matching_rule.leave_hours_k > 0),
            'leave_hours_p': matching_rule.leave_hours_p,
            'leave_hours_r': matching_rule.leave_hours_r,
            'leave_hours_o': matching_rule.leave_hours_o,
            'leave_hours_t': matching_rule.leave_hours_t,
            'leave_hours_c': matching_rule.leave_hours_c,
            'leave_hours_k': matching_rule.leave_hours_k,
            'official_start': matching_rule.start_time or time(8, 0),
            'official_end': matching_rule.end_time or time(17, 0),
            'ot_start_time': matching_rule.ot_start_time,
            'end_next_day': matching_rule.is_night_shift,
            'work_hours_expected': matching_rule.work_hours,

            'break_hours': matching_rule.break_hours,
            'has_overtime': True, 
            'max_hours': None,
            'standard_hours': matching_rule.standard_hours,
            'workday_base': matching_rule.workday_base or 8.0,
        }

    # ── Fallback logic for undefined codes ──
    is_leave = code in FULL_DAY_LEAVE_CODES
    return {
        'is_leave': is_leave,
        'leave_hours_p': 8.0 if code == 'P' else 0.0,
        'leave_hours_r': 8.0 if code == 'R' else 0.0,
        'leave_hours_t': 8.0 if code == 'T' else 0.0,
        'leave_hours_c': 8.0 if code == 'C' else 0.0,
        'leave_hours_o': 8.0 if code in ('O', 'X') else 0.0,
        'leave_hours_k': 8.0 if code == 'K' else 0.0,
        'official_start': time(8, 0),
        'official_end': time(17, 0),
        'end_next_day': code == 'D', # Legacy D was overnight
        'work_hours_expected': 0.0 if is_leave else 8.0,
        'break_hours': 1.0 if not is_leave else 0.0,
        'has_overtime': not is_leave,
        'max_hours': None,
        'standard_hours': 0.0 if is_leave else 8.0,
        'workday_base': 8.0,
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
    hours_t = window.get('leave_hours_t', 0.0)
    hours_c = window.get('leave_hours_c', 0.0)
    hours_k = window.get('leave_hours_k', 0.0)

    # ── Full-day leave: return leave hours and zeros for work ─────────────────
    if first == last and window['is_leave']:
        return 0.0, 0.0, 0.0, 0, 0, hours_p, hours_r, hours_o, hours_t, hours_c, hours_k, 0.0, window['standard_hours'], window['workday_base']

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
        raw_ot = (last - actual_ot_threshold).total_seconds() / 3600.0
        # Round down to nearest 0.5 (e.g. 1.4 -> 1.0, 1.9 -> 1.5)
        rounded_ot = math.floor(raw_ot * 2) / 2
        # Minimum threshold 1.0h
        hours_ot = rounded_ot if rounded_ot >= 1.0 else 0.0
    else:
        hours_ot = 0.0

    # 4. Standard hours
    # First, calculate effective work hours (Total - Break)
    raw_work_hours = (total_secs - break_secs) / 3600.0
    if raw_work_hours < 0: raw_work_hours = 0.0

    # Standard hours is the part of total work that IS NOT counted as valid OT, 
    # but still capped at the expected duration.
    # Note: If someone works 9.5h and gets 1.5h OT, they get 8.0h standard.
    # If someone works 8.8h and gets 0.0h OT (since < 1.0), they get min(8.8, 8.0) = 8.0h standard.
    hours_standard = min(raw_work_hours - hours_ot, float(window['work_hours_expected']))
    if hours_standard < 0: hours_standard = 0.0

    # 5. Night Subsidy (22:00 - 05:00)
    night_subsidy_hours = 0.0
    if window.get('end_next_day'):
        # Window: 22:00 today to 05:00 tomorrow
        ns = datetime.combine(w_date, time(22, 0))
        ne = datetime.combine(w_date + timedelta(days=1), time(5, 0))
        
        # Intersection of [first, last] and [ns, ne]
        overlap_start = max(first, ns)
        overlap_end = min(last, ne)
        
        if overlap_start < overlap_end:
            overlap_secs = (overlap_end - overlap_start).total_seconds()
            actual_night_secs = max(0.0, overlap_secs - break_secs)
            night_subsidy_hours = round(actual_night_secs / 3600.0, 2)

    # Final Rounding for display
    work_hours = round(raw_work_hours, 2)
    hours_standard = round(hours_standard, 2)
    hours_ot = round(hours_ot, 2)


    # Protection Rule: If neither late nor early, force standard hours to expected

    
    if minutes_late == 0 and minutes_early <= 5: 
        hours_standard = float(window['work_hours_expected'])

    return (
        work_hours, hours_standard, hours_ot, minutes_late, minutes_early, 
        hours_p, hours_r, hours_o, hours_t, hours_c, hours_k,
        night_subsidy_hours, window['standard_hours'], window['workday_base']
    )


def determine_missing_tap(tap_time, w_date, shift_code, department, rules_pool=None):
    """Determine whether a single tap is a missing check-in or missing check-out.

    Heuristic: compare the tap's distance to shift start_time vs end_time.
      - Closer to start_time → user checked IN, forgot to check OUT → 'Missing Check-out'
      - Closer to end_time   → user checked OUT, forgot to check IN  → 'Missing Check-in'
      - Cannot determine     → 'Missing Check-in/out' (fallback)
    """
    if not tap_time or not w_date:
        return "Missing Check-in/out"

    try:
        window = parse_shift_window(shift_code, department, rules_pool=rules_pool)

        start_dt = datetime.combine(w_date, window['official_start'])
        if window.get('end_next_day'):
            end_dt = datetime.combine(w_date + timedelta(days=1), window['official_end'])
        else:
            end_dt = datetime.combine(w_date, window['official_end'])

        dist_to_start = abs((tap_time - start_dt).total_seconds())
        dist_to_end   = abs((tap_time - end_dt).total_seconds())

        if dist_to_start <= dist_to_end:
            return "Missing Check-out"
        else:
            return "Missing Check-in"
    except Exception:
        return "Missing Check-in/out"
