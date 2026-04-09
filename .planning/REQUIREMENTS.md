# Requirements: Time Attendance Machine — v2.0

## Architecture

- **ARCH-01**: Backend organized as feature modules under `backend/src/features/{logs,daily_summary,employees,machines}/` — each with `router.py`, `service.py`, `schema.py`
- **ARCH-02**: Frontend organized as feature modules under `frontend/src/features/{logs,daily_summary,employees,machines}/` — each with its View + components + api module
- **ARCH-03**: `EmployeeLocalRegistry` DB table tracks all known employees with `source_status` enum: `excel_synced`, `machine_only`, `log_only`
- **ARCH-04**: Old `routers/` and `sync_service.py` removed after migration. `services/export_service.py` preserved under `features/daily_summary/`

---

## Feature 1: Log Management

> Cào log từ tất cả máy chấm công về DB, hiển thị và filter như tab Raw Log hiện tại.

- **LOG-01**: User can trigger a full sync from all configured machines; system pulls new attendance records into `AttendanceLogs` table with deduplication
- **LOG-02**: User can view paginated raw attendance logs with filters: employee_id, machine_ip, date range (start/end)
- **LOG-03**: User can see live sync progress (is_running, current machine, total machines, processed count, last sync time)
- **LOG-04**: System deduplicates by (employee_id, attendance_time, machine_ip) — no duplicate entries on re-sync

---

## Feature 2: Daily Summary

> Tổng hợp báo cáo ngày từ logs. Filter đầy đủ. Export Excel + Sync Excel nâng cấp.

- **SUM-01**: User can view daily attendance summary grouped by employee/day with shift-aware work-hours calculation (existing `compute_day_stats` logic preserved)
- **SUM-02**: User can filter summary by: date range, employee_id, machine_ip, shift (D/N), department, employee status, work hours (min/max), only_missing flag
- **SUM-03**: User can click a row to see attendance detail (individual taps for that employee/day)
- **SUM-04**: User can export summary to Excel for a date range — preserving all existing export logic (two-sheet format, styling, etc.)
- **SUM-05**: User can sync employee metadata from an uploaded Excel file (existing column mapping: EMP_ID, SHIFT, EMP_NAME, DEPARTMENT, GROUP, START_DATE)
- **SUM-06**: Excel sync also fetches all employees from all machines and upserts them into `EmployeeLocalRegistry` — employees present in machine but not in Excel get `source_status = machine_only`
- **SUM-07**: Sync Excel UI shows a results summary distinguishing: Excel-synced count vs Machine-only (ghost) count
- **SUM-08**: Feature does NOT include biometric coverage view or "Delete user from machine" operations (those are in Employee Management)

---

## Feature 3: Employee Management

> Registry thống nhất gồm: nhân viên từ Excel, từ máy chấm công, từ log cũ. Status phân biệt. CRUD cơ bản.

- **EMP-01**: `EmployeeLocalRegistry` table stores all known employees with fields: `employee_id`, `emp_name`, `department`, `group`, `start_date`, `shift`, `source_status` (`excel_synced` | `machine_only` | `log_only`), `updated_at`
- **EMP-02**: Employee list is populated from 3 sources:
  - Excel sync → `excel_synced`
  - Machine users not in Excel → `machine_only`
  - Employees found only in `AttendanceLogs` (not in Excel or any machine) → `log_only`
- **EMP-03**: Employee list UI shows all employees with a visible `source_status` badge/column for differentiation
- **EMP-04**: Missing employee info fields (name, dept, shift) for `machine_only` / `log_only` are displayed as `—` or blank
- **EMP-05**: User can delete an employee from all machines (background task, shows progress status)
- **EMP-06**: User can rename an employee (updates all machines + DB)
- **EMP-07**: User can view biometric coverage for any employee (same modal as current system — checks each machine for user + fingerprint presence)
- **EMP-08**: Employee list supports filtering by `source_status` and basic search by name/ID

---

## Feature 4: Machine Management

> Quản lý máy chấm công — giữ nguyên toàn bộ chức năng hiện tại, chỉ refactor vào feature slice.

- **MCH-01**: User can view list of configured machines with online/offline status
- **MCH-02**: User can view all employees registered on a specific machine, enriched with DB metadata (name, dept, shift, status)
- **MCH-03**: User can delete a single employee from a specific machine
- **MCH-04**: User can bulk-delete multiple employees from a specific machine
- **MCH-05**: User can view machine capacity (users/cap, fingerprints/cap, records/cap)
- **MCH-06**: User can sync fingerprints for a single employee from a specific machine
- **MCH-07**: User can bulk-sync all fingerprints from a specific machine to DB
- **MCH-08**: User can export fingerprint data to Excel (from DB)

---

## Traceability

| REQ-ID | Phase |
|--------|-------|
| ARCH-01 to ARCH-04 | Phase 1 |
| LOG-01 to LOG-04 | Phase 2 |
| SUM-01 to SUM-08 | Phase 3 |
| EMP-01 to EMP-08 | Phase 4 |
| MCH-01 to MCH-08 | Phase 5 |

---

## Out of Scope (v2.0)

- Automated unit/integration tests — future milestone
- Multi-language (i18n) — future milestone
- Configurable shift rules UI — future milestone
- Mobile app — not planned
- Cloud hosting — on-premise only
