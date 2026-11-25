import threading
import tempfile
from datetime import date, timedelta
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, NamedStyle, PatternFill, Side
from openpyxl.utils import get_column_letter

from database import EmployeeLocalRegistry, ShiftDefinition, AttendanceLog, SessionLocal

from utils.stats_utils import compute_day_stats, parse_shift_window, FULL_DAY_LEAVE_CODES, determine_missing_tap, extract_lunch_swipes
from features.employees.registry_service import SOURCE_LOG_ONLY
from .report_query import build_daily_summary_query
from .service import needs_shift_review


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

def _get_shift_meta(shift_code, rules_pool):
    """Return (shift_category, is_night_shift) for a given shift_code.

    shift_category values: 'NORMAL' | 'HOLIDAY' | 'ROTATION'
    Defaults to ('NORMAL', False) when the code is not in rules_pool.
    """
    if rules_pool and shift_code:
        code = shift_code.strip().upper()
        for r in rules_pool:
            if r.shift_code == code:
                cat = (r.shift_category or "NORMAL").upper()
                return cat, bool(r.is_night_shift)
    return "NORMAL", False


def _sheet1_indicators(view_mode: str):
    lunch_indicators = ["Ra trưa", "Vào trưa", "Ăn trưa quá giờ (phút)"]
    if view_mode == "time":
        return ["Giờ In", "Giờ Out", *lunch_indicators, "Đi muộn (phút)", "Về sớm (phút)", "Mã công"]
    if view_mode == "hours":
        return ["Giờ Công", "Tăng Ca", *lunch_indicators, "Đi muộn (phút)", "Về sớm (phút)", "Mã công"]
    return ["Giờ In", "Giờ Out", *lunch_indicators, "Giờ Công", "Tăng Ca", "Đi muộn (phút)", "Về sớm (phút)", "Mã công"]


def _sheet1_values(day_summary: dict, view_mode: str):
    overtime = day_summary["ot"]
    display_overtime = overtime if isinstance(overtime, (int, float)) and overtime > 0 else "-"
    lunch_values = [
        day_summary.get("lunch_out_str", "-"),
        day_summary.get("lunch_in_str", "-"),
        day_summary.get("lunch_late_minutes", "-"),
    ]

    if view_mode == "time":
        return [
            day_summary["first"], day_summary["last"], *lunch_values,
            day_summary["late"], day_summary["early"], day_summary.get("shift_code", "-"),
        ]
    if view_mode == "hours":
        return [
            day_summary["std"], display_overtime, *lunch_values,
            day_summary["late"], day_summary["early"], day_summary.get("shift_code", "-"),
        ]
    return [
        day_summary["first"], day_summary["last"], *lunch_values,
        day_summary["std"], display_overtime, day_summary["late"], day_summary["early"],
        day_summary.get("shift_code", "-"),
    ]


