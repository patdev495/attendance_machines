from datetime import date, time, timedelta
from typing import NamedTuple, Optional

from sqlalchemy import Date, Time, case, func, literal, text, true, union_all
from sqlalchemy.orm import Session, aliased

from database import (
    AttendanceLog,
    EmployeeDailyShifts,
    EmployeeLocalRegistry,
    EmployeeMetadata,
)
from features.employees.registry_service import REPORT_SOURCE_STATUSES


class DailySummaryQueryParts(NamedTuple):
    query: object
    union_keys: object
    agg_logs_sub: object
    roster_sub: object


def date_range_subquery(
    db: Session,
    start_date: date,
    end_date: date,
    name: str = "report_dates",
):
    current = start_date
    selects = []
    while current <= end_date:
        selects.append(db.query(literal(current).label("work_date")))
        current += timedelta(days=1)
    if not selects:
        selects.append(db.query(literal(start_date).label("work_date")))
    return union_all(*selects).subquery(name)


def _trimmed(value):
    return func.ltrim(func.rtrim(value))


def build_log_work_date_subquery(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    *,
    include_machine_ip: bool = False,
    include_registry_fields: bool = False,
    use_registry_shift_fallback: bool = False,
    trim_employee_joins: bool = False,
    date_padding_days: int = 0,
    name: str = "base_calc",
):
    today_shift = aliased(EmployeeDailyShifts)
    yest_shift = aliased(EmployeeDailyShifts)

    today_shift_code = today_shift.shift_code
    yest_shift_code = yest_shift.shift_code
    if use_registry_shift_fallback:
        today_shift_code = func.coalesce(today_shift.shift_code, EmployeeLocalRegistry.shift)
        yest_shift_code = func.coalesce(yest_shift.shift_code, EmployeeLocalRegistry.shift)

    columns = [
        AttendanceLog.id,
        AttendanceLog.attendance_time,
        AttendanceLog.employee_id,
    ]
    if include_machine_ip:
        columns.append(AttendanceLog.machine_ip)
    if include_registry_fields:
        columns.extend([
            EmployeeLocalRegistry.shift,
            EmployeeLocalRegistry.department,
            EmployeeLocalRegistry.full_emp_id,
        ])

    query = db.query(
        *columns,
        case(
            (
                (func.coalesce(today_shift_code, "").like("%D%"))
                & (func.cast(AttendanceLog.attendance_time, Time) < time(12, 0)),
                func.cast(func.dateadd(text("day"), text("-1"), AttendanceLog.attendance_time), Date),
            ),
            (
                (func.coalesce(today_shift_code, "").like("%D%"))
                & (func.cast(AttendanceLog.attendance_time, Time) >= time(18, 0)),
                func.cast(AttendanceLog.attendance_time, Date),
            ),
            (
                (func.coalesce(yest_shift_code, "").like("%D%"))
                & (func.cast(AttendanceLog.attendance_time, Time) < time(10, 0)),
                func.cast(func.dateadd(text("day"), text("-1"), AttendanceLog.attendance_time), Date),
            ),
            else_=func.cast(func.dateadd(text("hour"), text("-3"), AttendanceLog.attendance_time), Date),
        ).label("work_date"),
    )

    if include_registry_fields or use_registry_shift_fallback:
        left_id = AttendanceLog.employee_id
        right_id = EmployeeLocalRegistry.employee_id
        if trim_employee_joins:
            left_id = _trimmed(left_id)
            right_id = _trimmed(right_id)
        query = query.outerjoin(EmployeeLocalRegistry, left_id == right_id)

    today_log_id = AttendanceLog.employee_id
    today_roster_id = today_shift.employee_id
    yest_log_id = AttendanceLog.employee_id
    yest_roster_id = yest_shift.employee_id
    if trim_employee_joins:
        today_log_id = _trimmed(today_log_id)
        today_roster_id = _trimmed(today_roster_id)
        yest_log_id = _trimmed(yest_log_id)
        yest_roster_id = _trimmed(yest_roster_id)

    query = query.outerjoin(
        today_shift,
        (today_log_id == today_roster_id)
        & (func.cast(AttendanceLog.attendance_time, Date) == today_shift.work_date),
    ).outerjoin(
        yest_shift,
        (yest_log_id == yest_roster_id)
        & (
            func.cast(func.dateadd(text("day"), text("-1"), AttendanceLog.attendance_time), Date)
            == yest_shift.work_date
        ),
    )

    log_filter = []
    if start_date:
        log_filter.append(AttendanceLog.attendance_date >= (start_date - timedelta(days=date_padding_days)))
    if end_date:
        log_filter.append(AttendanceLog.attendance_date <= (end_date + timedelta(days=date_padding_days)))
    if log_filter:
        query = query.filter(*log_filter)

    return query.subquery(name)


