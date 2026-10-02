import sys
from pathlib import Path

import pytest
from fastapi import HTTPException


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import EmployeeLocalRegistry
from features.machines.router import MachineEmployeeCreate, add_machine_employee
from features.machines.service import _generate_unique_manager_password


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


def test_manager_creation_rejects_an_incorrect_system_authorization_password(monkeypatch, db_session):
    calls = []
    monkeypatch.setattr(
        "features.machines.router.add_user_to_machine",
        lambda **kwargs: calls.append(kwargs) or "Success",
    )

    with pytest.raises(HTTPException, match="Invalid system authorization password") as exc_info:
        add_machine_employee(
            "192.168.1.10",
            MachineEmployeeCreate(
                employee_id="1001",
                role="admin",
                photo_base64="real-photo",
                promotion_password="incorrect",
            ),
            db_session,
        )

    assert exc_info.value.status_code == 403
    assert calls == []


def test_manager_creation_uses_system_authorization_without_sending_it_to_machine(monkeypatch, db_session):
    captured = {}

    def fake_add_user(**kwargs):
        captured.update(kwargs)
        return "Success"

    monkeypatch.setattr("features.machines.router.add_user_to_machine", fake_add_user)

    add_machine_employee(
        "192.168.1.10",
        MachineEmployeeCreate(
            employee_id="1001",
            role="super_admin",
            photo_base64="real-photo",
            promotion_password="admin123",
        ),
        db_session,
    )

    assert captured["role"] == "super_admin"
    assert "password" not in captured
    assert "promotion_password" not in captured


def test_generated_manager_password_avoids_passwords_already_on_machine(monkeypatch):
    class FakeClient:
        def get_manager_ids(self):
            return ["existing-manager"]

        def get_manager(self, manager_id):
            assert manager_id == "existing-manager"
            return {"password": "123456"}

    generated_values = iter([123456, 654321])
    monkeypatch.setattr(
        "features.machines.service.secrets.randbelow",
        lambda upper_bound: next(generated_values),
    )

    assert _generate_unique_manager_password(FakeClient()) == "654321"