def _sheet2_headers():
    return [
        "Mã máy", "Mã công ty", "Tên nhân viên", "Phòng ban", "Nhóm", "Ngày vào làm",
        "Ngày", "Giờ In", "Giờ Out", "Ra trưa", "Vào trưa", "Phút trưa", "Trạng thái trưa",
        "Ăn trưa quá giờ (phút)",
        "Giờ Công", "Tăng Ca", "Đi muộn (phút)", "Về sớm (phút)", "Mã công",
        "Công tiêu chuẩn", "Giờ trợ cấp ca đêm",
        "Giờ ngày thường", "Giờ ngày nghỉ lễ", "Giờ ngày nghỉ luân phiên",
        "TC thường - ca ngày", "TC lễ - ca ngày", "TC luân phiên - ca ngày",
        "TC thường - ca đêm", "TC lễ - ca đêm", "TC luân phiên - ca đêm", "Ghi chú",
    ]

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

        # Pre-fetch shift rules for extreme performance
        rules_pool = db.query(ShiftDefinition).all()


        results = build_daily_summary_query(db, start_date, end_date).query.all()
        emp_meta = {employee.employee_id: employee for employee in db.query(EmployeeLocalRegistry)}

        # Pre-fetch all raw logs for the export date range
        raw_logs = db.query(AttendanceLog).filter(
            AttendanceLog.attendance_date >= start_date - timedelta(days=1),
            AttendanceLog.attendance_date <= end_date + timedelta(days=1)
        ).all()
        logs_by_emp_date = {}
        for log in raw_logs:
            log_date = log.attendance_time.date() if hasattr(log, "attendance_time") and log.attendance_time else getattr(log, "attendance_date", None)
            key = (log.employee_id, log_date)
            if key not in logs_by_emp_date:
                logs_by_emp_date[key] = []
            logs_by_emp_date[key].append(log.attendance_time)

        processed_data = {}
        with export_lock: export_status["current_step"] = "Preparing attendance statistics..."

        for row in results:
            emp_id = row.employee_id
            w_date = row.work_date
            if emp_id not in processed_data:
                processed_data[emp_id] = {"days": {}, "name": row.emp_name, "department": row.department}

            # Get effective shift code (daily override or fallback)
            daily_code = getattr(row, 'daily_shift_code', None)
            full_emp_id = getattr(row, 'full_emp_id', None)

            # Phase 13: Map to NA if not in definitions table
            valid_codes = {r.shift_code for r in rules_pool} if rules_pool else set()
            effective_shift_raw = (daily_code or row.shift or "").strip().upper()
            known_shift = effective_shift_raw in valid_codes

            if not known_shift:
                shift_code_display = "NA"
                effective_shift = "N"
            else:
                shift_code_display = effective_shift_raw.strip().upper()
                effective_shift = shift_code_display

            emp_m = emp_meta.get(emp_id)
            department = getattr(row, 'department', None) or (emp_m.department if emp_m else None)
            shift_window = parse_shift_window(
                effective_shift, department, rules_pool=rules_pool
            )

            # Initialization for row record
            first_val, last_val = "-", "-"
            std = ot = late = early = 0
            night_subsidy = 0.0
            hp = hr = ho = ht = hc = hk = 0.0
            std_expected = 8.0
            workday_base = 8.0
            note = ""

            # Extract lunch info
            day_taps = list(logs_by_emp_date.get((emp_id, w_date), []))
            if shift_window.get('end_next_day'):
                day_taps += logs_by_emp_date.get((emp_id, w_date + timedelta(days=1)), [])
            if not day_taps and row.tap_count >= 1:
                day_taps = [row.first_tap] if row.tap_count == 1 else [row.first_tap, row.last_tap]
            lunch_info = extract_lunch_swipes(
                day_taps,
                work_date=w_date,
                is_night_shift=shift_window.get('end_next_day', False),
            )
            lunch_out_str = lunch_info["lunch_out"].strftime("%H:%M") if lunch_info["lunch_out"] else "-"
            lunch_in_str = lunch_info["lunch_in"].strftime("%H:%M") if lunch_info["lunch_in"] else "-"
            lunch_dur_str = str(lunch_info["lunch_duration_minutes"]) if lunch_info["lunch_duration_minutes"] is not None else "-"
            lunch_late_minutes = lunch_info["lunch_late_minutes"] if lunch_info["lunch_late_minutes"] is not None else "-"
            lunch_status_str = lunch_info["lunch_status"]

            if row.tap_count and needs_shift_review(row, known_shift):
                first_val = row.first_tap.strftime("%H:%M")
                if row.last_tap != row.first_tap:
                    last_val = row.last_tap.strftime("%H:%M")
                std_expected = 0.0
                note = "Cần xác minh ca làm"
            elif effective_shift.strip().upper() in FULL_DAY_LEAVE_CODES:
                std = 0
                ot = 0
                late = 0
                early = 0
                note = effective_shift.strip().upper()
                if row.tap_count >= 1: first_val = row.first_tap.strftime("%H:%M")
                if row.tap_count >= 2: last_val = row.last_tap.strftime("%H:%M")
                # Phase 15: Get standard hours and leave types for leave days
                win = shift_window
                std_expected = win.get('standard_hours', 8.0)
                workday_base = win.get('workday_base', 8.0)
                hp = win.get('leave_hours_p', 0.0)
                hr = win.get('leave_hours_r', 0.0)
                ho = win.get('leave_hours_o', 0.0)
                ht = win.get('leave_hours_t', 0.0)
                hc = win.get('leave_hours_c', 0.0)
                hk = win.get('leave_hours_k', 0.0)
            elif row.tap_count >= 1:
                first_val = row.first_tap.strftime("%H:%M")
                last_val = row.last_tap.strftime("%H:%M")
                res_work, std, ot, late, early, hp, hr, ho, ht, hc, hk, night_subsidy, std_expected, workday_base = compute_day_stats(
                    row.first_tap,
                    row.last_tap,
                    w_date,
                    department,
                    effective_shift,
                    rules_pool=rules_pool
                )
                # If only 1 tap, OR multiple taps but they are within 5 minutes (duplicate taps)
                if row.tap_count == 1 or (row.last_tap - row.first_tap).total_seconds() < 300:
                    note = determine_missing_tap(row.first_tap, w_date, effective_shift, department, rules_pool)
                    # Single tap: suppress the metric we cannot know
                    if note == "Missing Check-out":
                        early = 0   # don't know when they left
                        last_val = "-"
                    elif note == "Missing Check-in":
                        late = 0    # don't know when they arrived
                        first_val = "-"

                    # If there's leave hours, we might want to suppress the "Missing" note
                    # but we ALWAYS keep the '-' in first_val/last_val as requested.
                    if (hp or hr or ho or ht or hc or hk):
                        note = "" # Leave note will be handled by the shift code or general notes


            if row.tap_count and row.status == SOURCE_LOG_ONLY:
                note = f"Chưa xác minh hồ sơ nhân viên. {note}".strip()

            # ── Classify std/ot by shift_category (NORMAL / HOLIDAY / ROTATION)
            #    and day vs night shift. Logic unchanged — only routing results.
            _cat, _is_night = _get_shift_meta(effective_shift, rules_pool)
            _std_num = std if isinstance(std, (int, float)) else 0.0
            _ot_num  = ot  if isinstance(ot,  (int, float)) else 0.0
            work_normal = work_holiday = work_rotation = 0.0
            ot_normal_day = ot_holiday_day = ot_rotation_day = 0.0
            ot_normal_night = ot_holiday_night = ot_rotation_night = 0.0
            if _cat == "HOLIDAY":
                work_holiday = _std_num
                if _is_night: ot_holiday_night = _ot_num
                else:         ot_holiday_day   = _ot_num
            elif _cat == "ROTATION":
                work_rotation = _std_num
                if _is_night: ot_rotation_night = _ot_num
                else:         ot_rotation_day   = _ot_num
            else:  # NORMAL (default)
                work_normal = _std_num
                if _is_night: ot_normal_night = _ot_num
                else:         ot_normal_day   = _ot_num

            processed_data[emp_id]["days"][w_date] = {
                "first": first_val, "last": last_val,
                "lunch_out_str": lunch_out_str, "lunch_in_str": lunch_in_str,
                "lunch_dur_str": lunch_dur_str, "lunch_status_str": lunch_status_str,
                "lunch_late_minutes": lunch_late_minutes,
                "std": std, "ot": ot, "late": late, "early": early,
                "shift": shift_code_display,
                "shift_code": shift_code_display,
                "note": note,
                "night_subsidy": night_subsidy,
                "std_expected": std_expected,
                "workday_base": workday_base,
                "hp": hp, "hr": hr, "ho": ho, "ht": ht, "hc": hc, "hk": hk,
                # 9 cột phân loại
                "work_normal": work_normal, "work_holiday": work_holiday, "work_rotation": work_rotation,
                "ot_normal_day": ot_normal_day, "ot_holiday_day": ot_holiday_day, "ot_rotation_day": ot_rotation_day,
                "ot_normal_night": ot_normal_night, "ot_holiday_night": ot_holiday_night, "ot_rotation_night": ot_rotation_night,
            }

            if full_emp_id:
                processed_data[emp_id]["full_id"] = full_emp_id

        sorted_emp_ids = sorted(processed_data.keys())

        dates_list = []
        curr = start_date
        while curr <= end_date:
            dates_list.append(curr)
            curr += timedelta(days=1)

        wb = Workbook()
        grid_line = Side(style="thin", color="FFB8C7D8")
        center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        wb.add_named_style(NamedStyle(
            name="Attendance Data", alignment=center,
            border=Border(left=grid_line, right=grid_line, top=grid_line, bottom=grid_line),
        ))
        wb.add_named_style(NamedStyle(
            name="Attendance Header", alignment=center,
            border=Border(
                left=grid_line, right=grid_line, top=grid_line,
                bottom=Side(style="medium", color="FF587493"),
            ),
            font=Font(bold=True, color="FF19334D"),
            fill=PatternFill(fill_type="solid", fgColor="FFE2EDF8"),
        ))
        ws = wb.active
        if ws is None:
            ws = wb.create_sheet()
        ws.title = "Attendance Export"
        # Column 7 renamed to "Chỉ số", and real "Ghi chú" added at the end
        headers = ["Mã máy", "Mã công ty", "Tên nhân viên", "Phòng ban", "Nhóm", "Ngày vào làm", "Chỉ số"]
        for d in dates_list: headers.append(f"{d.day}/{d.month}")
        headers.append("Ghi chú")
        ws.append(headers)

        for cell in ws[1]:
            cell.style = "Attendance Header"

        with export_lock:
            export_status["total"] = len(sorted_emp_ids)
            export_status["current_step"] = "Generating Sheet 1..."

        current_row = 2
        # Keep Sheet 1 indicator labels and values aligned across all view modes.
        all_indicators = _sheet1_indicators(view_mode)

        num_rows = len(all_indicators)

        for idx, emp_id in enumerate(sorted_emp_ids):
            if export_status["cancel_requested"]:
                with export_lock: export_status["is_running"] = False
                return

            if idx % 5 == 0:
                with export_lock:
                    export_status["progress"] = int((idx / len(sorted_emp_ids)) * 50)

            emp_data_info = processed_data[emp_id]
            emp_data = emp_data_info["days"]
            emp_m = emp_meta.get(emp_id)
            emp_name = emp_data_info["name"] or "-"
            emp_dept = emp_data_info["department"] or "-"
            emp_group = emp_m.group_name if emp_m and emp_m.group_name else "-"
            emp_start = emp_m.start_date.strftime("%d/%m/%Y") if emp_m and emp_m.start_date else "-"

            for r_offset in range(num_rows):
                r_idx = current_row + r_offset

                full_id_val = emp_data_info.get("full_id") or "-"
                vals = [emp_id, full_id_val, emp_name, emp_dept, emp_group, emp_start, all_indicators[r_offset]]
                for c_idx, val in enumerate(vals, 1):
                    ws.cell(row=r_idx, column=c_idx, value=val).style = "Attendance Data"

            # Fill in notes in the last column of the first row of each employee block
            notes_str = ""
            for d in dates_list:
                if d in emp_data and emp_data[d].get("note"):
                    if notes_str: notes_str += "; "
                    notes_str += f"{d.day}/{d.month}: {emp_data[d]['note']}"

            notes_col = len(dates_list) + 8
            ws.cell(row=current_row, column=notes_col, value=notes_str or "-").style = "Attendance Data"
            for i in range(1, num_rows):
                ws.cell(row=current_row+i, column=notes_col, value="").style = "Attendance Data"

            for date_idx, d in enumerate(dates_list):
                col = date_idx + 8 # Date columns start after "Chỉ số" (Column 7)
                vals = _sheet1_values(emp_data[d], view_mode) if d in emp_data else ["-"] * num_rows
                for i, value in enumerate(vals):
                    ws.cell(row=current_row+i, column=col, value=value).style = "Attendance Data"
            current_row += num_rows

        with export_lock: export_status["current_step"] = "Generating Sheet 2..."
        ws2 = wb.create_sheet(title="Thông tin chi tiết")
        # Added "Ngày vào làm" & Lunch Monitoring columns to Sheet 2
        ws2.append(_sheet2_headers())

        for cell in ws2[1]:
            cell.style = "Attendance Header"

        ws2_row = 2
        for idx, emp_id in enumerate(sorted_emp_ids):
            if export_status["cancel_requested"]:
                with export_lock: export_status["is_running"] = False
                return

            if idx % 10 == 0:
                with export_lock: export_status["progress"] = 50 + int((idx / len(sorted_emp_ids)) * 50)

            emp_info = processed_data[emp_id]
            emp_m = emp_meta.get(emp_id)
            for d, ds in sorted(emp_info["days"].items()):
                ot = ds["ot"]
                display_ot = ot if (isinstance(ot, (int, float)) and ot > 0) else 0
                shift_code_val = ds.get("shift_code", ds.get("shift", "N"))
                full_id_val = emp_info.get("full_id") or "-"
                hired_date_val = emp_m.start_date.strftime("%d/%m/%Y") if emp_m and emp_m.start_date else "-"
                row_data = [
                    emp_id, full_id_val, emp_info["name"] or "-",
                    emp_info["department"] or "-",
                    emp_m.group_name if emp_m else "-",
                    hired_date_val,
                    d.strftime("%d/%m/%Y"),
                    ds["first"], ds["last"],
                    ds.get("lunch_out_str", "-"), ds.get("lunch_in_str", "-"),
                    ds.get("lunch_dur_str", "-"), ds.get("lunch_status_str", "-"),
                    ds.get("lunch_late_minutes", "-"),
                    ds["std"], display_ot, ds["late"], ds["early"],
                    shift_code_val,
                    ds.get("std_expected", 8.0),
                    ds.get("night_subsidy", 0),
                    # 9 cột phân loại theo shift_category + ca ngày/đêm
                    ds.get("work_normal", 0), ds.get("work_holiday", 0), ds.get("work_rotation", 0),
                    ds.get("ot_normal_day", 0), ds.get("ot_holiday_day", 0), ds.get("ot_rotation_day", 0),
                    ds.get("ot_normal_night", 0), ds.get("ot_holiday_night", 0), ds.get("ot_rotation_night", 0),
                    ds["note"],
                ]


                for c_idx, val in enumerate(row_data, 1):
                    ws2.cell(row=ws2_row, column=c_idx, value=val).style = "Attendance Data"

                ws2_row += 1

        with export_lock: export_status["current_step"] = "Generating Sheet 3 (Summary)..."
        ws3_title = f"Bảng công {start_date.strftime('%d.%m')}-{end_date.strftime('%d.%m')}"
        ws3 = wb.create_sheet(title=ws3_title[:31]) # Excel sheet names are limited to 31 chars

        ws3_headers = [
            "Mã máy", "Mã công ty", "Tên nhân viên", "Phòng ban", "Nhóm", "Ngày vào làm",
            "Tổng Ngày Công",
            "Nghỉ Phép (P)", "Việc Riêng (R)", "Nghỉ Ốm (O)", "Nghỉ Tang (T)", "Nghỉ Cưới (C)", "Không Phép (K)",
            "Tổng số lần đi muộn", "Tổng số lần về sớm",
            "Tổng Giờ Công", "Tổng Tăng Ca", "Tổng Giờ trợ cấp ca đêm",
            "Tổng Giờ ngày thường", "Tổng Giờ ngày nghỉ lễ", "Tổng Giờ ngày nghỉ luân phiên",
            "Tổng TC thường - ca ngày", "Tổng TC lễ - ca ngày", "Tổng TC luân phiên - ca ngày",
            "Tổng TC thường - ca đêm", "Tổng TC lễ - ca đêm", "Tổng TC luân phiên - ca đêm"
        ]
        ws3.append(ws3_headers)
        for cell in ws3[1]:
            cell.style = "Attendance Header"

        for row_idx, emp_id in enumerate(sorted_emp_ids, start=2):
            emp_info = processed_data[emp_id]
            emp_m = emp_meta.get(emp_id)

            late_count = 0
            early_count = 0
            total_workdays = 0.0
            total_hp = total_hr = total_ho = total_ht = total_hc = total_hk = 0.0
            sum_std = sum_ot = sum_ns = 0.0
            sum_wn = sum_wh = sum_wr = 0.0
            sum_otnd = sum_othd = sum_otrd = 0.0
            sum_otnn = sum_othn = sum_otrn = 0.0

            for d in dates_list:
                if d not in emp_info["days"]: continue
                ds = emp_info["days"][d]

                # Calculate daily contributions: Actual Hours / Workday Base
                std_h = float(ds.get("std", 0.0))
                base = float(ds.get("workday_base", 8.0))
                if base > 0:
                    total_workdays += (std_h / base)
                    total_hp += (float(ds.get("hp", 0.0)) / base)
                    total_hr += (float(ds.get("hr", 0.0)) / base)
                    total_ho += (float(ds.get("ho", 0.0)) / base)
                    total_ht += (float(ds.get("ht", 0.0)) / base)
                    total_hc += (float(ds.get("hc", 0.0)) / base)
                    total_hk += (float(ds.get("hk", 0.0)) / base)

                if isinstance(ds.get("late"), (int, float)) and ds["late"] > 0: late_count += 1
                if isinstance(ds.get("early"), (int, float)) and ds["early"] > 0: early_count += 1

                sum_std += float(ds.get("std", 0.0))
                sum_ot  += float(ds.get("ot", 0.0))
                sum_ns  += float(ds.get("night_subsidy", 0.0))
                sum_wn  += float(ds.get("work_normal", 0.0))
                sum_wh  += float(ds.get("work_holiday", 0.0))
                sum_wr  += float(ds.get("work_rotation", 0.0))
                sum_otnd += float(ds.get("ot_normal_day", 0.0))
                sum_othd += float(ds.get("ot_holiday_day", 0.0))
                sum_otrd += float(ds.get("ot_rotation_day", 0.0))
                sum_otnn += float(ds.get("ot_normal_night", 0.0))
                sum_othn += float(ds.get("ot_holiday_night", 0.0))
                sum_otrn += float(ds.get("ot_rotation_night", 0.0))

            full_id_val = emp_info.get("full_id") or "-"
            hired_date_val = emp_m.start_date.strftime("%d/%m/%Y") if emp_m and emp_m.start_date else "-"

            row_data_ws3 = [
                emp_id, full_id_val, emp_info["name"] or "-",
                emp_info["department"] or "-",
                emp_m.group_name if emp_m else "-",
                hired_date_val,
                round(total_workdays, 3),
                round(total_hp, 3), round(total_hr, 3), round(total_ho, 3),
                round(total_ht, 3), round(total_hc, 3), round(total_hk, 3),
                late_count, early_count,
                round(sum_std, 2), round(sum_ot, 2), round(sum_ns, 2),
                round(sum_wn, 2), round(sum_wh, 2), round(sum_wr, 2),
                round(sum_otnd, 2), round(sum_othd, 2), round(sum_otrd, 2),
                round(sum_otnn, 2), round(sum_othn, 2), round(sum_otrn, 2)
            ]
            for col_idx, value in enumerate(row_data_ws3, start=1):
                ws3.cell(row=row_idx, column=col_idx, value=value).style = "Attendance Data"

        for sheet in [ws, ws2, ws3]:
            for col_idx in range(1, sheet.max_column + 1):
                column_letter = get_column_letter(col_idx)
                max_length = 0
                for row_idx in range(1, min(sheet.max_row, 20) + 1):
                    val = sheet.cell(row=row_idx, column=col_idx).value
                    if val:
                        length = max(len(line) for line in str(val).split('\n'))
                        if length > max_length: max_length = length

                adjusted_width = (max_length + 4) * 1.1
                sheet.column_dimensions[column_letter].width = min(adjusted_width, 60)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", prefix="Attendance_Export_Temp_")
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
