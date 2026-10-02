from datetime import date, datetime

from sqlalchemy.dialects import sqlite

from database import AttendanceLog, EmployeeLocalRegistry
from features.daily_summary.report_query import build_daily_summary_query


def test_employee_search_is_applied_before_daily_summary_aggregation(db_session):
    """A targeted Employee search must constrain source rows, not only final rows."""
    parts = build_daily_summary_query(
        db_session,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 30),
        employee_search="EMP-001",
    )

    compiled = str(
        parts.query.statement.compile(
            dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
        )
    )

    # The predicate has to occur in both source paths.  If it only appears after
    # union_keys, SQL must aggregate every Employee's Raw Logs before filtering.
    assert compiled.count('"AttendanceLogs".employee_id IN') >= 1
    assert compiled.count('"EmployeeDailyShifts".employee_id IN') >= 1


def test_daily_summary_employee_search_preserves_pagination(client, db_session):
    db_session.add_all([
        EmployeeLocalRegistry(
            employee_id="EMP-001",
            emp_name="Target Employee",
            source_status="excel_synced",
        ),
        EmployeeLocalRegistry(
            employee_id="EMP-002",
            emp_name="Other Employee",
            source_status="excel_synced",
        ),
        AttendanceLog(
            employee_id="EMP-001",
            attendance_date=date(2026, 9, 1),
            attendance_time=datetime(2026, 9, 1, 8, 0),
            machine_ip="10.0.0.1",
        ),
    ])
    db_session.flush()

    response = client.get(
        "/api/daily-summary",
        params={
            "start_date": "2026-09-01",
            "end_date": "2026-09-03",
            "employee_id": "EMP-001",
            "page": 2,
            "size": 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_count"] == 3
    assert payload["total_pages"] == 2
    assert payload["page"] == 2
    assert [item["employee_id"] for item in payload["items"]] == ["EMP-001"]
