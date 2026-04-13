import re
from datetime import datetime, timedelta, time
from utils.shift_utils import get_shift_rules

# ── Full-day leave/absence codes: work_hours=0, ot=0 ────────────────────────
# P=Phép, O=Ốm, T=Tang, C=Cưới, R=Việc riêng, K=Nghỉ không phép, X=Chưa vào làm
FULL_DAY_LEAVE_CODES = {'P', 'O', 'T', 'C', 'R', 'K', 'X'}

# ── Regex to parse split codes like 4N4R, 2R6N, 6P6N ────────────────────────
_SPLIT_RE = re.compile(r'^(\d+)([A-Z])(\d+)([A-Z])$', re.IGNORECASE)


def parse_shift_window(shift_code, department, rules_pool=None):
    """
    Parse a daily shift code into an effective work window.

    Returns a dict:
      - is_leave:       True if full-day leave (P, O, T, C, R)
      - leave_code:     The code letter if is_leave, else None
      - official_start: time  (effective work start)
      - official_end:   time  (effective work end)
      - end_next_day:   bool
      - work_hours_expected: float (how many hours this code expects)
      - deduct_break:   bool
      - has_overtime:    bool
      - max_hours:       float | None
      - standard_hours: float
    """
    code = (shift_code or 'N').strip().upper()

    # ── 1. Full-day leave ────────────────────────────────────────────────────
    if code in FULL_DAY_LEAVE_CODES:
        return {
            'is_leave': True,
            'leave_code': code,
            'official_start': time(8, 0),
            'official_end': time(17, 0),
            'end_next_day': False,
            'work_hours_expected': 0,
            'deduct_break': False,
            'has_overtime': False,
            'max_hours': None,
            'standard_hours': 0,
        }

    # ── 2. Try to parse split code (e.g. 4N4R, 2R6N, 6P6N) ─────────────────
    m = _SPLIT_RE.match(code)
    if m:
        h1, c1, h2, c2 = int(m.group(1)), m.group(2).upper(), int(m.group(3)), m.group(4).upper()
        # Determine base shift type: N (day) or D (night)
        work_char = c1 if c1 in ('N', 'D') else c2
        leave_chars = {'R', 'P', 'O', 'T', 'C'}

        # Get the base rules for this shift type + department
        base_rules = get_shift_rules(department, work_char, rules_pool=rules_pool)
        base_start = base_rules['official_start']
        base_end = base_rules['official_end']
        end_next_day = base_rules['end_next_day']

        # Calculate the base window start as a reference datetime
        ref_date = datetime(2000, 1, 1)
        start_dt = datetime.combine(ref_date, base_start)
        if end_next_day:
            end_dt = datetime.combine(ref_date + timedelta(days=1), base_end)
        else:
            end_dt = datetime.combine(ref_date, base_end)

        # Adjust window based on the split
        if c1 in leave_chars:
            # Basic math: offset by h1 hours
            new_start_dt = start_dt + timedelta(hours=h1)
            
            # Phase 13: Apply specific half-shift thresholds (nửa buổi sau)
            # Threshold only applies if leave is significant (>= 4 hours)
            if h1 >= 4:
                is_ws1 = department and "Xưởng 1" in department
                if work_char == 'N': # Day
                    target_t = time(14, 0) if is_ws1 else time(13, 0)
                    new_start_dt = datetime.combine(ref_date, target_t)
                else: # Night (D)
                    target_t = time(2, 0) if is_ws1 else time(1, 0)
                    # Night shifts starting at 20:00 cross midnight for anything >= 4h
                    new_start_dt = datetime.combine(ref_date + timedelta(days=1), target_t)

            new_end_dt = new_start_dt + timedelta(hours=h2)
            # Cap to base end
            new_end_dt = min(new_end_dt, end_dt)
            work_hours_expected = h2
        else:
            # Trailing leave: start at base start, work for h1 hours
            new_start_dt = start_dt
            new_end_dt = start_dt + timedelta(hours=h1)
            # Cap to base end
            new_end_dt = min(new_end_dt, end_dt)
            work_hours_expected = h1

        new_start = new_start_dt.time()
        # Check if new_end crosses midnight relative to ref_date
        new_end_next_day = new_end_dt.date() > ref_date.date()
        new_end = new_end_dt.time()

        return {
            'is_leave': False,
            'leave_code': None,
            'official_start': new_start,
            'official_end': new_end,
            'end_next_day': new_end_next_day,
            'work_hours_expected': work_hours_expected,
            'deduct_break': base_rules['deduct_break'],
            'has_overtime': base_rules['has_overtime'] and base_rules['standard_hours'] < 12,
            'max_hours': None,
            'standard_hours': base_rules['standard_hours'],
        }

    # ── 3. Simple N or D code ────────────────────────────────────────────────
    base_rules = get_shift_rules(department, code, rules_pool=rules_pool)
    return {
        'is_leave': False,
        'leave_code': None,
        'official_start': base_rules['official_start'],
        'official_end': base_rules['official_end'],
        'end_next_day': base_rules['end_next_day'],
        'work_hours_expected': base_rules['standard_hours'],
        'deduct_break': base_rules['deduct_break'],
        'has_overtime': base_rules['has_overtime'],
        'max_hours': base_rules['max_hours'],
        'standard_hours': base_rules['standard_hours'],
    }


