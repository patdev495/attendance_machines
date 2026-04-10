# Roadmap: Time Attendance Machine — v2.0

## Milestone v2.0: Feature-Based Architecture Refactor
Goal: Refactor toàn bộ backend và frontend thành vertical feature slices, nâng cấp employee registry, giữ nguyên toàn bộ business logic.

**Numbering:** Phases 1–6 (fresh start for v2.0)
**Strategy:** Mỗi phase = 1 feature hoàn chỉnh (backend + frontend). User test sau mỗi phase.

> ⚠️ **DB Hard Constraint**: Chỉ được THÊM bảng mới. Không được ALTER/DROP bất kỳ bảng hiện có nào (`ShiftRules`, `AttendanceLogs`, `EmployeeMetadata`, `EmployeeFingerprints`).

---

### Phase 1: Foundation & DB Schema
- **Goal**: Dọn sạch cấu trúc cũ, tạo khung feature-based và thêm `EmployeeLocalRegistry` vào DB.
- **Requirements**: ARCH-01, ARCH-02, ARCH-03, ARCH-04
- **Depends on**: None
- **UI hint**: no

**Plans:**
- [x] **1-01** — Create backend feature scaffold: `features/{logs,daily_summary,employees,machines}/` với `__init__.py`, `router.py`, `service.py`, `schema.py` placeholder. Khởi tạo `shared/` (move database.py, config.py, utils/). Cập nhật import paths.
- [x] **1-02** — Add `EmployeeLocalRegistry` model vào database.py: fields `employee_id`, `emp_name`, `department`, `group`, `start_date`, `shift`, `source_status` (enum: excel_synced/machine_only/log_only), `updated_at`. Run `init_db()` để tạo table. **KHÔNG sửa bất kỳ model hiện có nào.** Chỉ dùng `Base.metadata.create_all()` — SQLAlchemy sẽ chỉ tạo bảng nếu chưa tồn tại.
- [x] **1-03** — Create frontend feature scaffold: `src/features/{logs,daily_summary,employees,machines}/` với `index.vue`, `api.js`, `components/` placeholder. Move shared code vào `src/shared/`.
- [x] **1-04** — Update `main.py` để đăng ký feature routers. Update Vue `router/index.js` để point tới feature views. Verify app khởi động không lỗi.

**Success criteria:**
1. `python main.py` chạy không có import errors
2. DB có table `EmployeeLocalRegistry` sau `init_db()`
3. Frontend build thành công, routes load đúng
4. Old `routers/` vẫn còn (chưa xóa), app vẫn hoạt động bình thường

---

### Phase 2: Log Management Feature
- **Goal**: Hoàn thiện tính năng quản lý log (sync + hiển thị) dưới dạng feature slice.
- **Requirements**: LOG-01, LOG-02, LOG-03, LOG-04
- **Depends on**: Phase 1
- **UI hint**: yes

**Plans:**
4/4 plans complete
- [ ] **2-02** — Backend `features/logs/router.py`: Endpoints `POST /api/logs/sync`, `GET /api/logs/sync/status`, `GET /api/logs` (paginated + filtered: employee_id, machine_ip, start_date, end_date), `GET /api/logs/date-range`. Schema Pydantic cho response.
- [ ] **2-03** — Frontend `features/logs/api.js`: Functions `startSync()`, `getSyncStatus()`, `getLogs(filters)`, `getDateRange()`. Migrate từ `api/attendance.js` (phần raw log).
- [ ] **2-04** — Frontend `features/logs/LogsView.vue` + components `LogsFilters.vue`, `LogsTable.vue`, `SyncStatusBar.vue`: Giống Raw Log tab hiện tại — filter panel, paginated table, sync button với progress. Register route `/logs`.

**Success criteria:**
1. User bấm Sync → progress bar hiện → logs được pull về DB
2. Raw log table hiển thị dữ liệu đúng với pagination
3. Filter theo employee_id, machine_ip, date range hoạt động
4. Re-sync không tạo duplicate records

---

### Phase 3: Daily Summary Feature
- **Goal**: Tổng hợp báo cáo ngày với filter đầy đủ, Export Excel giữ nguyên logic, Sync Excel nâng cấp (merge machine users).
- **Requirements**: SUM-01, SUM-02, SUM-03, SUM-04, SUM-05, SUM-06, SUM-07, SUM-08
- **Depends on**: Phase 1, Phase 2
- **UI hint**: yes

