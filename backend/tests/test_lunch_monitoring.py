import pytest
from datetime import datetime, date, time
from utils.stats_utils import extract_lunch_swipes

def test_extract_lunch_swipes_normal_4_taps():
    w_date = date(2026, 8, 5)
    taps = [
        datetime(2026, 8, 5, 7, 30),   # Check-in
        datetime(2026, 8, 5, 11, 25),  # Lunch Out
        datetime(2026, 8, 5, 12, 5),   # Lunch In
        datetime(2026, 8, 5, 16, 30),  # Check-out
    ]
    res = extract_lunch_swipes(taps)
    assert res["lunch_out"] == datetime(2026, 8, 5, 11, 25)
    assert res["lunch_in"] == datetime(2026, 8, 5, 12, 5)
    assert res["lunch_duration_minutes"] == 40
    assert res["lunch_status"] == "OK"

def test_extract_lunch_swipes_debounce_ignore_under_5_min():
    taps = [
        datetime(2026, 8, 5, 7, 30),
        datetime(2026, 8, 5, 11, 25, 0),   # Lunch Out
        datetime(2026, 8, 5, 11, 26, 30), # Duplicate tap < 5 min -> ignored for lunch_in
        datetime(2026, 8, 5, 12, 10, 0),  # Valid Lunch In >= 5 min
        datetime(2026, 8, 5, 16, 30),
    ]
    res = extract_lunch_swipes(taps)
    assert res["lunch_out"] == datetime(2026, 8, 5, 11, 25, 0)
    assert res["lunch_in"] == datetime(2026, 8, 5, 12, 10, 0)
    assert res["lunch_duration_minutes"] == 45
    assert res["lunch_status"] == "OK"

def test_extract_lunch_swipes_missing_lunch_in():
    taps = [
        datetime(2026, 8, 5, 7, 30),
        datetime(2026, 8, 5, 11, 30),  # Lunch Out
        datetime(2026, 8, 5, 16, 30),  # Evening Check-out
    ]
    res = extract_lunch_swipes(taps)
    assert res["lunch_out"] == datetime(2026, 8, 5, 11, 30)
    assert res["lunch_in"] is None
    assert res["lunch_duration_minutes"] is None
    assert res["lunch_status"] == "MISSING_LUNCH_IN"

def test_extract_lunch_swipes_no_lunch_swipe():
    taps = [
        datetime(2026, 8, 5, 7, 30),
        datetime(2026, 8, 5, 16, 30),
    ]
    res = extract_lunch_swipes(taps)
    assert res["lunch_out"] is None
    assert res["lunch_in"] is None
    assert res["lunch_duration_minutes"] is None
    assert res["lunch_status"] == "NO_LUNCH_SWIPE"

def test_extract_lunch_swipes_window_bounds_1120_to_1240():
    taps_early = [
        datetime(2026, 8, 5, 7, 30),
        datetime(2026, 8, 5, 11, 15), # Too early (< 11:20)
        datetime(2026, 8, 5, 16, 30),
    ]
    res = extract_lunch_swipes(taps_early)
    assert res["lunch_status"] == "NO_LUNCH_SWIPE"

    taps_late = [
        datetime(2026, 8, 5, 7, 30),
        datetime(2026, 8, 5, 12, 40), # 12:40 upper bound
        datetime(2026, 8, 5, 16, 30),
    ]
    res = extract_lunch_swipes(taps_late)
    assert res["lunch_status"] == "NO_LUNCH_SWIPE"
