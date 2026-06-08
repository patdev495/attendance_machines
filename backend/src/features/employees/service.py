from sqlalchemy.orm import Session
from database import EmployeeLocalRegistry, EmployeeMetadata, AttendanceLog, SessionLocal
from config import DEMO_MODE
from shared.hardware import get_machine_list

if not DEMO_MODE:
    from features.machines.service import delete_user_from_machine
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import logging
import io
import openpyxl
from sqlalchemy import func
from .registry_service import filter_registry_by_employee_search, reconcile_employee_local_registry

logger = logging.getLogger(__name__)

def update_registry(db: Session):
    try:
        reconcile_employee_local_registry(db)
    except Exception as e:
        logger.error(f"Error updating registry: {e}")
        db.rollback()
        raise

def delete_user_from_hardware(employee_id: str):
    """
    Deletes user ONLY from hardware, does not delete from DB.
    Uses ThreadPoolExecutor for parallel processing.
    """
    ips = get_machine_list()
    results = {}

    with ThreadPoolExecutor(max_workers=max(1, len(ips))) as executor:
        future_to_ip = {executor.submit(delete_user_from_machine, ip, employee_id): ip for ip in ips}
        for future in concurrent.futures.as_completed(future_to_ip):
            ip = future_to_ip[future]
            try:
                result = future.result()
                results[ip] = result
            except Exception as e:
                results[ip] = f"Error: {str(e)}"
    return results

def update_employee_info(employee_id: str, db_name: str, db: Session):
    """
    Updates user info in EmployeeLocalRegistry and EmployeeMetadata.
    """
    # 1. Update EmployeeLocalRegistry
    registry_entry = db.query(EmployeeLocalRegistry).filter(EmployeeLocalRegistry.employee_id == employee_id).first()
    if registry_entry:
        registry_entry.emp_name = db_name

    # 2. Update EmployeeMetadata
    meta_entry = db.query(EmployeeMetadata).filter(EmployeeMetadata.employee_id == employee_id).first()
    if meta_entry:
        meta_entry.emp_name = db_name

    db.commit()

    return {"status": "success", "message": "Updated in DB"}

def export_employees_to_excel(db: Session, search: str = None, source_status: str = None):
    query = db.query(EmployeeLocalRegistry)

    query = filter_registry_by_employee_search(query, db, search)

    if source_status:
        query = query.filter(EmployeeLocalRegistry.source_status == source_status)

    # Hanvon IDs can exceed SQL Server INT range, so do not cast employee_id.
    query = query.order_by(EmployeeLocalRegistry.employee_id.asc())
    employees = query.all()

    # Lấy thông tin chấm công gần nhất cho mỗi nhân viên
    latest_logs = db.query(
        AttendanceLog.employee_id,
        func.max(AttendanceLog.attendance_time).label('last_time')
    ).group_by(AttendanceLog.employee_id).all()
    latest_log_dict = {log.employee_id: log.last_time for log in latest_logs}

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Employees"

    headers = [
        "Mã NV (Máy CC)", "Mã NV (Đầy đủ)", "Họ và Tên", "Phòng Ban",
        "Nhóm / Chuyền", "Ngày vào làm", "Ca làm việc", "Nguồn dữ liệu", "Lần chấm công gần nhất"
    ]
    ws.append(headers)

    for emp in employees:
        last_time = latest_log_dict.get(emp.employee_id)
        ws.append([
            emp.employee_id,
            emp.full_emp_id or "",
            emp.emp_name or "",
            emp.department or "",
            emp.group_name or "",
            (emp.start_date if emp.start_date and emp.start_date.year > 1970 else ""),
            emp.shift or "",
            emp.source_status or "",
            last_time if last_time else ""
        ])

        # Định dạng lại cột Ngày (cột 6) và cột Thời gian (cột 9) theo chuẩn Date/Time của Excel
        current_row = ws.max_row
        if emp.start_date:
            ws.cell(row=current_row, column=6).number_format = 'yyyy-mm-dd'
        if last_time:
            ws.cell(row=current_row, column=9).number_format = 'yyyy-mm-dd hh:mm:ss'

    # Auto-adjust column widths
    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[col_letter].width = adjusted_width

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
