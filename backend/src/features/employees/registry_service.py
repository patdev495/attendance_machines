from typing import Iterable, Optional

from sqlalchemy import func, true
from sqlalchemy.orm import Session

from compat import safe_ilike
from config import DEMO_MODE
from database import AttendanceLog, EmployeeLocalRegistry, EmployeeMetadata, EmployeeOffboarding


SOURCE_EXCEL_SYNCED = "excel_synced"
SOURCE_MACHINE_ONLY = "machine_only"
SOURCE_LOG_ONLY = "log_only"
REPORT_SOURCE_STATUSES = (SOURCE_EXCEL_SYNCED, SOURCE_MACHINE_ONLY)


def normalize_employee_id(employee_id) -> str:
    return str(employee_id or "").strip()


def _machine_employee_ids() -> set[str]:
    if DEMO_MODE:
        return set()

    from features.machines.service import get_users_from_machine
    from shared.hardware import get_machine_list

    machine_ids = set()
    for ip in get_machine_list():
        users, status = get_users_from_machine(ip)
        if status == "Success":
            for user in users:
                employee_id = normalize_employee_id(user.get("user_id"))
                if employee_id:
                    machine_ids.add(employee_id)
    return machine_ids


def _apply_excel_metadata(registry_entry: EmployeeLocalRegistry, metadata: EmployeeMetadata) -> None:
    registry_entry.emp_name = metadata.emp_name
    registry_entry.department = metadata.department
    registry_entry.group_name = metadata.group
    registry_entry.start_date = metadata.start_date
    registry_entry.shift = metadata.shift
    registry_entry.full_emp_id = metadata.full_emp_id
    registry_entry.privilege = metadata.privilege
    registry_entry.source_status = SOURCE_EXCEL_SYNCED


def mark_employees_log_only(db: Session, employee_ids: set[str]) -> set[str]:
    marked = set()
    ordered_ids = sorted(employee_ids)
    # Keep the IN clauses below SQL Server's parameter limit.
    for offset in range(0, len(ordered_ids), 500):
        candidates = ordered_ids[offset:offset + 500]
        rows = db.query(EmployeeLocalRegistry).filter(EmployeeLocalRegistry.employee_id.in_(candidates))
        # Acquire the registry row locks before checking for existing offboarding markers.
        rows.update({EmployeeLocalRegistry.source_status: SOURCE_LOG_ONLY}, synchronize_session=False)
        batch = {employee_id for (employee_id,) in rows.with_entities(EmployeeLocalRegistry.employee_id)}
        existing = {
            employee_id
            for (employee_id,) in db.query(EmployeeOffboarding.employee_id).filter(
                EmployeeOffboarding.employee_id.in_(batch),
            )
        }
        db.add_all(EmployeeOffboarding(employee_id=employee_id) for employee_id in batch - existing)
        marked.update(batch)
    db.commit()
    return marked


def reconcile_employee_local_registry(
    db: Session,
    machine_employee_ids: Optional[Iterable[str]] = None,
) -> None:
    excel_users = {
        normalize_employee_id(emp.employee_id): emp
        for emp in db.query(EmployeeMetadata).all()
        if normalize_employee_id(emp.employee_id)
    }
    machine_users = {
        normalize_employee_id(employee_id)
        for employee_id in (machine_employee_ids if machine_employee_ids is not None else _machine_employee_ids())
        if normalize_employee_id(employee_id)
    }
    log_users = {
        normalize_employee_id(employee_id)
        for (employee_id,) in db.query(AttendanceLog.employee_id).distinct().all()
        if normalize_employee_id(employee_id)
    }
    offboarded_users = {employee_id for (employee_id,) in db.query(EmployeeOffboarding.employee_id)}

    all_active_ids = set(excel_users.keys()) | machine_users | log_users

    for registry_entry in db.query(EmployeeLocalRegistry).all():
        employee_id = normalize_employee_id(registry_entry.employee_id)
        if employee_id in offboarded_users:
            registry_entry.source_status = SOURCE_LOG_ONLY
        elif employee_id not in all_active_ids:
            db.delete(registry_entry)
        elif employee_id in excel_users:
            _apply_excel_metadata(registry_entry, excel_users[employee_id])
        elif employee_id in machine_users:
            registry_entry.source_status = SOURCE_MACHINE_ONLY
        else:
            registry_entry.source_status = SOURCE_LOG_ONLY

    db.flush()

    existing_ids = {
        normalize_employee_id(employee_id)
        for (employee_id,) in db.query(EmployeeLocalRegistry.employee_id).all()
    }
    for employee_id in all_active_ids - existing_ids:
        if employee_id in excel_users:
            registry_entry = EmployeeLocalRegistry(employee_id=employee_id)
            _apply_excel_metadata(registry_entry, excel_users[employee_id])
        elif employee_id in machine_users:
            registry_entry = EmployeeLocalRegistry(
                employee_id=employee_id,
                source_status=SOURCE_MACHINE_ONLY,
            )
        else:
            registry_entry = EmployeeLocalRegistry(
                employee_id=employee_id,
                source_status=SOURCE_LOG_ONLY,
            )
        db.add(registry_entry)

    db.commit()


