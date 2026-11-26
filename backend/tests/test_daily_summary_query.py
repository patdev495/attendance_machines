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

def test_daily_summary_night_lunch_does_not_read_employee_history(client, db_session):
    from datetime import time, timedelta

    from database import EmployeeDailyShifts, ShiftDefinition

    employee_id = "NIGHT-001"
    work_date = date(2026, 9, 10)
    db_session.add_all([
        EmployeeLocalRegistry(employee_id=employee_id, source_status="excel_synced", shift="D"),
        EmployeeDailyShifts(employee_id=employee_id, work_date=work_date, shift_code="D"),
        ShiftDefinition(shift_code="D", start_time=time(20), end_time=time(5), is_night_shift=True),
    ])
    taps = [
        datetime(2026, 9, 10, 20),
        datetime(2026, 9, 10, 23, 20),
        datetime(2026, 9, 11, 0, 10),
        datetime(2026, 9, 11, 5),
    ]
    taps.extend(taps[0] - timedelta(days=7, minutes=i) for i in range(500))
    db_session.add_all(
        AttendanceLog(
            employee_id=employee_id, attendance_date=tap.date(),
            attendance_time=tap, machine_ip="10.0.0.1",
        )
        for tap in taps
    )
    db_session.flush()

    connection = db_session.connection().connection.driver_connection
    original_factory = connection.row_factory
    returned_rows = 0

    def count_rows(cursor, row):
        nonlocal returned_rows
        returned_rows += 1
        return original_factory(cursor, row) if original_factory else row

    connection.row_factory = count_rows
    try:
        response = client.get("/api/daily-summary", params={
            "start_date": work_date.isoformat(), "end_date": work_date.isoformat(),
        })
    finally:
        connection.row_factory = original_factory

    assert response.status_code == 200
    item, = response.json()["items"]
    assert item["lunch_out"] == "2026-09-10T23:20:00"
    assert item["lunch_in"] == "2026-09-11T00:10:00"
    assert item["lunch_duration_minutes"] == 50
    assert returned_rows < 50


def test_daily_summary_filters_before_paging_and_only_reads_lunch_for_page(client, db_session):
    from datetime import time

    from database import ShiftDefinition

    work_date = date(2026, 9, 10)
    db_session.add(ShiftDefinition(shift_code="N", start_time=time(8), end_time=time(17), work_hours=8))
    for index in range(60):
        employee_id = f"FILTER-{index:03}"
        db_session.add(EmployeeLocalRegistry(employee_id=employee_id, source_status="excel_synced", shift="N"))
        hours = [8] if index < 20 else [8, 11, 12, 15 if index < 40 else 17]
        db_session.add_all(
            AttendanceLog(
                employee_id=employee_id, attendance_date=work_date,
                attendance_time=datetime.combine(work_date, time(hour)), machine_ip="10.0.0.1",
            )
            for hour in hours
        )
    db_session.flush()

    connection = db_session.connection().connection.driver_connection
    original_factory = connection.row_factory
    returned_rows = 0

    def count_rows(cursor, row):
        nonlocal returned_rows
        returned_rows += 1
        return original_factory(cursor, row) if original_factory else row

    connection.row_factory = count_rows
    try:
        response = client.get("/api/daily-summary", params={
            "start_date": work_date.isoformat(), "end_date": work_date.isoformat(),
            "employee_id": "FILTER-", "min_hours": 4, "early_departure": True,
            "page": 2, "size": 2,
        })
    finally:
        connection.row_factory = original_factory

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_count"] == 20
    assert payload["total_pages"] == 10
    assert [item["employee_id"] for item in payload["items"]] == ["FILTER-022", "FILTER-023"]
    assert [item["lunch_duration_minutes"] for item in payload["items"]] == [60, 60]
    assert returned_rows < 100


def test_daily_summary_partial_name_keeps_matches_from_both_employee_sources(client, db_session):
    from database import EmployeeMetadata

    work_date = date(2026, 9, 10)
    for index in range(300):
        employee_id = f"SEARCH-{index:03}"
        db_session.add(EmployeeLocalRegistry(
            employee_id=employee_id, emp_name="Alex Example" if index == 1 else "Other Name",
            source_status="excel_synced",
        ))
        db_session.add(EmployeeMetadata(
            employee_id=employee_id, emp_name="Alexa Example" if index == 2 else "Legacy Name",
        ))
    db_session.flush()

    connection = db_session.connection().connection.driver_connection
    statement_steps = 0

    def count_steps():
        nonlocal statement_steps
        statement_steps += 1000
        return 0

    connection.set_progress_handler(count_steps, 1000)
    try:
        response = client.get("/api/daily-summary", params={
            "start_date": work_date.isoformat(), "end_date": work_date.isoformat(),
            "employee_id": "lex exa", "status": "excel_synced", "size": 1,
        })
    finally:
        connection.set_progress_handler(None, 0)

    assert response.status_code == 200
    assert response.json()["total_count"] == 2
    assert [item["employee_id"] for item in response.json()["items"]] == ["SEARCH-001"]
    assert statement_steps < 15_000


