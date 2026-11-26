from datetime import date, datetime
from io import BytesIO

import pytest
from openpyxl import Workbook, load_workbook
from sqlalchemy.orm import Session

from database import AttendanceLog, EmployeeDailyShifts, EmployeeLocalRegistry, EmployeeMetadata
from features.daily_summary import export_service, service as summary_service


@pytest.fixture
def attendance_machine(monkeypatch):
    class FakeHanvon:
        employee_ids = {"OFF101"}
        manager_ids = set()
        delete_error = None

        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get_employee_ids(self):
            return self.employee_ids, set()

        def get_manager_ids(self):
            return self.manager_ids

        def delete_employee(self, employee_id):
            if self.delete_error:
                raise self.delete_error
            self.employee_ids.remove(employee_id)

    monkeypatch.setattr("features.machines.service.HanvonClient", FakeHanvon)
    return FakeHanvon


def test_machine_delete_changes_excel_employee_to_log_only(client, db_session, attendance_machine):
    db_session.add(EmployeeLocalRegistry(employee_id="OFF101", emp_name="Employee A", source_status="excel_synced"))
    db_session.flush()

    response = client.delete("/api/machines/192.0.2.1/employees/OFF101")

    assert response.status_code == 200
    items = client.get("/api/employees", params={"search": "OFF101"}).json()["items"]
    assert [(item["employee_id"], item["emp_name"], item["source_status"]) for item in items] == [
        ("OFF101", "Employee A", "log_only"),
    ]


def test_failed_machine_delete_keeps_excel_status(client, db_session, attendance_machine):
    db_session.add(EmployeeLocalRegistry(employee_id="OFF101", source_status="excel_synced"))
    db_session.flush()
    attendance_machine.delete_error = RuntimeError("Device refused removal")

    response = client.delete("/api/machines/192.0.2.1/employees/OFF101")

    assert response.status_code == 502
    items = client.get("/api/employees", params={"search": "OFF101"}).json()["items"]
    assert items[0]["source_status"] == "excel_synced"


def test_offboarded_employee_returns_to_excel_status_on_import(client, db_session, attendance_machine, monkeypatch):
    db_session.add(EmployeeLocalRegistry(employee_id="OFF101", source_status="excel_synced"))
    db_session.add(EmployeeMetadata(employee_id="OFF101", emp_name="Old roster"))
    db_session.flush()
    connection = db_session.connection()
    monkeypatch.setattr(summary_service, "SessionLocal", lambda: Session(bind=connection))

    assert client.delete("/api/machines/192.0.2.1/employees/OFF101").status_code == 200
    assert client.post("/api/employees/update-registry").status_code == 200
    items = client.get("/api/employees", params={"search": "OFF101"}).json()["items"]
    assert items[0]["source_status"] == "log_only"

    workbook = Workbook()
    workbook.active.append(["EMP_ID", "EMP_NAME"])
    workbook.active.append(["OFF101", "New roster"])
    upload = BytesIO()
    workbook.save(upload)
    assert client.post("/api/daily-summary/sync-excel", files={"file": ("roster.xlsx", upload.getvalue())}).status_code == 200
    items = client.get("/api/employees", params={"search": "OFF101"}).json()["items"]
    assert [(item["source_status"], item["emp_name"]) for item in items] == [("excel_synced", "New roster")]


def test_export_includes_full_period_for_offboarded_employee_only_when_they_tapped(
    client, db_session, attendance_machine, monkeypatch,
):
    db_session.add(EmployeeLocalRegistry(employee_id="OFF101", source_status="excel_synced", shift="N"))
    db_session.add(EmployeeDailyShifts(employee_id="OFF101", work_date=date(2026, 9, 5), shift_code="K"))
    db_session.add(AttendanceLog(
        employee_id="OFF101", attendance_date=date(2026, 9, 2),
        attendance_time=datetime(2026, 9, 2, 8), machine_ip="192.0.2.1",
    ))
    db_session.flush()
    connection = db_session.connection()
    monkeypatch.setattr(export_service, "SessionLocal", lambda: Session(bind=connection))
    assert client.delete("/api/machines/192.0.2.1/employees/OFF101").status_code == 200

    def download_details(start, end):
        response = client.post("/api/daily-summary/export", params={
            "start_date": start, "end_date": end, "view_mode": "both",
        })
        assert response.status_code == 200
        download = client.get("/api/daily-summary/export/download")
        assert download.status_code == 200
        with BytesIO(download.content) as data:
            workbook = load_workbook(data)
            return [row for row in workbook.worksheets[1].values if row[0] == "OFF101"]

    rows = download_details("2026-09-01", "2026-09-05")
    assert [row[6] for row in rows] == ["01/09/2026", "02/09/2026", "03/09/2026", "04/09/2026", "05/09/2026"]
    assert "08:00" in rows[1][7:9]
    for row in [rows[0], *rows[2:]]:
        assert row[7:9] == ("-", "-")
        assert row[14:16] == (0, 0)
        assert row[-1] == "Không chấm công"
    assert download_details("2026-09-04", "2026-09-06") == []
