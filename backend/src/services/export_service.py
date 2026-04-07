import os
import threading
import tempfile
from datetime import date, datetime, timedelta
from sqlalchemy import text, func, Date, case
from openpyxl import Workbook
from openpyxl.styles import Font, Border, Side, Alignment, PatternFill
from openpyxl.utils import get_column_letter

from ..database import AttendanceLog, EmployeeMetadata, SessionLocal
from ..utils.stats_utils import compute_day_stats

export_status = {
    "is_running": False,
    "progress": 0,
    "total": 0,
    "current_step": "",
    "cancel_requested": False,
    "filename": None,
    "error": None
}
export_lock = threading.Lock()

def run_export_task(start_date: date, end_date: date, view_mode: str):
    global export_status
    
    db = SessionLocal()
    try:
        with export_lock:
            export_status.update({
                "is_running": True, "progress": 0, "total": 0, 
                "current_step": "Fetching data...", "cancel_requested": False, 
                "filename": None, "error": None
            })

        # Base query for attendance aggregation
        base_calc_sub = db.query(
            AttendanceLog.id,
            AttendanceLog.attendance_time,
            AttendanceLog.employee_id,
            EmployeeMetadata.shift,
            case(
                (EmployeeMetadata.shift == text("'D'"), func.cast(func.dateadd(text("hour"), text("-10"), AttendanceLog.attendance_time), Date)),
                else_=func.cast(func.dateadd(text("hour"), text("-4"), AttendanceLog.attendance_time), Date)
            ).label("work_date")
        ).outerjoin(EmployeeMetadata, AttendanceLog.employee_id == EmployeeMetadata.employee_id).subquery()
        
        query = db.query(
            base_calc_sub.c.employee_id,
            base_calc_sub.c.work_date,
            func.min(base_calc_sub.c.attendance_time).label("first_tap"),
            func.max(base_calc_sub.c.attendance_time).label("last_tap"),
            func.count(base_calc_sub.c.id).label("tap_count"),
            base_calc_sub.c.shift
        )
        query = query.filter(base_calc_sub.c.work_date >= start_date)
        query = query.filter(base_calc_sub.c.work_date <= end_date)
        query = query.group_by(
            base_calc_sub.c.employee_id, 
            base_calc_sub.c.work_date, 
            base_calc_sub.c.shift
        )
        
        results = query.all()
        if not results:
             with export_lock:
                 export_status.update({"is_running": False, "error": "No data found for this range."})
             return

        # Process results into a dictionary
        data = {}
        for row in results:
            emp_id = row.employee_id
            w_date = row.work_date
            if emp_id not in data:
                data[emp_id] = {"general_shift": row.shift, "days": {}}
            data[emp_id]["days"][w_date] = {
                "first_tap": row.first_tap, "last_tap": row.last_tap,
                "count": row.tap_count, "shift": row.shift
            }
            
        dates_list = []
        curr = start_date
        while curr <= end_date:
            dates_list.append(curr)
            curr += timedelta(days=1)
            
        wb = Workbook()
        ws = wb.active
        ws.title = "Attendance Export"
        headers = ["Mã nhân viên", "Tên nhân viên", "Phòng ban", "Nhóm", "Ngày vào làm", "Ca làm việc", "Ghi chú"]
        for d in dates_list: headers.append(f"{d.day}/{d.month}")
        ws.append(headers)

        # Style headers
        border_style = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        header_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border_style
            cell.fill = header_fill

        sorted_emp_ids = sorted(data.keys())
        emp_meta = {m.employee_id: m for m in db.query(EmployeeMetadata).filter(EmployeeMetadata.employee_id.in_(sorted_emp_ids)).all()}
        
        with export_lock:
            export_status["total"] = len(sorted_emp_ids)
            export_status["current_step"] = "Generating Sheet 1..."

        current_row = 2
        num_rows = 6 if view_mode == "both" else 4
        
        for idx, emp_id in enumerate(sorted_emp_ids):
            if export_status["cancel_requested"]: 
                with export_lock: export_status["is_running"] = False
                return
            
            with export_lock:
                export_status["progress"] = int((idx / len(sorted_emp_ids)) * 50) 

            emp_data_info = data[emp_id]
            emp_data = emp_data_info["days"]
            shift_val = emp_data_info["general_shift"]
            emp_m = emp_meta.get(emp_id)
            emp_name = emp_m.emp_name if emp_m and emp_m.emp_name else emp_id
            emp_dept = emp_m.department if emp_m and emp_m.department else "-"
            emp_group = emp_m.group if emp_m and emp_m.group else "-"
            emp_start = emp_m.start_date.strftime("%d/%m/%Y") if emp_m and emp_m.start_date else "-"
            shift_text = shift_val if shift_val else "-"

            for r_offset in range(num_rows):
                r_idx = current_row + r_offset
                is_first = (r_offset == 0)
                ws.cell(row=r_idx, column=1, value=emp_id)
                ws.cell(row=r_idx, column=2, value=emp_name)
                ws.cell(row=r_idx, column=3, value=emp_dept)
                ws.cell(row=r_idx, column=4, value=emp_group)
                ws.cell(row=r_idx, column=5, value=emp_start)
                ws.cell(row=r_idx, column=6, value=shift_text)
                
                if view_mode == "time": all_indicators = ["Giờ In", "Giờ Out", "Đi muộn (phút)", "Về sớm (phút)"]
                elif view_mode == "hours": all_indicators = ["Giờ Công", "Tăng Ca", "Đi muộn (phút)", "Về sớm (phút)"]
                else: all_indicators = ["Giờ In", "Giờ Out", "Giờ Công", "Tăng Ca", "Đi muộn (phút)", "Về sớm (phút)"]
                ws.cell(row=r_idx, column=7, value=all_indicators[r_offset])

                if not is_first:
                    for c_idx in range(1, 7):
                        ws.cell(row=r_idx, column=c_idx).font = Font(color="FFFFFF")

            for date_idx, d in enumerate(dates_list):
                col = date_idx + 8
                if d not in emp_data:
                    for i in range(num_rows): ws.cell(row=current_row+i, column=col, value="-")
                else:
                    day_stat = emp_data[d]
                    first_val, last_val, std, ot, late, early = "-", "-", "-", "-", "-", "-"
                    if day_stat["count"] >= 1: first_val = day_stat["first_tap"].strftime("%H:%M")
                    if day_stat["count"] >= 2:
                        last_val = day_stat["last_tap"].strftime("%H:%M")
                        _, std, ot, late, early = compute_day_stats(day_stat["first_tap"], day_stat["last_tap"], d, emp_m.department if emp_m else None, day_stat["shift"])
                    
                    def fmt_ot(v):
                        return v if (isinstance(v, (int, float)) and v > 0) else "-"

                    if view_mode=="time":
                        vals = [first_val, last_val, late, early]
                    elif view_mode=="hours":
                        vals = [std, fmt_ot(ot), late, early]
                    else:
                        vals = [first_val, last_val, std, fmt_ot(ot), late, early]
                    
                    for i, v in enumerate(vals): ws.cell(row=current_row+i, column=col, value=v)
            current_row += num_rows

        # Sheet 2
        with export_lock: export_status["current_step"] = "Generating Sheet 2..."
        ws2 = wb.create_sheet(title="Thông tin chi tiết")
        ws2.append(["Mã NV", "Tên nhân viên", "Phòng ban", "Nhóm", "Ca", "Ngày", "Giờ In", "Giờ Out", "Giờ Công", "Tăng Ca", "Đi muộn (phút)", "Về sớm (phút)"])
        
        for cell in ws2[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border_style
            cell.fill = header_fill
        
        for idx, emp_id in enumerate(sorted_emp_ids):
            if export_status["cancel_requested"]: 
                with export_lock: export_status["is_running"] = False
                return
            with export_lock: export_status["progress"] = 50 + int((idx / len(sorted_emp_ids)) * 50)
            
            emp_info = data[emp_id]
            emp_m = emp_meta.get(emp_id)
            for d in dates_list:
                if d not in emp_info["days"]: continue
                ds = emp_info["days"][d]
                first = ds["first_tap"].strftime("%H:%M") if ds["count"]>=1 else "-"
                last, std, ot, late, early = "-", "-", 0, "-", "-"
                if ds["count"] >= 2:
                    last = ds["last_tap"].strftime("%H:%M")
                    _, std, ot, late, early = compute_day_stats(ds["first_tap"], ds["last_tap"], d, emp_m.department if emp_m else None, ds["shift"])
                
                display_ot = ot if (isinstance(ot, (int, float)) and ot > 0) else 0
                ws2.append([emp_id, emp_m.emp_name if emp_m else emp_id, emp_m.department if emp_m else "-", emp_m.group if emp_m else "-", ds["shift"] or "N", d.strftime("%d/%m/%Y"), first, last, std, display_ot, late, early])

        # Final Formatting
        for sheet in [ws, ws2]:
            for row in sheet.iter_rows():
                for cell in row:
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                    cell.border = border_style

            for column_cells in sheet.columns:
                max_length = 0
                column_letter = get_column_letter(column_cells[0].column)
                for cell in column_cells:
                    try:
                        if cell.value:
                            lines = str(cell.value).split('\n')
                            length = max(len(line) for line in lines)
                            if length > max_length:
                                max_length = length
                    except:
                        pass
                adjusted_width = (max_length + 4) * 1.1 
                sheet.column_dimensions[column_letter].width = min(adjusted_width, 60)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        wb.save(tmp.name)
        with export_lock:
            export_status.update({"is_running": False, "progress": 100, "filename": tmp.name, "current_step": "Ready for download"})
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        with export_lock:
            export_status.update({"is_running": False, "error": str(e)})
    finally:
        db.close()
