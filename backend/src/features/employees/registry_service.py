from typing import Iterable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from compat import safe_ilike
from config import DEMO_MODE
from database import AttendanceLog, EmployeeLocalRegistry, EmployeeMetadata


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

    all_active_ids = set(excel_users.keys()) | machine_users | log_users

    for registry_entry in db.query(EmployeeLocalRegistry).all():
        employee_id = normalize_employee_id(registry_entry.employee_id)
        if employee_id not in all_active_ids:
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

    registry_rows = db.query(EmployeeLocalRegistry.employee_id).filter(
        EmployeeLocalRegistry.employee_id.ilike(f"%{search}%")
        | EmployeeLocalRegistry.full_emp_id.ilike(f"%{search}%")
        | safe_ilike(EmployeeLocalRegistry.emp_name, f"%{search}%")
    ).all()
    found_ids = {normalize_employee_id(row[0]) for row in registry_rows}

    if include_metadata:
        metadata_rows = db.query(EmployeeMetadata.employee_id).filter(
            EmployeeMetadata.employee_id.ilike(f"%{search}%")
            | EmployeeMetadata.full_emp_id.ilike(f"%{search}%")
            | safe_ilike(EmployeeMetadata.emp_name, f"%{search}%")
        ).all()
        found_ids |= {normalize_employee_id(row[0]) for row in metadata_rows}

    found_ids.add(search)
    return {employee_id for employee_id in found_ids if employee_id}


def filter_registry_by_employee_search(query, db: Session, search: Optional[str]):
    search = normalize_employee_id(search)
    if not search:
        return query

    target_ids = find_employee_ids_for_search(db, search, include_metadata=False)
    return query.filter(func.ltrim(func.rtrim(EmployeeLocalRegistry.employee_id)).in_(list(target_ids)))


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