def test_daily_summary_combines_logs_roster_and_absences_with_bounded_work(client, db_session):
    from datetime import time, timedelta

    from database import EmployeeDailyShifts, ShiftDefinition

    work_date = date(2026, 9, 10)
    db_session.add(ShiftDefinition(shift_code="N", start_time=time(8), end_time=time(17), work_hours=8))
    db_session.add_all([
        EmployeeLocalRegistry(employee_id="A", source_status="excel_synced", shift="N"),
        EmployeeLocalRegistry(employee_id="B", source_status="excel_synced", shift="N"),
        EmployeeDailyShifts(employee_id="A", work_date=work_date, shift_code="N"),
    ])
    for day in (work_date, work_date - timedelta(days=1)):
        db_session.add_all(
            AttendanceLog(
                employee_id="A", attendance_date=day,
                attendance_time=datetime.combine(day, time(8)) + timedelta(minutes=i),
                machine_ip="10.0.0.1",
            )
            for i in range(450)
        )
    db_session.flush()

    connection = db_session.connection().connection.driver_connection
    statement_steps = 0

    def count_steps():
        nonlocal statement_steps
        statement_steps += 1000
        return 0

    connection.set_progress_handler(count_steps, 1000)
    try:
        response = client.get("/api/daily-summary", params={
            "start_date": work_date.isoformat(), "end_date": work_date.isoformat(),
            "shift": "N", "status": "excel_synced",
        })
    finally:
        connection.set_progress_handler(None, 0)

    assert response.status_code == 200
    assert response.json()["total_count"] == 2
    assert [(item["employee_id"], item["tap_count"]) for item in response.json()["items"]] == [
        ("A", 450), ("B", 0),
    ]
    assert statement_steps < 195_000


def test_unassigned_employee_uses_day_shift_regardless_of_roster_source(client, db_session):
    from datetime import time

    from database import ShiftDefinition

    work_date = date(2026, 11, 25)
    db_session.add(ShiftDefinition(shift_code="N", start_time=time(9), end_time=time(18), work_hours=7))
    for source in ("excel_synced", "machine_only", "log_only"):
        db_session.add(EmployeeLocalRegistry(employee_id=source, source_status=source, shift="D"))
        db_session.add_all(
            AttendanceLog(
                employee_id=source, attendance_date=work_date,
                attendance_time=datetime(2026, 11, 25, hour, minute), machine_ip="10.0.0.1",
            )
            for hour, minute in ((7, 39), (20, 2))
        )
    db_session.flush()

    response = client.get("/api/daily-summary", params={
        "start_date": work_date.isoformat(), "end_date": work_date.isoformat(),
    })

    assert response.status_code == 200
    assert {
        item["employee_id"]: (item["shift"], item["work_status"], item["work_hours"], item["hours_ot"])
        for item in response.json()["items"]
    } == {source: ("N", "OK", 8, 3) for source in ("excel_synced", "machine_only", "log_only")}


def test_workshop_one_uses_twelve_hour_day_and_night_shifts_without_overtime(client, db_session):
    from datetime import time, timedelta

    from database import EmployeeDailyShifts, ShiftDefinition

    work_date = date(2026, 11, 25)
    db_session.add_all([
        ShiftDefinition(shift_code="N12", start_time=time(8), end_time=time(20),
                        ot_start_time=time(21), work_hours=12),
        ShiftDefinition(shift_code="D12", start_time=time(20), end_time=time(8),
                        ot_start_time=time(9), is_night_shift=True, break_hours=1, work_hours=12),
        EmployeeDailyShifts(employee_id="night", work_date=work_date, shift_code="D"),
    ])
    for employee, taps in {
        "day": [datetime.combine(work_date, time(7, 36)), datetime.combine(work_date, time(22, 30))],
        "night": [datetime.combine(work_date, time(19, 50)),
                  datetime.combine(work_date + timedelta(days=1), time(9, 30))],
    }.items():
        db_session.add(EmployeeLocalRegistry(
            employee_id=employee, department="X\u01b0\u1edfng 1\u4e00\u90e8", source_status="machine_only",
        ))
        db_session.add_all(
            AttendanceLog(employee_id=employee, attendance_date=tap.date(), attendance_time=tap,
                          machine_ip="10.0.0.1")
            for tap in taps
        )
    db_session.flush()
    params = {"start_date": work_date.isoformat(), "end_date": work_date.isoformat()}

    response = client.get("/api/daily-summary", params=params)
    assert response.status_code == 200
    assert {
        item["employee_id"]: (item["shift"], item["work_status"], item["work_hours"], item["hours_ot"])
        for item in response.json()["items"]
    } == {"day": ("N12", "OK", 12, 0), "night": ("D12", "OK", 12, 0)}

    filtered = client.get("/api/daily-summary", params={**params, "shift": "D12"})
    night, = filtered.json()["items"]
    assert night["last_tap"] == "2026-11-26T09:30:00"