def build_aggregated_logs_subquery(db: Session, base_calc_sub, name: str = "agg_logs"):
    return db.query(
        base_calc_sub.c.employee_id,
        base_calc_sub.c.work_date,
        func.min(base_calc_sub.c.attendance_time).label("first_tap"),
        func.max(base_calc_sub.c.attendance_time).label("last_tap"),
        func.count(base_calc_sub.c.id).label("tap_count"),
        func.max(base_calc_sub.c.machine_ip).label("machine_ip"),
    ).group_by(base_calc_sub.c.employee_id, base_calc_sub.c.work_date).subquery(name)


def build_roster_subquery(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    name: str = "roster",
):
    query = db.query(
        EmployeeDailyShifts.employee_id,
        EmployeeDailyShifts.work_date,
        EmployeeDailyShifts.shift_code,
    )
    if start_date:
        query = query.filter(EmployeeDailyShifts.work_date >= start_date)
    if end_date:
        query = query.filter(EmployeeDailyShifts.work_date <= end_date)
    return query.subquery(name)


def build_daily_summary_query(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> DailySummaryQueryParts:
    base_calc_sub = build_log_work_date_subquery(
        db,
        start_date,
        end_date,
        include_machine_ip=True,
        date_padding_days=1,
    )
    agg_logs_sub = build_aggregated_logs_subquery(db, base_calc_sub)
    roster_sub = build_roster_subquery(db, start_date, end_date)

    roster_keys = db.query(
        roster_sub.c.employee_id.label("employee_id"),
        roster_sub.c.work_date.label("work_date"),
    )

    registry_keys = None
    if start_date and end_date:
        report_dates = date_range_subquery(db, start_date, end_date)
        registry_keys = db.query(
            EmployeeLocalRegistry.employee_id.label("employee_id"),
            report_dates.c.work_date.label("work_date"),
        ).select_from(EmployeeLocalRegistry).join(
            report_dates,
            true(),
        ).filter(EmployeeLocalRegistry.source_status.in_(REPORT_SOURCE_STATUSES))

    log_keys = db.query(
        agg_logs_sub.c.employee_id.label("employee_id"),
        agg_logs_sub.c.work_date.label("work_date"),
    )
    if start_date:
        log_keys = log_keys.filter(agg_logs_sub.c.work_date >= start_date)
    if end_date:
        log_keys = log_keys.filter(agg_logs_sub.c.work_date <= end_date)

    union_parts = [roster_keys, log_keys]
    if registry_keys is not None:
        union_parts.insert(0, registry_keys)
    union_keys = union_parts[0].union(*union_parts[1:]).subquery("union_keys")

    query = db.query(
        union_keys.c.employee_id,
        union_keys.c.work_date,
        agg_logs_sub.c.first_tap,
        agg_logs_sub.c.last_tap,
        func.coalesce(agg_logs_sub.c.tap_count, 0).label("tap_count"),
        func.coalesce(roster_sub.c.shift_code, EmployeeLocalRegistry.shift, EmployeeMetadata.shift).label("shift"),
        func.coalesce(EmployeeLocalRegistry.emp_name, EmployeeMetadata.emp_name).label("emp_name"),
        func.coalesce(EmployeeLocalRegistry.full_emp_id, EmployeeMetadata.full_emp_id).label("full_emp_id"),
        func.coalesce(EmployeeLocalRegistry.department, EmployeeMetadata.department).label("department"),
        func.coalesce(EmployeeLocalRegistry.source_status, "machine_only").label("status"),
        roster_sub.c.shift_code.label("daily_shift_code"),
    ).outerjoin(
        agg_logs_sub,
        (union_keys.c.employee_id == agg_logs_sub.c.employee_id)
        & (union_keys.c.work_date == agg_logs_sub.c.work_date),
    ).outerjoin(
        roster_sub,
        (union_keys.c.employee_id == roster_sub.c.employee_id)
        & (union_keys.c.work_date == roster_sub.c.work_date),
    ).outerjoin(
        EmployeeLocalRegistry,
        union_keys.c.employee_id == EmployeeLocalRegistry.employee_id,
    ).outerjoin(
        EmployeeMetadata,
        union_keys.c.employee_id == EmployeeMetadata.employee_id,
    ).filter(EmployeeLocalRegistry.source_status.in_(REPORT_SOURCE_STATUSES))

    return DailySummaryQueryParts(query, union_keys, agg_logs_sub, roster_sub)