**Plans:**
- [x] **3-01** — Backend `features/daily_summary/service.py`: Extract `AttendanceService.process_summary_rows`, shift calculation logic. Upgrade `sync_employees_from_excel` to upsert into `EmployeeLocalRegistry` and merge machine users.
- [x] **3-02** — Backend `features/daily_summary/router.py`: Endpoints `GET /api/summary`, `GET /api/summary/detail`, `POST /api/summary/export`, `GET /api/summary/export/status`, `POST /api/summary/sync-excel`.
- [x] **3-03** — Frontend `features/daily_summary/api.js`: Functions for fetching summary, detail, triggering export and sync.
- [x] **3-04** — Frontend `features/daily_summary/DailySummaryView.vue` + `SummaryTable.vue`, `SummaryFilters.vue`.
- [x] **3-05** — Frontend `features/daily_summary/components/ExcelSyncModal.vue`: Upload dialog + progress bar with detailed results.

**Success criteria:**
1. Daily summary table load đúng dữ liệu với shift-aware work hours
2. Tất cả filters hoạt động (date, employee, machine, shift, dept, status, hours, only_missing)
3. Export Excel tạo file đúng format 2-sheet như cũ
4. Sync Excel upload file → update EmployeeMetadata + upsert machine users vào EmployeeLocalRegistry
5. Sync result modal phân biệt Excel-synced vs Machine-only count

---

### Phase 4: Employee Management Feature
- **Goal**: Registry nhân viên thống nhất — Excel + Machine + Log-only. Status badge. Xóa/đổi tên/biometric.
- **Requirements**: EMP-01, EMP-02, EMP-03, EMP-04, EMP-05, EMP-06, EMP-07, EMP-08
- **Depends on**: Phase 1, Phase 3
- **UI hint**: yes

**Plans:**
- [x] **4-01** — Backend `features/employees/service.py`: Logic build `EmployeeLocalRegistry` từ 3 nguồn: (1) đọc `EmployeeMetadata` & upsert với `excel_synced`, (2) query machine users & upsert với `machine_only` nếu không có trong Excel, (3) query `AttendanceLogs` distinct employee_id & upsert với `log_only` nếu không có trong 2 nguồn trên. Extract `delete_user_from_all_machines()`, `update_user_name_all_machines()`, `get_biometric_coverage()` từ `sync_service.py`.
- [x] **4-02** — Backend `features/employees/router.py`: `GET /api/employees` (paginated, filter by source_status + search), `POST /api/employees/rebuild-registry` (rebuild EmployeeLocalRegistry từ 3 nguồn), `DELETE /api/employees/{id}` (xóa khỏi tất cả máy, background task), `GET /api/employees/{id}/delete-status`, `PUT /api/employees/{id}/name` (đổi tên), `GET /api/employees/{id}/biometric-coverage`. Schema Pydantic cho EmployeeLocalRegistry.
- [x] **4-03** — Frontend `features/employees/api.js`: `getEmployees(filters)`, `rebuildRegistry()`, `deleteEmployee(id)`, `getDeleteStatus(id)`, `updateName(id, name)`, `getBiometricCoverage(id)`.
- [x] **4-04** — Frontend `features/employees/EmployeesView.vue` + `EmployeesTable.vue`: Danh sách nhân viên có cột `source_status` badge (màu khác nhau: Excel=xanh, Machine=cam, Log-only=xám). Filter bar: search by ID/name, filter by source_status. Actions: Rename, Delete (với confirm modal), Biometric Coverage.
- [x] **4-05** — Frontend: Reuse `BiometricCoverageModal.vue` từ `components/employees/` & move vào `features/employees/components/`. Wiring vào EmployeesTable action.

**Success criteria:**
1. Employee list hiển thị đủ 3 loại nhân viên với status badge phân biệt
2. Nhân viên machine-only/log-only có fields rỗng/`—` cho name, dept, shift
3. Delete employee → background task → user có thể poll status
4. Rename → cập nhật trên tất cả máy + trong DB
5. Biometric coverage modal load đúng per-machine status

---

