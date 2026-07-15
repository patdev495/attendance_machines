from datetime import date, datetime

from database import AttendanceLog
from features.hanvon.client import HanvonRecord
from features.logs import service
from backend.scripts.apply_indexes import index_commands_for_dialect


def _attendance_log(employee_id, attendance_time, machine_ip="192.168.1.10"):
    return AttendanceLog(
        employee_id=employee_id,
        attendance_date=attendance_time.date(),
        attendance_time=attendance_time,
        machine_ip=machine_ip,
    )


def _hanvon_record(employee_id, attendance_time, machine_ip="192.168.1.10"):
    return HanvonRecord(
        employee_id=employee_id,
        attendance_time=attendance_time,
        machine_ip=machine_ip,
        raw={},
    )


def test_load_existing_log_keys_scopes_to_machine_and_attendance_date(db_session):
    target_time = datetime(2026, 7, 8, 8, 1, 2)
    db_session.add_all(
        [
            _attendance_log("E1", target_time, "192.168.1.10"),
            _attendance_log("E2", datetime(2026, 7, 9, 8, 1, 2), "192.168.1.10"),
            _attendance_log("E3", target_time, "192.168.1.11"),
        ]
    )
    db_session.commit()

    keys = service.load_existing_log_keys(
        db_session,
        "192.168.1.10",
        date(2026, 7, 8),
    )

    assert keys == {("E1", target_time)}


def test_sync_hanvon_machine_loads_existing_keys_by_day_and_skips_duplicates(
    db_session,
    monkeypatch,
):
    ip = "192.168.1.10"
    first_day = date(2026, 7, 8)
    second_day = date(2026, 7, 9)
    duplicate_time = datetime(2026, 7, 8, 8, 1, 2)
    new_time = datetime(2026, 7, 8, 17, 30, 0)
    second_day_time = datetime(2026, 7, 9, 8, 5, 0)
    db_session.add(_attendance_log("E1", duplicate_time, ip))
    db_session.commit()

    class FakeHanvonClient:
        requested_dates = []

        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def get_device_info(self):
            return {"real_facerecord": "99", "model": "fake", "sn": "fake-sn"}

        def get_records_by_day(self, target_date):
            self.requested_dates.append(target_date)
            return {
                first_day: [
                    _hanvon_record("E1", duplicate_time, ip),
                    _hanvon_record(" E2 ", new_time, ip),
                    _hanvon_record("1", datetime(2026, 7, 8, 12, 0, 0), ip),
                ],
                second_day: [
                    _hanvon_record("E3", second_day_time, ip),
                ],
            }[target_date]

    original_load_existing_log_keys = service.load_existing_log_keys
    key_lookup_calls = []

    def spy_load_existing_log_keys(db, machine_ip, attendance_date):
        key_lookup_calls.append((machine_ip, attendance_date))
        return original_load_existing_log_keys(db, machine_ip, attendance_date)

    monkeypatch.setattr(service, "HanvonClient", FakeHanvonClient)
    monkeypatch.setattr(service, "load_existing_log_keys", spy_load_existing_log_keys)

    added = service._sync_hanvon_machine(db_session, ip, first_day, second_day)

    assert added == 2
    assert FakeHanvonClient.requested_dates == [first_day, second_day]
    assert key_lookup_calls == [(ip, first_day), (ip, second_day)]
    rows = {
        (row.employee_id, row.attendance_time)
        for row in db_session.query(AttendanceLog).order_by(AttendanceLog.attendance_time).all()
    }
    assert rows == {
        ("E1", duplicate_time),
        ("E2", new_time),
        ("E3", second_day_time),
    }


def test_apply_indexes_includes_attendance_log_sync_index_for_mssql_and_sqlite():
    expected_index_name = "idx_attendance_logs_machine_date_employee_time"

    assert any(expected_index_name in command for command in index_commands_for_dialect("mssql"))
    assert any(expected_index_name in command for command in index_commands_for_dialect("sqlite"))