def compute_day_stats(first, last, w_date, department, shift_code, rules_pool=None):
    """
    Return (work_hours, hours_standard, hours_ot, minutes_late, minutes_early).

    If shift_code is a full-day leave code (P, O, T, C, R), returns:
      work_hours=0, hours_standard=0, hours_ot=0, minutes_late=0, minutes_early=0
    """
    window = parse_shift_window(shift_code, department, rules_pool=rules_pool)

    # ── Full-day leave: all zeros ────────────────────────────────────────────
    if window['is_leave']:
        return 0.0, 0.0, 0.0, 0, 0

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

    if window['deduct_break']:
        # Phase 13: Precise overlap-based break deduction
        is_ws1 = department and "Xưởng 1" in department
        shift_code_upper = shift_code.upper() if shift_code else ''
        
        if 'D' in shift_code_upper:
            # Night shift break
            # WS1: 01:00-02:00 AM, Default: 00:00-01:00 AM
            b_start_t = time(1, 0) if is_ws1 else time(0, 0)
            b_end_t = time(2, 0) if is_ws1 else time(1, 0)
            b_start_dt = datetime.combine(w_date + timedelta(days=1), b_start_t)
            b_end_dt = datetime.combine(w_date + timedelta(days=1), b_end_t)
            # User rule: Only deduct if they started before the break restart point
            threshold_t = time(2, 0) if is_ws1 else time(1, 0)
            t_in = effective_in.time()
            if not (t_in >= time(18, 0) or t_in < threshold_t):
                b_start_dt = b_end_dt
        else:
            # Day shift break
            b_start_t = time(13, 0) if is_ws1 else time(12, 0)
            b_end_t = time(14, 0) if is_ws1 else time(13, 0)
            b_start_dt = datetime.combine(w_date, b_start_t)
            b_end_dt = datetime.combine(w_date, b_end_t)
            if effective_in.time() >= time(13, 0):
                b_start_dt = b_end_dt

        # Calculate Overlap
        overlap_start = max(effective_in, b_start_dt)
        overlap_end = min(effective_out, b_end_dt)
        overlap_secs = max(0.0, (overlap_end - overlap_start).total_seconds())
        
        # USE RAW SECONDS for now, NO ROUNDING yet
        raw_work_hours = (total_secs - overlap_secs) / 3600.0
    else:
        raw_work_hours = total_secs / 3600.0

    # Apply cap if max_hours is set (using raw values)
    if window['max_hours'] is not None:
        raw_work_hours = min(raw_work_hours, float(window['max_hours']))

    # 3. OT logic
    is_12h = window['standard_hours'] >= 12.0
    hours_ot = 0.0
    raw_std_hours = raw_work_hours

    if window['has_overtime'] and not is_12h:
        # Phase 13 rule: Overtime strictly starts at 17:00 (Day shift) or 05:00 (Night shift)
        shift_code_upper = shift_code.upper() if shift_code else ''
        
        if 'N' in shift_code_upper:
            actual_ot_threshold = datetime.combine(w_date, time(17, 0))
        elif 'D' in shift_code_upper:
            actual_ot_threshold = datetime.combine(w_date + timedelta(days=1), time(5, 0))
        else:
            actual_ot_threshold = official_end_dt

        # OT is only the portion of the actual shift that falls after ot_threshold.
        if first == last and last > actual_ot_threshold:
            ot_start = actual_ot_threshold
        else:
            ot_start = max(first, actual_ot_threshold)
            
        ot_end = max(last, actual_ot_threshold)
        if ot_end > ot_start:
            ot_secs = (ot_end - ot_start).total_seconds()
        else:
            ot_secs = 0.0
            
        hours_ot = round(ot_secs / 3600.0, 2)
        # Calculate standard hours using RAW SECONDS (or raw hours) to avoid 7.99
        raw_std_hours = max(0.0, raw_work_hours - (ot_secs / 3600.0))

    # Phase 13: Cap standard hours at the expected duration
    raw_std_hours = min(raw_std_hours, float(window['work_hours_expected']))

    # FINAL ROUNDING as the last step
    work_hours = round(raw_work_hours, 2)
    hours_standard = round(raw_std_hours, 2)
    hours_ot = round(hours_ot, 2)
    
    # Phase 13: Perfect Attendance Protection Rule
    # If the employee is neither late nor leaving early, we override standard hours 
    # with the full theoretical shift duration to ensure clean data (e.g., 8.00 instead of 7.99).
    if minutes_late == 0 and minutes_early == 0:
        hours_standard = float(window['work_hours_expected'])

    return work_hours, hours_standard, hours_ot, minutes_late, minutes_early
