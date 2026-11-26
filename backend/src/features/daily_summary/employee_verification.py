import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Lock
from time import monotonic

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import config
from database import EmployeeLocalRegistry, EmployeeOffboarding
from features.employees.registry_service import (
    SOURCE_LOG_ONLY, SOURCE_MACHINE_ONLY, employee_search_filter, normalize_employee_id,
)
from features.machines.service import get_users_from_machine
from shared import hardware

from .report_query import build_log_work_date_subquery


logger = logging.getLogger(__name__)
_machine_reads = ThreadPoolExecutor(max_workers=4, thread_name_prefix="report-roster")
_locks_guard = Lock()
_roster_locks: dict[str, Lock] = {}
_roster_cache: dict[str, tuple[float, set[str]]] = {}


def _machine_roster(ip: str) -> set[str]:
    # Repeated report requests share a roster read, including short offline backoff.
    with _locks_guard:
        lock = _roster_locks.setdefault(ip, Lock())
    with lock:
        cached = _roster_cache.get(ip)
        if cached and cached[0] > monotonic():
            return cached[1]
        users, status = get_users_from_machine(ip)
        available = status == "Success"
        employee_ids = {normalize_employee_id(user.get("user_id")) for user in users} if available else set()
        _roster_cache[ip] = (monotonic() + (120 if available else 30), employee_ids)
        return employee_ids


def verify_report_employees(bind, start_date: date, end_date: date, employee_search: str | None = None) -> None:
    if config.DEMO_MODE:
        return
    try:
        with Session(bind) as db:
            logs = build_log_work_date_subquery(
                db, start_date, end_date, include_machine_ip=True,
                use_registry_shift_fallback=True, date_padding_days=1,
            )
            candidates = (
                db.query(logs.c.employee_id, logs.c.machine_ip)
                .outerjoin(EmployeeLocalRegistry, EmployeeLocalRegistry.employee_id == logs.c.employee_id)
                .filter(
                    logs.c.work_date.between(start_date, end_date),
                    logs.c.employee_id.not_in(select(EmployeeOffboarding.employee_id)),
                    employee_search_filter(db, employee_search, logs.c.employee_id),
                    or_(EmployeeLocalRegistry.employee_id.is_(None),
                        EmployeeLocalRegistry.source_status == SOURCE_LOG_ONLY),
                )
                .distinct()
                .all()
            )
        pending = {normalize_employee_id(employee_id) for employee_id, _ in candidates}
        pending.discard("")
        if not pending:
            return

        machines = set(hardware.get_machine_list())
        sources = machines & {ip for _, ip in candidates}
        roster = set().union(*_machine_reads.map(_machine_roster, sources))
        if pending - roster:
            roster.update(*_machine_reads.map(_machine_roster, machines - sources))
        confirmed = pending & roster

        if not confirmed:
            return
        with Session(bind) as db:
            for employee_id in sorted(confirmed):
                try:
                    with db.begin_nested():
                        registry_entry = db.get(EmployeeLocalRegistry, employee_id)
                        if registry_entry is None:
                            db.add(EmployeeLocalRegistry(employee_id=employee_id, source_status=SOURCE_MACHINE_ONLY))
                        elif registry_entry.source_status == SOURCE_LOG_ONLY:
                            db.execute(update(EmployeeLocalRegistry).where(
                                EmployeeLocalRegistry.employee_id == employee_id,
                                EmployeeLocalRegistry.source_status == SOURCE_LOG_ONLY,
                                EmployeeLocalRegistry.employee_id.not_in(select(EmployeeOffboarding.employee_id)),
                            ).values(source_status=SOURCE_MACHINE_ONLY))
                except IntegrityError:
                    if db.get(EmployeeLocalRegistry, employee_id) is None:
                        raise
            db.commit()
    except Exception:
        logger.exception("Could not verify Daily Summary employees for %s through %s", start_date, end_date)
