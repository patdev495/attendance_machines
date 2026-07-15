import sys
from pathlib import Path
from datetime import datetime

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import AttendanceLog


def test_get_date_range_empty(client):
    response = client.get("/api/logs/date-range")
    assert response.status_code == 200
    data = response.json()
    assert data == {"min_date": None, "max_date": None}


def test_get_date_range_with_logs(client, db_session):
    # Add logs
    db_session.add_all([
        AttendanceLog(
            employee_id="E1",
            attendance_date=datetime(2026, 7, 10).date(),
            attendance_time=datetime(2026, 7, 10, 8, 0, 0),
            machine_ip="192.168.1.10"
        ),
        AttendanceLog(
            employee_id="E2",
            attendance_date=datetime(2026, 7, 15).date(),
            attendance_time=datetime(2026, 7, 15, 17, 30, 0),
            machine_ip="192.168.1.10"
        ),
        AttendanceLog(
            employee_id="E3",
            attendance_date=datetime(2026, 7, 12).date(),
            attendance_time=datetime(2026, 7, 12, 12, 0, 0),
            machine_ip="192.168.1.10"
        )
    ])
    db_session.commit()

    response = client.get("/api/logs/date-range")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "min_date": "2026-07-10",
        "max_date": "2026-07-15"
    }
