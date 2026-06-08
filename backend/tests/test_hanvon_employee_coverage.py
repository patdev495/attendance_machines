import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from features.machines import service


class FakeHanvonClient:
    employee_ids = []
    face_ids = set()
    employee_details = {}
    manager_ids = []
    manager_authority = {}
    manager_photos = {}
    fail = False
    get_employee_calls = []

    def __init__(self, *args, **kwargs):
        if self.fail:
            raise OSError("offline")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def get_employee_ids(self):
        return self.employee_ids, self.face_ids

    def get_employee(self, employee_id):
        self.get_employee_calls.append(employee_id)
        return self.employee_details.get(employee_id, {})

    def get_manager_ids(self):
        return self.manager_ids

    def get_manager(self, manager_id):
        return {
            "id": manager_id,
            "authority": self.manager_authority.get(manager_id, 2),
            "capturejpg": self.manager_photos.get(manager_id, ""),
        }


def patch_client(monkeypatch, *, employees=None, faces=None, employee_details=None, managers=None, authorities=None, manager_photos=None, fail=False):
    FakeHanvonClient.employee_ids = employees or []
    FakeHanvonClient.face_ids = set(faces or [])
    FakeHanvonClient.employee_details = employee_details or {}
    FakeHanvonClient.manager_ids = managers or []
    FakeHanvonClient.manager_authority = authorities or {}
    FakeHanvonClient.manager_photos = manager_photos or {}
    FakeHanvonClient.fail = fail
    FakeHanvonClient.get_employee_calls = []
    monkeypatch.setattr(service, "HanvonClient", FakeHanvonClient)


def test_hanvon_coverage_employee_with_face(monkeypatch):
    patch_client(monkeypatch, employees=["1001"], faces=["1001"])

    result = service.check_user_biometric_on_machine("192.168.1.10", "1001")

    assert result["status"] == "Online"
    assert result["registered"] is True
    assert result["role"] == "employee"
    assert result["has_face"] is True


def test_hanvon_coverage_admin_roles(monkeypatch):
    patch_client(
        monkeypatch,
        managers=["admin1", "root"],
        authorities={"admin1": 2, "root": 0},
        manager_photos={"admin1": "jpeg_base64", "root": "jpeg_base64"},
    )

    admin = service.check_user_biometric_on_machine("192.168.1.10", "admin1")
    super_admin = service.check_user_biometric_on_machine("192.168.1.10", "root")

    assert admin["role"] == "admin"
    assert admin["has_face"] is True
    assert super_admin["role"] == "super_admin"
    assert super_admin["has_face"] is True


def test_hanvon_coverage_not_registered(monkeypatch):
    patch_client(monkeypatch, employees=["1001"], managers=["admin1"])

    result = service.check_user_biometric_on_machine("192.168.1.10", "2002")

    assert result["registered"] is False
    assert result["role"] == "not_registered"


def test_hanvon_coverage_offline(monkeypatch):
    patch_client(monkeypatch, fail=True)

    result = service.check_user_biometric_on_machine("192.168.1.10", "1001")

    assert result["status"] == "Offline"
    assert result["registered"] is False
    assert result["role"] == "not_registered"


def test_get_users_from_machine_does_not_fetch_employee_details(monkeypatch):
    patch_client(
        monkeypatch,
        employees=["1001"],
        faces=["1001"],
        employee_details={"1001": {"name": "Nguyen Van A", "capturejpg": "photo_base64"}},
    )

    users, status = service.get_users_from_machine("192.168.1.10")

    assert status == "Success"
    assert users[0]["user_id"] == "1001"
    assert users[0]["name"] == ""
    assert FakeHanvonClient.get_employee_calls == []


def test_get_user_photo_from_machine_returns_employee_photo(monkeypatch):
    patch_client(
        monkeypatch,
        employees=["1001"],
        employee_details={"1001": {"capturejpg": "employee_photo_base64"}},
    )

    photo, status = service.get_user_photo_from_machine("192.168.1.10", "1001")

    assert status == "Success"
    assert photo == "employee_photo_base64"


def test_get_user_photo_from_machine_prefers_manager_photo(monkeypatch):
    patch_client(
        monkeypatch,
        employees=["1001"],
        employee_details={"1001": {"capturejpg": "employee_photo_base64"}},
        managers=["1001"],
        manager_photos={"1001": "manager_photo_base64"},
    )

    photo, status = service.get_user_photo_from_machine("192.168.1.10", "1001")

    assert status == "Success"
    assert photo == "manager_photo_base64"


def test_get_user_photo_from_machine_reports_not_found(monkeypatch):
    patch_client(monkeypatch, employees=["1001"])

    photo, status = service.get_user_photo_from_machine("192.168.1.10", "2002")

    assert photo == ""
    assert "not found" in status
