# Phase 1: Backend Modularization - Context

**Gathered:** 2026-04-07
**Status:** Planning

## Phase Boundary
Decompose the monolithic `backend/src/main.py` into a modular, service-oriented structure. The API endpoints will be separated from business logic and utility functions.

### Deliverables
- New directories: `routers/`, `services/`, `utils/` within `backend/src/`.
- Modularized routers for Devices, Employees, Attendance, and Sync.
- Extracted services for Attendance reporting and Excel export.
- Shared utility functions for shift calculations.
- Refactored `main.py` acting strictly as an entry point.

---

## Technical Decisions

### 1. Directory Structure
We will adopt the standard FastAPI modular application structure:
- `backend/src/routers/`: API endpoints using `APIRouter`.
- `backend/src/services/`: Core logic processing (independent of API/HTTP).
- `backend/src/utils/`: Shared help functions/stateless logic.

### 2. Router Separation
- `attendance.py`: All `/api/attendance/*` and `/api/export-attendance/*` endpoints.
- `employees.py`: All `/api/employees/*` endpoints.
- `devices.py`: All `/api/devices/*` endpoints and capacity checks.
- `sync.py`: Trigger endpoints for machine and employee sync.

### 3. Service Extraction
- `AttendanceService`: Handle database aggregations and work date calculations.
- `ExportService`: Handle background Excel generation, progress tracking, and lock management.
- `EmployeeService`: Handle business rules for employee data merging.

### 4. Shared Utilities
- `shift_utils.py`: `get_shift_rules` and `compute_day_stats`.
- `stats_utils.py`: Any additional data processing helpers.

---

## Canonical References
- [main.py](file:///d:/Workspace/Time_Attendance_Machine/backend/src/main.py) — Source monolith.
- [sync_service.py](file:///d:/Workspace/Time_Attendance_Machine/backend/src/sync_service.py) — External service interface (remains as is for now, or integrates with new services).
- [CONCERNS.md](file:///d:/Workspace/Time_Attendance_Machine/.planning/codebase/CONCERNS.md) — Motivation for refactoring.

---
*Phase: 01-backend-modularization*
