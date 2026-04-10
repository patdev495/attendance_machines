# Project State: Time Attendance Machine

## Current Milestone
- **Name**: v2.0 — Feature-Based Architecture Refactor
- **Status**: Active
- **Progress**: 50% (3/6 phases complete)

## Active Phase
- **Phase**: Phase 4: Employee Management Feature
- **Goal**: Registry nhân viên thống nhất — Excel + Machine + Log-only. Status badge. Xóa/đổi tên/biometric.

## Accumulated Context

### Project Vision
Refactor backend and frontend into vertical feature slices (logs, daily_summary, employees, machines). Add EmployeeLocalRegistry to unify all employee sources. Preserve all existing business logic.

### Architecture Target
```
backend/src/
  features/
    logs/          ← sync_service (log pulling) + raw log endpoints
    daily_summary/ ← attendance summary + export
    employees/     ← unified employee registry (EmployeeLocalRegistry)
    machines/      ← machine management + fingerprints
  shared/          ← database.py, config.py, utils/
  main.py          ← thin orchestrator

frontend/src/
  features/
    logs/          ← LogsView + components
    daily_summary/ ← DailySummaryView + components
    employees/     ← EmployeesView + components
    machines/      ← DeviceListView + DeviceDetailView
  shared/          ← layout, i18n, stores, router
```

### Key Constraints
- Windows OS deployment.
- MSSQL 2008 compatibility (no modern SQL features).
- Hardware dependency on ZKTeco (PyZK protocol).
- `uv pip` for all Python package installs.

### Roadmap Evolution
- v1.x: Routers/services split completed.
- v2.0 started 2026-04-09: Full feature-based refactor.

---
*Last updated: 2026-04-09*
