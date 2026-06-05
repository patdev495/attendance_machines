import pytest
from datetime import datetime, date, time
from types import SimpleNamespace
from backend.src.utils.stats_utils import compute_day_stats


def make_shift_def(shift_code, start_time, end_time, is_night_shift=False,
                   break_hours=1.0, work_hours=8.0, standard_hours=8.0,
                   workday_base=8.0, ot_start_time=None,
                   leave_hours_p=0.0, leave_hours_r=0.0, leave_hours_o=0.0,
                   leave_hours_t=0.0, leave_hours_c=0.0, leave_hours_k=0.0):
    """Create a ShiftDefinition-compatible object without hitting the DB."""
    return SimpleNamespace(
        shift_code=shift_code,
        start_time=start_time,
        end_time=end_time,
        ot_start_time=ot_start_time,
        is_night_shift=is_night_shift,
        break_hours=break_hours,
        work_hours=work_hours,
        standard_hours=standard_hours,
        workday_base=workday_base,
        leave_hours_p=leave_hours_p,
        leave_hours_r=leave_hours_r,
        leave_hours_o=leave_hours_o,
        leave_hours_t=leave_hours_t,
        leave_hours_c=leave_hours_c,
        leave_hours_k=leave_hours_k,
    )


# ── Shared rule definitions ─────────────────────────────────────────────────
STANDARD_DAY = make_shift_def("N", time(8, 0), time(17, 0),
                              break_hours=1.0, work_hours=8.0, standard_hours=8.0)
STANDARD_NIGHT = make_shift_def("D", time(20, 0), time(5, 0),
                                is_night_shift=True, break_hours=1.0,
                                work_hours=8.0, standard_hours=8.0)
XUONG1_DAY = make_shift_def("N", time(8, 0), time(20, 0),
                             break_hours=0.0, work_hours=12.0, standard_hours=12.0,
                             workday_base=12.0)

STANDARD_RULES = [STANDARD_DAY, STANDARD_NIGHT]


def test_compute_day_stats_standard_day():
    # 08:30 -> 17:30 (Late 30m, No Early, 8h Standard, 0.0h OT)
    first = datetime(2026, 4, 7, 8, 30)
    last = datetime(2026, 4, 7, 17, 30)
    d = date(2026, 4, 7)

    stats = compute_day_stats(first, last, d, "Office", "N", rules_pool=STANDARD_RULES)
    _, hours_std, hours_ot, min_late, min_early = stats[:5]

    assert min_late == 30
    assert min_early == 0
    assert hours_std == 8.0
    assert hours_ot == 0.0


def test_compute_day_stats_standard_night():
    # 20:05 -> 05:10 (Late 5m, No Early, 8h Standard)
    # 10 min OT = 0.16h raw -> floor(0.16*2)/2 = 0.0 (< 1h threshold)
    first = datetime(2026, 4, 7, 20, 5)
    last = datetime(2026, 4, 8, 5, 10)
    d = date(2026, 4, 7)

    stats = compute_day_stats(first, last, d, "Store", "D", rules_pool=STANDARD_RULES)
    _, hours_std, hours_ot, min_late, min_early = stats[:5]

    assert min_late == 5
    assert min_early == 0
    assert hours_std == 8.0
    assert hours_ot == 0.0  # 10 min < 1h minimum threshold


def test_compute_day_stats_early_leave():
    # 07:55 -> 16:50 (No Late, Early 10m, partial standard)
    # effective: 08:00-16:50 = 8h 50m. Deduct 1h break = 7h 50m = 7.833h
    first = datetime(2026, 4, 7, 7, 55)
    last = datetime(2026, 4, 7, 16, 50)
    d = date(2026, 4, 7)

    stats = compute_day_stats(first, last, d, "Office", "N", rules_pool=STANDARD_RULES)
    _, hours_std, hours_ot, min_late, min_early = stats[:5]

    assert min_late == 0
    assert min_early == 10
    # 16:50 - 08:00 = 8h 50m. Deduct 1h = 7h 50m = 7.833...
    assert round(hours_std, 2) == 7.83


def test_compute_day_stats_xuong1_day():
    # Xuong 1: 08:00-20:00, 12h std, no break, no OT threshold
    # 07:50 -> 20:10
    first = datetime(2026, 4, 7, 7, 50)
    last = datetime(2026, 4, 7, 20, 10)
    d = date(2026, 4, 7)

    xuong1_rules = [XUONG1_DAY]
    stats = compute_day_stats(first, last, d, "Xưởng 1 - Phụ kiện", "N",
                              rules_pool=xuong1_rules)
    _, hours_std, hours_ot, min_late, min_early = stats[:5]

    assert min_late == 0
    assert min_early == 0
    assert hours_std == 12.0
    assert hours_ot == 0.0  # 10 min OT < 1h minimum threshold


def test_compute_day_stats_missing_last_tap():
    first = datetime(2026, 4, 7, 8, 0)
    last = first  # Only one tap
    d = date(2026, 4, 7)

    stats = compute_day_stats(first, last, d, "Office", "N", rules_pool=STANDARD_RULES)
    _, hours_std, hours_ot, min_late, min_early = stats[:5]

    assert hours_std == 0
    assert hours_ot == 0
