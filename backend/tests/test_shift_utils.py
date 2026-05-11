import pytest
from datetime import time
from backend.src.utils.shift_utils import get_shift_rules
from backend.src.database import ShiftRule

def test_get_shift_rules_xuong1_night(db_session):
    # Setup test data
    rule = ShiftRule(
        dept_keyword="Xưởng 1", shift_code="D",
        official_start=time(20, 0), official_end=time(8, 0),
        end_next_day=True, max_hours=12.0, standard_hours=12.0,
        deduct_break=False, has_overtime=False
    )
    db_session.add(rule)
    db_session.commit()
    
    # Execute
    res = get_shift_rules("Xưởng 1 - Phụ kiện", "D")
    
    # Assert
    assert res["official_start"] == time(20, 0)
    assert res["standard_hours"] == 12.0
    assert res["end_next_day"] is True

def test_get_shift_rules_xuong1_day(db_session):
    # Setup test data
    rule = ShiftRule(
        dept_keyword="Xưởng 1", shift_code="N",
        official_start=time(8, 0), official_end=time(20, 0),
        end_next_day=False, max_hours=12.0, standard_hours=12.0,
        deduct_break=False, has_overtime=False
    )
    db_session.add(rule)
    db_session.commit()
    
    # Execute
    res = get_shift_rules("Phòng Xưởng 1", "N")
    
    # Assert
    assert res["official_start"] == time(8, 0)
    assert res["standard_hours"] == 12.0
    assert res["end_next_day"] is False

def test_get_shift_rules_default_fallback(db_session):
    # Setup test data (only default rule)
    rule = ShiftRule(
        dept_keyword=None, shift_code="N",
        official_start=time(8, 0), official_end=time(17, 0),
        end_next_day=False, max_hours=None, standard_hours=8.0,
        deduct_break=True, has_overtime=True
    )
    db_session.add(rule)
    db_session.commit()
    
    # Execute (unknown department)
    res = get_shift_rules("Phòng Kế Toán", "N")
    
    # Assert
    assert res["official_start"] == time(8, 0)
    assert res["standard_hours"] == 8.0
    assert res["deduct_break"] is True

def test_get_shift_rules_empty_db_fallback():
    # If DB is empty, should return hardcoded safety default
    res = get_shift_rules("Any", "N")
    assert res["official_start"] == time(8, 0)
    assert res["standard_hours"] == 8.0