def find_employee_ids_for_search(
    db: Session,
    search: str,
    *,
    include_metadata: bool = True,
) -> set[str]:
    search = normalize_employee_id(search)
    if not search:
        return set()

    words = search.split()
    if not words:
        return set()

    registry_conditions = []
    for word in words:
        registry_conditions.append(
            EmployeeLocalRegistry.employee_id.ilike(f"%{word}%")
            | EmployeeLocalRegistry.full_emp_id.ilike(f"%{word}%")
            | safe_ilike(EmployeeLocalRegistry.emp_name, f"%{word}%")
        )
    registry_rows = db.query(EmployeeLocalRegistry.employee_id).filter(*registry_conditions).all()
    found_ids = {normalize_employee_id(row[0]) for row in registry_rows}

    if include_metadata:
        metadata_conditions = []
        for word in words:
            metadata_conditions.append(
                EmployeeMetadata.employee_id.ilike(f"%{word}%")
                | EmployeeMetadata.full_emp_id.ilike(f"%{word}%")
                | safe_ilike(EmployeeMetadata.emp_name, f"%{word}%")
            )
        metadata_rows = db.query(EmployeeMetadata.employee_id).filter(*metadata_conditions).all()
        found_ids |= {normalize_employee_id(row[0]) for row in metadata_rows}

    found_ids.add(search)
    return {employee_id for employee_id in found_ids if employee_id}


def filter_registry_by_employee_search(query, db: Session, search: Optional[str]):
    search = normalize_employee_id(search)
    if not search:
        return query

    words = search.split()
    if not words:
        return query

    conditions = []
    for word in words:
        conditions.append(
            EmployeeLocalRegistry.employee_id.ilike(f"%{word}%")
            | EmployeeLocalRegistry.full_emp_id.ilike(f"%{word}%")
            | safe_ilike(EmployeeLocalRegistry.emp_name, f"%{word}%")
        )
    return query.filter(*conditions)


def employee_name_map(db: Session, employee_ids: Iterable[str]) -> dict[str, str]:
    normalized_ids = {normalize_employee_id(employee_id) for employee_id in employee_ids}
    normalized_ids.discard("")
    if not normalized_ids:
        return {}

    registry_rows = db.query(
        EmployeeLocalRegistry.employee_id,
        EmployeeLocalRegistry.emp_name,
    ).filter(EmployeeLocalRegistry.employee_id.in_(list(normalized_ids))).all()
    names = {
        normalize_employee_id(row.employee_id): row.emp_name
        for row in registry_rows
        if row.emp_name
    }

    missing_ids = normalized_ids - set(names.keys())
    if missing_ids:
        metadata_rows = db.query(
            EmployeeMetadata.employee_id,
            EmployeeMetadata.emp_name,
        ).filter(EmployeeMetadata.employee_id.in_(list(missing_ids))).all()
        names.update({
            normalize_employee_id(row.employee_id): row.emp_name
            for row in metadata_rows
            if row.emp_name
        })

    return names


def employee_keyword_query(db: Session, model, words: list[str]):
    conditions = [
        model.employee_id.ilike(f"%{word}%")
        | model.full_emp_id.ilike(f"%{word}%")
        | safe_ilike(model.emp_name, f"%{word}%")
        for word in words
    ]
    return db.query(model.employee_id.label("employee_id")).filter(*conditions)


def employee_search_filter(db: Session, search: str, column):
    """
    Returns an SQLAlchemy filter clause matching employees by keyword search.
    The filter is applied to the given `column`.
    """
    search = normalize_employee_id(search)
    if not search:
        return true()

    words = search.split()
    if not words:
        return true()

    registry_subquery = employee_keyword_query(db, EmployeeLocalRegistry, words).scalar_subquery()
    metadata_subquery = employee_keyword_query(db, EmployeeMetadata, words).scalar_subquery()

    return (
        column.in_(registry_subquery)
        | column.in_(metadata_subquery)
        | column.ilike(f"%{search}%")
    )

