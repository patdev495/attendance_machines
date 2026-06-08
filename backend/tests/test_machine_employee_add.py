import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import EmployeeLocalRegistry
from features.machines.router import MachineEmployeeCreate, add_machine_employee


def test_add_machine_employee_records_name_in_registry(monkeypatch, db_session):
    monkeypatch.setattr(
        "features.machines.router.add_user_to_machine",
        lambda **kwargs: "Success",
    )

    result = add_machine_employee(
        "192.168.1.10",
        MachineEmployeeCreate(employee_id="1001", name="Nguyen Van A", role="employee"),
        db_session,
    )

    registry_entry = db_session.query(EmployeeLocalRegistry).filter(
        EmployeeLocalRegistry.employee_id == "1001"
    ).first()

    assert result == {"status": "Success", "employee_id": "1001"}
    assert registry_entry is not None
    assert registry_entry.emp_name == "Nguyen Van A"
    assert registry_entry.source_status == "machine_only"


def test_add_machine_employee_does_not_overwrite_existing_registry_name(monkeypatch, db_session):
    db_session.add(EmployeeLocalRegistry(
        employee_id="1001",
        emp_name="Official Excel Name",
        source_status="excel_synced",
    ))
    db_session.commit()
    monkeypatch.setattr(
        "features.machines.router.add_user_to_machine",
        lambda **kwargs: "Success",
    )

    add_machine_employee(
        "192.168.1.10",
        MachineEmployeeCreate(employee_id="1001", name="Device Name", role="employee"),
        db_session,
    )

    registry_entry = db_session.query(EmployeeLocalRegistry).filter(
        EmployeeLocalRegistry.employee_id == "1001"
    ).first()

    assert registry_entry.emp_name == "Official Excel Name"
    assert registry_entry.source_status == "excel_synced"
