import sys
from pathlib import Path

from sqlalchemy import event


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import EmployeeLocalRegistry
from features.employees.router import list_employees


def test_employee_list_does_not_cast_hanvon_ids_to_int(db_session):
    db_session.add_all([
        EmployeeLocalRegistry(employee_id="5424108994762", source_status="machine_only"),
        EmployeeLocalRegistry(employee_id="1001", source_status="machine_only"),
    ])
    db_session.commit()

    statements = []

    def capture_sql(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        result = list_employees(page=1, page_size=50, db=db_session)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert result.total_count == 2
    employee_selects = [sql for sql in statements if "EmployeeLocalRegistry" in sql]
    assert employee_selects
    assert all("CAST" not in sql.upper() for sql in employee_selects)
