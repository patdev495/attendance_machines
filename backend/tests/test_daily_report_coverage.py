from datetime import date, datetime
from io import BytesIO

from openpyxl import load_workbook
from database import AttendanceLog, EmployeeDailyShifts, EmployeeLocalRegistry
from features.daily_summary import export_service
from features.machines import service as machine_service
from shared import hardware


DAY = date(2026, 11, 25)
PERIOD = {"start_date": DAY.isoformat(), "end_date": DAY.isoformat()}
MACHINE = "10.0.0.1"


def raw_log(employee_id, hour=7, minute=47):
    return AttendanceLog(
        employee_id=employee_id,
        attendance_date=DAY,
        attendance_time=datetime(2026, 11, 25, hour, minute, 1),
        machine_ip=MACHINE,
    )


def test_report_includes_unverified_tap_and_scheduled_absence(client, db_session):
    db_session.add_all([
        raw_log("NEW-EMP", hour=1),
        EmployeeDailyShifts(employee_id="SCHEDULED", work_date=DAY, shift_code="N"),
        EmployeeLocalRegistry(employee_id="OLD-EMP", source_status="machine_only"),
    ])
    db_session.flush()

    response = client.get("/api/daily-summary", params=PERIOD)
    assert response.status_code == 200
    items = {item["employee_id"]: item for item in response.json()["items"]}
    assert set(items) == {"NEW-EMP", "SCHEDULED"}
    assert items["NEW-EMP"]["first_tap"] == "2026-11-25T01:47:01"
    assert items["NEW-EMP"]["status"] == "log_only"
    assert items["NEW-EMP"]["shift"] == "N"
    assert items["SCHEDULED"]["tap_count"] == 0

    response = client.get("/api/daily-summary", params={**PERIOD, "employee_id": "NEW-EMP"})
    assert [item["employee_id"] for item in response.json()["items"]] == ["NEW-EMP"]
    detail = client.get(
        "/api/daily-summary/detail",
        params={"work_date": DAY.isoformat(), "employee_id": "NEW-EMP"},
    )
    assert [item["employee_id"] for item in detail.json()] == ["NEW-EMP"]


def test_opening_report_only_registers_confirmed_employees_with_period_taps(client, db_session, monkeypatch):
    class MachineRoster:
        def __init__(self, ip, **kwargs):
            assert ip == MACHINE

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get_employee_ids(self):
            return ["CONFIRMED", "NEW-CONFIRMED", "OLD-EMP", "KNOWN"], []

        def get_manager_ids(self):
            return []

    monkeypatch.setattr("config.DEMO_MODE", False)
    monkeypatch.setattr(hardware, "get_machine_list", lambda: [MACHINE])
    monkeypatch.setattr(machine_service, "HanvonClient", MachineRoster)
    db_session.add_all([
        raw_log("CONFIRMED"),
        raw_log("NEW-CONFIRMED"),
        raw_log("UNVERIFIED"),
        raw_log("KNOWN"),
        EmployeeLocalRegistry(employee_id="CONFIRMED", source_status="log_only"),
        EmployeeLocalRegistry(employee_id="KNOWN", source_status="excel_synced", emp_name="Roster Name"),
    ])
    db_session.flush()

    for _ in range(2):
        report = client.get("/api/daily-summary", params=PERIOD)
        assert report.status_code == 200
    items = {item["employee_id"]: item for item in report.json()["items"]}
    assert items["UNVERIFIED"]["first_tap"] == "2026-11-25T07:47:01"
    assert items["UNVERIFIED"]["status"] == "log_only"
    assert items["CONFIRMED"]["status"] == "machine_only"

    employees = {item["employee_id"]: item for item in client.get("/api/employees").json()["items"]}
    assert set(employees) == {"CONFIRMED", "NEW-CONFIRMED", "KNOWN"}
    assert employees["CONFIRMED"]["source_status"] == "machine_only"
    assert employees["NEW-CONFIRMED"]["source_status"] == "machine_only"
    assert employees["KNOWN"]["emp_name"] == "Roster Name"
    assert employees["KNOWN"]["source_status"] == "excel_synced"


def test_export_download_has_same_employee_days_as_report(client, db_session, monkeypatch):
    monkeypatch.setattr(export_service, "SessionLocal", lambda: db_session)
    db_session.add_all([
        raw_log("NEW-EMP", hour=1),
        EmployeeDailyShifts(employee_id="SCHEDULED", work_date=DAY, shift_code="N"),
        EmployeeLocalRegistry(employee_id="OLD-EMP", source_status="machine_only"),
    ])
    db_session.flush()

    period = {**PERIOD, "end_date": "2026-11-26"}
    report = client.get("/api/daily-summary", params=period).json()["items"]
    response = client.post("/api/daily-summary/export", params={**period, "view_mode": "both"})
    assert response.status_code == 200
    state = client.get("/api/daily-summary/export/status").json()
    assert state["error"] is None
    response = client.get("/api/daily-summary/export/download")
    assert response.status_code == 200
    with BytesIO(response.content) as content:
        workbook = load_workbook(content, read_only=True)
        headers, *rows = workbook["Thông tin chi tiết"].values
        workbook.close()

    exported = {(row[0], row[6]): row for row in rows}
    assert set(exported) == {
        (row["employee_id"], date.fromisoformat(row["attendance_date"]).strftime("%d/%m/%Y"))
        for row in report
    }
    tap = exported[("NEW-EMP", "25/11/2026")]
    assert tap[headers.index("Giờ In")] == "01:47"
    assert tap[headers.index("Giờ Công")] == 0
    assert "Chưa xác minh" in tap[headers.index("Ghi chú")]
