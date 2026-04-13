# Plan: Phase 13 — Dynamic Daily Shifts & Complex Logic

Support calendar-based shift assignments from Excel, enabling flexible work/leave combinations and specific reporting requirements for all departments (including 12h Workshop 1).

## 1. Database & Persistence
- **File**: `backend/src/database.py`
- **Change**: Add `EmployeeDailyShifts` model.
  ```python
  class EmployeeDailyShifts(Base):
      __tablename__ = "EmployeeDailyShifts"
      employee_id = Column(String(50), primary_key=True)
      work_date = Column(Date, primary_key=True)
      shift_code = Column(String(10), nullable=False)
  ```
- **Task**: Run `init_db()` to create the table in MSSQL.

## 2. Shift Window & Logic Engine
- **File**: `backend/src/utils/stats_utils.py`
- **Task 2.1**: Implement `parse_shift_window(code, dept)`.
    - Detect Workshop 1 via `dept`. Base = 12h. Others = 8h (9h span).
    - Map `N` -> (08:00, 17:00), `D` -> (20:00, 05:00+1).
    - For split codes (e.g., `2R6N`, `4D4P`):
        - Regex match `(\d+)([A-Z]+)(\d+)?([A-Z]+)?`.
        - If starts with leave (`R`, `P`): `official_start += X hours`.
        - If ends with leave (`R`, `P`): `official_end -= Y hours`.
- **Task 2.2**: Update `compute_day_stats`.
    - If `code` in [`P`, `O`, `T`, `C`, `R`]: set `work_hours = code`, `ot = 0`.
    - Calculate `minutes_late` and `minutes_early` using the *adjusted* window.

## 3. Excel Sync Refactor
- **File**: `backend/src/features/daily_summary/service.py`
- **Task**: Update `sync_employees_full`.
    - Filter columns that match `\d+/\d+` or single digits `\d+`.
    - For each row, loop through detected date columns.
    - Upsert `EmployeeDailyShifts` records for the month.

## 4. Summary API (JOIN Logic)
- **File**: `backend/src/features/daily_summary/router.py`
- **Task**: Update the main summary query.
    - Implement the **09:00 AM Anchor**:
      ```sql
      work_date = case(
          (func.cast(AttendanceLog.attendance_time, Time) < time(9,0), func.cast(func.dateadd(text("day"), text("-1"), AttendanceLog.attendance_time), Date)),
          else_=func.cast(AttendanceLog.attendance_time, Date)
      )
      ```
    - JOIN `AttendanceLogs` with `EmployeeDailyShifts` on `employee_id` and the calculated `work_date`.
    - Pass the per-day `shift_code` to the processing function.

## 5. Export Logic Consistency
- **File**: `backend/src/features/daily_summary/export_service.py`
- **Task**: Synchronize logic with `router.py` to ensure Excel exports match the UI's dynamic shifts and character-based hours (P, T, O...).

## 6. Frontend UI Safety
- **File**: `frontend/src/features/daily_summary/components/SummaryTable.vue`
- **Task**: Update template to handle `item.work_hours` when it is a string (e.g., "P") instead of a float.

## Verification Checklist
- [ ] DB Table `EmployeeDailyShifts` exists.
- [ ] Excel sync correctly parses `2R6N` and `6P6N`.
- [ ] Night Shift (20:00-05:00) is assigned to the START date.
- [ ] Workshop 1 Night Shift (ending 08:00) is assigned to the START date.
- [ ] Days marked `P` show "P" in the Giờ công column.
- [ ] Split shifts (4N4P) calculate "Early Leave" based on a 12:00 end time.