### Phase 5: Machine Management Feature
- **Goal**: Refactor toàn bộ machine management vào feature slice — giữ nguyên 100% behavior hiện tại.
- **Requirements**: MCH-01, MCH-02, MCH-03, MCH-04, MCH-05, MCH-06, MCH-07, MCH-08
- **Depends on**: Phase 1
- **UI hint**: yes

**Plans:**
- [ ] **5-01** — Backend `features/machines/service.py`: Extract từ `sync_service.py`: `get_machine_list()`, `get_users_from_machine()`, `delete_user_from_machine()`, `bulk_delete_users_from_machine()`, `get_devices_capacity_info()`, `download_fingerprints_from_machine()`, `bulk_download_fingerprints_from_machine()`, `check_user_biometric_on_machine()`. Mỗi hàm giữ nguyên hoàn toàn.
- [ ] **5-02** — Backend `features/machines/router.py`: Toàn bộ endpoints từ `routers/machines.py` → prefix `/api/machines`. `GET /api/machines`, `GET /api/machines/{ip}/employees`, `DELETE /api/machines/{ip}/employees/{id}`, `POST /api/machines/{ip}/employees/bulk-delete`, `GET /api/machines/capacity`, `POST /api/machines/{ip}/sync-fingerprints`, `POST /api/machines/{ip}/sync-all-fingerprints`, `GET /api/machines/export-fingerprints`. Kèm biometric export service.
- [ ] **5-03** — Frontend `features/machines/api.js`: Migrate toàn bộ `api/devices.js` + fingerprint endpoints sang feature api module.
- [ ] **5-04** — Frontend `features/machines/` views + components: Move `DeviceListView.vue`, `DeviceDetailView.vue` (với toàn bộ sub-components) vào feature folder. Update imports. Register routes `/machines`, `/machines/:ip`.

**Success criteria:**
1. Device list hiển thị online/offline status đúng
2. Device detail page load employees, capacity đúng
3. Single + bulk delete employee từ machine hoạt động
4. Fingerprint sync (individual + bulk) hoạt động
5. Export fingerprints tạo file Excel đúng

---

### Phase 6: Cleanup & Final Wiring
- **Goal**: Xóa code cũ, cập nhật tất cả imports, verify toàn bộ app hoạt động end-to-end.
- **Requirements**: ARCH-04 (removal of old files)
- **Depends on**: Phase 2, Phase 3, Phase 4, Phase 5
- **UI hint**: no

**Plans:**
- [ ] **6-01** — Backend cleanup: Xóa `routers/attendance.py`, `routers/export.py`, `routers/machines.py`, `routers/__init__.py`. Xóa `services/attendance_service.py`, `services/biometric_export.py`. Xóa `sync_service.py`. Update `main.py` imports chỉ dùng feature routers. Verify không còn import lỗi.
- [ ] **6-02** — Frontend cleanup: Xóa `api/attendance.js`, `api/devices.js`, `api/employees.js`, `api/export.js` (nếu đã migrate hết). Verify tất cả components import từ feature module. Remove unused views cũ.
- [ ] **6-03** — Integration verification: Chạy toàn bộ app, verify tất cả routes hoạt động. Kiểm tra navigation, API calls không bị lỗi 404/500. Update `GEMINI.md` với architecture mới.

**Success criteria:**
1. Không còn file nào trong `routers/`, `sync_service.py` bị import
2. `uv pip install` và `python main.py` chạy OK
3. Frontend build `npm run build` không lỗi
4. Tất cả 4 features accessible từ navigation
5. Sync log, export Excel, sync Excel, employee operations đều hoạt động

---

## Phase Summary

| # | Phase | Goal | Requirements | Effort |
|---|-------|------|--------------|--------|
| 1 | Foundation & DB Schema | Scaffold structure + EmployeeLocalRegistry | ARCH-01–04 | Medium |
| 2 | Log Management | 4/4 | Complete   | 2026-04-09 |
| 3 | Daily Summary | 5/5 | Complete   | 2026-04-09 |
| 4 | Employee Management | 5/5 | Complete   | 2026-04-10 |
| 5 | Machine Management | Feature-slice machine ops | MCH-01–08 | Medium |
| 6 | Cleanup & Wiring | Remove old code, final integration | ARCH-04 | Low |

**Total**: 24 plans across 6 phases
