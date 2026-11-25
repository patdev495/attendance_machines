from datetime import date, time, timedelta
from typing import NamedTuple, Optional, Any

from sqlalchemy import Date, Time, case, func, literal, null, or_, select, text, true, union_all
from sqlalchemy.orm import Session, aliased

from database import (
    AttendanceLog,
    EmployeeDailyShifts,
    EmployeeLocalRegistry,
    EmployeeMetadata,
)
from features.employees.registry_service import SOURCE_EXCEL_SYNCED, SOURCE_LOG_ONLY, employee_keyword_query


class DailySummaryQueryParts(NamedTuple):
    query: Any
    summary_days: Any


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
    employee_ids=None,
    employee_search: Optional[str] = None,
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
            (
                today_shift_code.is_(None) & yest_shift_code.is_(None),
                func.cast(AttendanceLog.attendance_time, Date),
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
    if employee_ids is not None:
        log_filter.append(
            or_(
                AttendanceLog.employee_id.in_(select(employee_ids.c.employee_id)),
                AttendanceLog.employee_id.ilike(f"%{employee_search.strip()}%"),
            )
        )
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
    employee_ids=None,
    employee_search: Optional[str] = None,
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
    if employee_ids is not None:
        query = query.filter(
            or_(
                EmployeeDailyShifts.employee_id.in_(select(employee_ids.c.employee_id)),
                EmployeeDailyShifts.employee_id.ilike(f"%{employee_search.strip()}%"),
            )
        )
    return query.subquery(name)


def build_matching_employee_ids_subquery(db: Session, employee_search: Optional[str]):
    """Return only Employee IDs matching the Daily Summary search input.

    This is deliberately shared by every source query so an Employee search
    constrains Raw Logs, roster rows, and registry-generated dates before any
    expensive aggregation or union takes place.
    """
    if not employee_search or not employee_search.strip():
        return None

    words = employee_search.split()
    registry_ids = employee_keyword_query(db, EmployeeLocalRegistry, words)
    metadata_ids = employee_keyword_query(db, EmployeeMetadata, words)
    return registry_ids.union(metadata_ids).cte("matching_employee_ids")


def build_daily_summary_query(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    employee_search: Optional[str] = None,
) -> DailySummaryQueryParts:
    matching_employee_ids = build_matching_employee_ids_subquery(db, employee_search)
    base_calc_sub = build_log_work_date_subquery(
        db,
        start_date,
        end_date,
        include_machine_ip=True,
        use_registry_shift_fallback=True,
        date_padding_days=1,
        employee_ids=matching_employee_ids,
        employee_search=employee_search,
    )
    agg_logs_sub = build_aggregated_logs_subquery(db, base_calc_sub)
    roster_sub = build_roster_subquery(
        db, start_date, end_date, employee_ids=matching_employee_ids, employee_search=employee_search
    )

    roster_keys = db.query(
        roster_sub.c.employee_id.label("employee_id"),
        roster_sub.c.work_date.label("work_date"),
        null(), null(), null(), null(),
        roster_sub.c.shift_code,
    )

    registry_keys = None
    if start_date and end_date:
        report_dates = date_range_subquery(db, start_date, end_date)
        registry_keys = db.query(
            EmployeeLocalRegistry.employee_id.label("employee_id"),
            report_dates.c.work_date.label("work_date"),
            null(), null(), null(), null(), null(),
        ).select_from(EmployeeLocalRegistry).join(
            report_dates,
            true(),
        ).filter(EmployeeLocalRegistry.source_status == SOURCE_EXCEL_SYNCED)
        if matching_employee_ids is not None:
            registry_keys = registry_keys.filter(
                EmployeeLocalRegistry.employee_id.in_(
                    select(matching_employee_ids.c.employee_id)
                )
            )

    log_days = db.query(
        agg_logs_sub.c.employee_id,
        agg_logs_sub.c.work_date,
        agg_logs_sub.c.first_tap,
        agg_logs_sub.c.last_tap,
        agg_logs_sub.c.tap_count,
        agg_logs_sub.c.machine_ip,
        null().label("shift_code"),
    )
    if start_date:
        log_days = log_days.filter(agg_logs_sub.c.work_date >= start_date)
    if end_date:
        log_days = log_days.filter(agg_logs_sub.c.work_date <= end_date)

    # Raw Logs and roster each contribute at most one row per employee/day.
    # Combine their values in one pass, including days with no Raw Logs.
    union_parts = [log_days, roster_keys]
    if registry_keys is not None:
        union_parts.append(registry_keys)
    source_days = union_all(*(part.statement for part in union_parts)).subquery("source_days")
    summary_days = db.query(
        source_days.c.employee_id,
        source_days.c.work_date,
        func.max(source_days.c.first_tap).label("first_tap"),
        func.max(source_days.c.last_tap).label("last_tap"),
        func.max(source_days.c.tap_count).label("tap_count"),
        func.max(source_days.c.machine_ip).label("machine_ip"),
        func.max(source_days.c.shift_code).label("shift_code"),
    ).group_by(source_days.c.employee_id, source_days.c.work_date).subquery("summary_days")

    query = db.query(
        summary_days.c.employee_id,
        summary_days.c.work_date,
        summary_days.c.first_tap,
        summary_days.c.last_tap,
        func.coalesce(summary_days.c.tap_count, 0).label("tap_count"),
        func.coalesce(summary_days.c.shift_code, EmployeeLocalRegistry.shift, EmployeeMetadata.shift).label("shift"),
        func.coalesce(EmployeeLocalRegistry.emp_name, EmployeeMetadata.emp_name).label("emp_name"),
        func.coalesce(EmployeeLocalRegistry.full_emp_id, EmployeeMetadata.full_emp_id).label("full_emp_id"),
        func.coalesce(EmployeeLocalRegistry.department, EmployeeMetadata.department).label("department"),
        func.coalesce(EmployeeLocalRegistry.source_status, SOURCE_LOG_ONLY).label("status"),
        summary_days.c.shift_code.label("daily_shift_code"),
    ).outerjoin(
        EmployeeLocalRegistry,
        summary_days.c.employee_id == EmployeeLocalRegistry.employee_id,
    ).outerjoin(
        EmployeeMetadata,
        summary_days.c.employee_id == EmployeeMetadata.employee_id,
    )

    return DailySummaryQueryParts(query, summary_days)
