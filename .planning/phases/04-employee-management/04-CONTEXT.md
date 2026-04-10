# Phase 4: Employee Management - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary
This phase delivers a unified employee registry that consolidates data from three sources (Excel, Machines, and Attendance Logs). It also migration machine-specific operations (rename, delete, biometric coverage) into the new feature-based architecture.

</domain>

<decisions>
## Implementation Decisions

### 1. Unified Employee Registry (EmployeeLocalRegistry)
- [Locked] Populate from Excel Sync (source_status = `excel_synced`).
- [Locked] Merge machine users not in Excel (source_status = `machine_only`).
- [Locked] Identify employees found only in historical AttendanceLogs (source_status = `log_only`).
- [Decision] A `rebuild_registry` service function will run these three steps in sequence to ensure `EmployeeLocalRegistry` is up-to-date.

### 2. Machine Operations
- [Locked] Delete employee from all machines (Background task with status polling).
- [Locked] Rename employee (Sync across all machines + update DB).
- [Locked] Biometric coverage check (Check each machine in parallel).

### 3. UI/UX
- [Locked] Source status badges: Excel (Green), Machine (Orange), Log-only (Gray).
- [Locked] Handle missing data (name/dept/shift) with `—` for non-excel users.
- [Locked] Reuse `BiometricCoverageModal.vue`.

</decisions>

<canonical_refs>
## Canonical References
- `backend/src/database.py` — Schema for `EmployeeLocalRegistry`
- `backend/src/sync_service.py` — Original logic for machine operations
- `backend/src/features/daily_summary/service.py` — Current Excel sync logic to be migrated/shared

</canonical_refs>

<specifics>
## Specific Ideas
- Use `ThreadPoolExecutor` for parallel machine connectivity (already used in `sync_service.py`).
- Implement `delete_status` tracking in `features/employees/service.py` similar to `sync_status` in Phase 2.

</specifics>

<deferred>
## Deferred Ideas
- Automated cleanup of "log_only" users that are older than X months.
- Advanced biometric management (bulk sync from DB to machine).

</deferred>
