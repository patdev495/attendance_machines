import pytest
from datetime import datetime, date, time
from backend.src.utils.stats_utils import compute_day_stats
from backend.src.database import ShiftRule

def setup_standard_rules(db_session):
    # Default Day
    db_session.add(ShiftRule(
        dept_keyword=None, shift_code="N",
        official_start=time(8, 0), official_end=time(17, 0),
        end_next_day=False, max_hours=None, standard_hours=8.0,
        deduct_break=True, has_overtime=True
    ))
    # Default Night
    db_session.add(ShiftRule(
        dept_keyword=None, shift_code="D",
        official_start=time(20, 0), official_end=time(5, 0),
        end_next_day=True, max_hours=None, standard_hours=8.0,
        deduct_break=True, has_overtime=True
    ))
    # Xuong 1 Day
    db_session.add(ShiftRule(
        dept_keyword="Xưởng 1", shift_code="N",
        official_start=time(8, 0), official_end=time(20, 0),
        end_next_day=False, max_hours=12.0, standard_hours=12.0,
        deduct_break=False, has_overtime=False
    ))
    db_session.commit()

def test_compute_day_stats_standard_day(db_session):
    setup_standard_rules(db_session)
    
    # 08:30 -> 17:30 (Late 30m, No Early, 8h Standard, 0.0h OT)
    first = datetime(2026, 4, 7, 8, 30)
    last = datetime(2026, 4, 7, 17, 30)
    d = date(2026, 4, 7)
    
    # department="Office", shift="N"
    _, hours_std, hours_ot, min_late, min_early = compute_day_stats(first, last, d, "Office", "N")
    
    assert min_late == 30
    assert min_early == 0
    assert hours_std == 8.0
    assert hours_ot == 0.0

def test_compute_day_stats_standard_night(db_session):
    setup_standard_rules(db_session)
    
    # 20:05 -> 05:10 (Late 5m, No Early, 8h Standard, ~0.08h OT)
    # Note: 5 mins OT = 5/60 = 0.0833...
    first = datetime(2026, 4, 7, 20, 5)
    last = datetime(2026, 4, 8, 5, 10)
    d = date(2026, 4, 7)
    
    _, hours_std, hours_ot, min_late, min_early = compute_day_stats(first, last, d, "Store", "D")
    
    assert min_late == 5
    assert min_early == 0
    assert hours_std == 8.0
    assert round(hours_ot, 2) == 0.08 # 5/60

def test_compute_day_stats_early_leave(db_session):
    setup_standard_rules(db_session)
    
    # 07:55 -> 16:50 (No Late, Early 10m, 7.83...h Standard)
    # Total duration: 8h 55m. Deduct 1h break = 7h 55m = 7.91... hours
    first = datetime(2026, 4, 7, 7, 55)
    last = datetime(2026, 4, 7, 16, 50)
    d = date(2026, 4, 7)
    
    _, hours_std, hours_ot, min_late, min_early = compute_day_stats(first, last, d, "Office", "N")
    
    assert min_late == 0
    assert min_early == 10
    # 16:50 - 08:00 = 8h 50m. Deduct 1h = 7h 50m = 7.833...
    assert round(hours_std, 2) == 7.83

def test_compute_day_stats_xuong1_day(db_session):
    setup_standard_rules(db_session)
    
    # Xuong 1: 08:00-20:00, 12h std, no break, no OT
    # 07:50 -> 20:10
    first = datetime(2026, 4, 7, 7, 50)
    last = datetime(2026, 4, 7, 20, 10)
    d = date(2026, 4, 7)
    
    _, hours_std, hours_ot, min_late, min_early = compute_day_stats(first, last, d, "Xưởng 1 - Phụ kiện", "N")
    
    assert min_late == 0
    assert min_early == 0
    assert hours_std == 12.0
    assert hours_ot == 0.0

def test_compute_day_stats_missing_last_tap(db_session):
    setup_standard_rules(db_session)
    
    first = datetime(2026, 4, 7, 8, 0)
    last = first # Only one tap
    d = date(2026, 4, 7)
    
    _, hours_std, hours_ot, min_late, min_early = compute_day_stats(first, last, d, "Office", "N")
    
    assert hours_std == 0
    assert hours_ot == 0
