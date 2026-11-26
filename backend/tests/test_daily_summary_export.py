from datetime import date, datetime
from io import BytesIO

import pytest
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from database import AttendanceLog, EmployeeLocalRegistry
from features.daily_summary import export_service
from features.daily_summary.export_service import (
    _sheet2_headers,
    _sheet1_indicators,
    _sheet1_values,
)


@pytest.fixture
def day_summary():
    return {
        "first": "08:00",
        "last": "17:00",
        "lunch_out_str": "11:30",
        "lunch_in_str": "12:15",
        "lunch_late_minutes": 15,
        "std": 8.0,
        "ot": 1.0,
        "late": 0,
        "early": 0,
        "shift_code": "N",
    }


@pytest.mark.parametrize("view_mode", ["time", "hours", "both"])
def test_sheet1_includes_lunch_taps_with_aligned_values(day_summary, view_mode):
    indicators = _sheet1_indicators(view_mode)
    values = _sheet1_values(day_summary, view_mode)

    assert len(indicators) == len(values)
    assert values[indicators.index("Ra trưa")] == "11:30"
    assert values[indicators.index("Vào trưa")] == "12:15"
    assert values[indicators.index("Ăn trưa quá giờ (phút)")] == 15


def test_sheet2_includes_lunch_late_minutes_column():
    headers = _sheet2_headers()

    assert "Ăn trưa quá giờ (phút)" in headers
    assert headers.index("Ăn trưa quá giờ (phút)") == headers.index("Trạng thái trưa") + 1


def test_downloaded_daily_summary_centers_and_borders_all_sheets(client, db_session, monkeypatch):
    work_date = date(2026, 9, 10)
    db_session.add(EmployeeLocalRegistry(employee_id="EXPORT-001", source_status="excel_synced"))
    db_session.add(AttendanceLog(
        employee_id="EXPORT-001", attendance_date=work_date,
        attendance_time=datetime(2026, 9, 10, 8), machine_ip="10.0.0.1",
    ))
    db_session.flush()
    connection = db_session.connection()
    monkeypatch.setattr(export_service, "SessionLocal", lambda: Session(bind=connection))

    response = client.post("/api/daily-summary/export", params={
        "start_date": work_date.isoformat(), "end_date": work_date.isoformat(), "view_mode": "both",
    })
    assert response.status_code == 200
    download = client.get("/api/daily-summary/export/download")
    assert download.status_code == 200

    workbook = load_workbook(BytesIO(download.content))
    assert len(workbook.worksheets) == 3
    for sheet in workbook.worksheets:
        assert sheet["A2"].value == "EXPORT-001"
        assert sheet["A1"].font.bold
        assert sheet["A1"].fill.patternType == "solid"
        for row in sheet.iter_rows():
            for cell in row:
                assert cell.alignment.horizontal == "center"
                assert cell.alignment.vertical == "center"
                assert all(
                    getattr(cell.border, side).style in {"thin", "medium"}
                    for side in ("left", "right", "top", "bottom")
                )


def test_downloaded_report_applies_default_day_shifts_to_all_employee_sources(client, db_session, monkeypatch):
    work_date = date(2026, 11, 25)
    for employee, source, department in [
        ("WORKSHOP", "log_only", "X\u01b0\u1edfng 1\u4e00\u90e8"),
        ("OTHER", "machine_only", None),
    ]:
        db_session.add(EmployeeLocalRegistry(
            employee_id=employee, source_status=source, department=department,
        ))
        db_session.add_all(
            AttendanceLog(
                employee_id=employee, attendance_date=work_date,
                attendance_time=datetime(2026, 11, 25, hour, minute), machine_ip="10.0.0.1",
            )
            for hour, minute in ((7, 39), (22, 30))
        )
    db_session.flush()
    connection = db_session.connection()
    monkeypatch.setattr(export_service, "SessionLocal", lambda: Session(bind=connection))

    response = client.post("/api/daily-summary/export", params={
        "start_date": work_date.isoformat(), "end_date": work_date.isoformat(), "view_mode": "both",
    })
    assert response.status_code == 200
    download = client.get("/api/daily-summary/export/download")
    assert download.status_code == 200

    with BytesIO(download.content) as content:
        workbook = load_workbook(content, read_only=True)
        headers, *rows = workbook.worksheets[1].values
        workbook.close()

    shift = headers.index("M\u00e3 c\u00f4ng")
    work = headers.index("Gi\u1edd C\u00f4ng")
    overtime = headers.index("T\u0103ng Ca")
    assert {row[0]: (row[shift], row[work], row[overtime]) for row in rows} == {
        "WORKSHOP": ("N12", 12, 0),
        "OTHER": ("N", 8, 5.5),
    }
