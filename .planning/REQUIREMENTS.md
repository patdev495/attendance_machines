# Requirements: Time Attendance Machine — v3.0

> 🌍 **Multi-language Goal**: Đảm bảo 100% giao diện hỗ trợ English (mặc định), Tiếng Việt, và Tiếng Trung. Không còn chuỗi ký tự text cứng (hardcoded) trong code frontend.

## Foundation & Setup

- **I18N-01**: English (en) là ngôn ngữ mặc định và là fallback nếu thiếu bản dịch ở các ngôn ngữ khác.
- **I18N-02**: Hệ thống lưu trữ lựa chọn ngôn ngữ của người dùng qua `localStorage` và tự động áp dụng khi load trang.
- **I18N-03**: Nút chuyển đổi ngôn ngữ (Lựa chọn giữa EN, VI, ZH) được tích hợp vào `AppHeader`.

## Layout & Shared Components

- **I18N-04**: Đa ngôn ngữ cho `AppSidebar` (Nav items: Dashboard, Logs, Summary, Employees, Machines).
- **I18N-05**: Đa ngôn ngữ cho các Shared components:
  - `PaginationBar`: "Showing X-Y of Z", labels.
  - `ToastNotification`: Success/Error/Info types.
  - `ConfirmModal`: "Confirm", "Cancel", generic titles.
  - `AppModal`: Close buttons.

## Feature: Employee Management (Priority)

- **I18N-06**: Chuyển đổi toàn diện `EmployeesView`: Header, Search placeholder, Sync/Bulk Delete buttons.
- **I18N-07**: Chuyển đổi `EmployeesTable`: Table headers, Action tooltips (View, Edit, Delete, Coverage).
- **I18N-08**: Chuyển đổi Source Status badges: "Excel Synced", "Machine Only", "Log Only".
- **I18N-09**: Chuyển đổi các Modals:
  - `EditEmployeeModal`: Field labels (Name), Rename button.
  - `EmployeeDetailsModal`: Toàn bộ các field từ DB (Id, Name, Department, Group, Start Date, Shift, Source Status, Updated At).
  - `BiometricCoverageModal`: Machine list, Status messages ("Template Present", "No Biometrics", etc.).

## Feature: Daily Summary

- **I18N-10**: Chuyển đổi `SummaryView`: Title, Filter group labels.
- **I18N-11**: Chuyển đổi `SummaryFilters`: Placeholders cho Employee ID, Min/Max hours, Checkboxes (Only Missing).
- **I18N-12**: Chuyển đổi `SummaryTable`: Table headers (Date, Employee ID, Name, Dept, Shift, Check In, Check Out, Work Hours, Status, Note).
- **I18N-13**: Chuyển đổi Attendance Status & Notes: "Late", "Early", "Missing", "Day Shift", "Night Shift".

## Feature: Log Management

- **I18N-14**: Chuyển đổi `LogsView`: Page title, Sync button.
- **I18N-15**: Chuyển đổi `LogsFilters`: Date From/To, Machine IP filters.
- **I18N-16**: Chuyển đổi `LogsTable`: Table headers (Employee ID, Time, Machine IP).
- **I18N-17**: Chuyển đổi Sync status banners: "Syncing...", "Sync Complete", process messages.

## Feature: Machine Management

- **I18N-18**: Chuyển đổi `MachineListView`: Card labels (Users, Fingers, Records, Sync Status).
- **I18N-19**: Chuyển đổi `MachineDetailView`: Header labels, Detailed capacity counts.
- **I18N-20**: Chuyển đổi Control buttons: "Sync Fingerprint", "Rename", "Bulk Delete", "Capacity Info".

## Traceability

| REQ-ID | Phase |
|--------|-------|
| I18N-01 to I18N-05 | Phase 1: Foundation & Layout |
| I18N-06 to I18N-09 | Phase 2: Employee Management i18n |
| I18N-10 to I18N-13 | Phase 3: Daily Summary i18n |
| I18N-14 to I18N-17 | Phase 4: Log Management i18n |
| I18N-18 to I18N-20 | Phase 5: Machine Management i18n |

## Out of Scope (v3.0)

- Backend error message translation (FastAPI responses remain English/Technical).
- Translation of database data (Employee names, Departments - những dữ liệu từ input của người dùng).
- Support for additional languages beyond EN, VI, ZH.
