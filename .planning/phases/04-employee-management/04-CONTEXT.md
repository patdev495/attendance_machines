# Phase 4: Employee Management - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning (Revised)

<domain>
## Phase Boundary
This phase delivers a unified employee registry that consolidates data from Excel, Machines, and Attendance Logs. 
Key updates include dual-name tracking (DB vs Hardware), robust machine connectivity handling, and dedicated editing capabilities.

</domain>

<decisions>
## Implementation Decisions

### 1. Unified Employee Registry (EmployeeLocalRegistry)
- [Locked] Populate from Excel Sync (source_status = `excel_synced`).
- [Locked] Merge machine users not in Excel (source_status = `machine_only`).
- [Locked] Identify employees found only in historical AttendanceLogs (source_status = `log_only`).
- [Decision] Rename the master button to **"Update"**.
- [Decision] The "Update" process MUST persist all discovered employees into the `EmployeeLocalRegistry` table.
- [Decision] Track a single name field:
    - `emp_name`: Name from DB/Excel (Source of Truth). 
    - Names from biometric machines are IGNORED and not stored in the database.

### 2. Machine Operations & Robustness
- [Decision] **Delete from machines only**: The "Delete" button removes the user from hardware BUT preserves the record in the local DB.
- [Decision] **Offline Handling**: If a machine is unreachable during a delete/rename, the process continues on reachable machines and reports the failed IPs to the user.
- [Decision] **Renaming**: Updating the name triggers a sync of `emp_name` to all reachable machines.

### 3. UI/UX
- [Locked] Source status badges: Excel (Green), Machine (Orange), Log-only (Gray).
- [Decision] Single name column in the main table.
- [Decision] Add an **"Edit"** button that opens a form to modify the name and other metadata.
- [Decision] Add a **"View Info"** button for each employee to display all stored database information (use "-" for missing values).
- [Locked] Reuse `BiometricCoverageModal.vue`.

</decisions>

<canonical_refs>
## Canonical References
- `backend/src/database.py` — Schema for `EmployeeLocalRegistry`
- `backend/src/sync_service.py` — Original logic for machine operations
- `backend/src/features/daily_summary/service.py` — Current Excel sync logic

</canonical_refs>

<specifics>
## Specific Ideas
- Capture error messages per IP in all background machine tasks.
- Use a modal form for the "Edit" action.

</specifics>

<deferred>
## Deferred Ideas
- Automatic "Retry" for offline machines once they come back online.
- Bulk editing of departments/groups.

</deferred>
