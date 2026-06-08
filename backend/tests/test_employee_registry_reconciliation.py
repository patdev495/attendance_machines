import sys
from datetime import date, datetime
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import AttendanceLog, EmployeeLocalRegistry, EmployeeMetadata
from features.employees.registry_service import (
    SOURCE_EXCEL_SYNCED,
    SOURCE_LOG_ONLY,
    SOURCE_MACHINE_ONLY,
    employee_name_map,
    find_employee_ids_for_search,
    reconcile_employee_local_registry,
)


def _log(employee_id: str) -> AttendanceLog:
    return AttendanceLog(
        employee_id=employee_id,
        attendance_date=date(2026, 1, 5),
        attendance_time=datetime(2026, 1, 5, 8, 0),
        machine_ip="192.168.1.10",
    )


def test_registry_reconciliation_applies_source_precedence(db_session):
    db_session.add_all([
        EmployeeMetadata(
            employee_id="E1",
            emp_name="Excel Name",
            department="Assembly",
            group="A",
            start_date=date(2025, 12, 1),
            shift="N",
            full_emp_id="NY-E1",
            privilege=14,
        ),
        EmployeeLocalRegistry(employee_id="OLD", source_status=SOURCE_MACHINE_ONLY),
        _log("E1"),
        _log("M1"),
        _log("L1"),
    ])
    db_session.commit()

    reconcile_employee_local_registry(db_session, machine_employee_ids={"E1", "M1"})

    rows = {
        row.employee_id: row
        for row in db_session.query(EmployeeLocalRegistry).all()
    }

    assert set(rows) == {"E1", "M1", "L1"}
    assert rows["E1"].source_status == SOURCE_EXCEL_SYNCED
    assert rows["E1"].emp_name == "Excel Name"
    assert rows["E1"].department == "Assembly"
    assert rows["E1"].group_name == "A"
    assert rows["E1"].full_emp_id == "NY-E1"
    assert rows["E1"].privilege == 14
    assert rows["M1"].source_status == SOURCE_MACHINE_ONLY
    assert rows["L1"].source_status == SOURCE_LOG_ONLY


def test_registry_lookup_and_name_enrichment_share_precedence(db_session):
    db_session.add_all([
        EmployeeLocalRegistry(
            employee_id="1001",
            full_emp_id="NY1001",
            emp_name="Registry Alice",
            source_status=SOURCE_EXCEL_SYNCED,
        ),
        EmployeeMetadata(
            employee_id="1001",
            emp_name="Metadata Alice",
            full_emp_id="OLD1001",
        ),
        EmployeeMetadata(
            employee_id="2002",
            emp_name="Metadata Bob",
            full_emp_id="NY2002",
        ),
    ])
    db_session.commit()

    assert "1001" in find_employee_ids_for_search(db_session, "NY1001")
    assert "2002" in find_employee_ids_for_search(db_session, "Metadata Bob")

    names = employee_name_map(db_session, ["1001", "2002"])
    assert names["1001"] == "Registry Alice"
    assert names["2002"] == "Metadata Bob"
