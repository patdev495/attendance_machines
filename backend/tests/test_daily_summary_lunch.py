import pytest
from datetime import datetime, date
from unittest.mock import MagicMock
from features.daily_summary.service import process_summary_rows

def test_process_summary_rows_includes_lunch_monitoring_fields():
    # Mock grouped row
    mock_row = MagicMock()
    mock_row.employee_id = "EMP001"
    mock_row.full_emp_id = "EMP001"
    mock_row.emp_name = "Nguyen Van A"
    mock_row.work_date = date(2026, 8, 5)
    mock_row.first_tap = datetime(2026, 8, 5, 7, 30)
    mock_row.last_tap = datetime(2026, 8, 5, 16, 30)
    mock_row.tap_count = 4
    mock_row.shift = "N"
    mock_row.department = "Xuong 1"
    mock_row.daily_shift_code = "N"
    mock_row.status = "Active"

    # Mock DB session with AttendanceLog query
    mock_db = MagicMock()
    log1 = MagicMock(employee_id="EMP001", attendance_time=datetime(2026, 8, 5, 7, 30))
    log2 = MagicMock(employee_id="EMP001", attendance_time=datetime(2026, 8, 5, 11, 25))
    log3 = MagicMock(employee_id="EMP001", attendance_time=datetime(2026, 8, 5, 12, 5))
    log4 = MagicMock(employee_id="EMP001", attendance_time=datetime(2026, 8, 5, 16, 30))
    mock_db.query.return_value.filter.return_value.all.return_value = [log1, log2, log3, log4]

    items = process_summary_rows([mock_row], rules_pool=[], db=mock_db)
    assert len(items) == 1
    item = items[0]

    assert "lunch_out" in item
    assert "lunch_in" in item
    assert "lunch_duration_minutes" in item
    assert "lunch_status" in item
    assert "work_status" in item

    assert item["lunch_out"] == datetime(2026, 8, 5, 11, 25)
    assert item["lunch_in"] == datetime(2026, 8, 5, 12, 5)
    assert item["lunch_duration_minutes"] == 40
    assert item["lunch_status"] == "OK"
    assert item["work_status"] == "OK"
