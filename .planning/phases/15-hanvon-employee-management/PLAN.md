---
id: 15
wave: 15
depends_on: ["04-04"]
autonomous: true
objective: Convert Employee Management to Hanvon-only device operations and remove ZKTeco runtime/UI assumptions.
files_modified:
  - CONTEXT.md
  - research_hanvon_sdk/HANVON_PROTOCOL.md
  - backend/src/features/hanvon/client.py
  - backend/src/features/employees/router.py
  - backend/src/features/employees/schema.py
  - backend/src/features/employees/service.py
  - backend/src/features/machines/service.py
  - backend/src/features/logs/service.py
  - frontend/src/features/employees/index.vue
  - frontend/src/features/employees/api.js
  - frontend/src/features/employees/components/EmployeesTable.vue
  - frontend/src/features/employees/components/BiometricCoverageModal.vue
  - frontend/src/i18n/locales/vi.json
  - frontend/src/i18n/locales/en.json
  - frontend/src/i18n/locales/zh.json
---

# Plan 15 - Hanvon Employee Management

Goal: Employee Management must treat Hanvon as the only supported Attendance Machine protocol. The Employee tab remains a paginated Employee Local Registry view, while per-machine role and face coverage live in Biometric Coverage.

## Decisions

- ZKTeco is removed from runtime and UI in this phase.
- Legacy DB columns/tables such as `privilege` and `EmployeeFingerprints` are not dropped in this phase.
- The Employee list does not have a global privilege filter because Hanvon roles are per machine.
- Deleting an Employee from the Employee tab deletes that ID from all Hanvon Attendance Machines, including Machine Manager accounts.
- If the Employee still exists in Excel or Raw Logs, the registry row remains visible after hardware deletion.
- Biometric Coverage labels are: Not registered, Employee, Admin, Super Admin, Offline/Error.
- Face capability is displayed separately from role as Has face / No face.

<tasks>
<task id="15.1">
<title>Remove ZKTeco selection from log sync runtime</title>
<read_first>
- `backend/src/features/logs/service.py`
- `backend/src/shared/hardware.py`
- `backend/src/config.py`
</read_first>
<action>
Update log synchronization so every configured Attendance Machine is handled through Hanvon client logic. Remove protocol branching that falls back to ZKTeco and stop importing `zk` in this flow.
</action>
<acceptance_criteria>
- `sync_all_machines()` calls only Hanvon sync code.
- Machine configs without an explicit protocol default to Hanvon.
- No runtime dependency on `zk` remains in log sync.
- Existing Hanvon deduplication by `(employee_id, attendance_time, machine_ip)` is preserved.
</acceptance_criteria>
</task>

<task id="15.2">
<title>Clean Employee list API filters</title>
<read_first>
- `backend/src/features/employees/router.py`
- `backend/src/features/employees/schema.py`
- `backend/src/features/employees/service.py`
</read_first>
<action>
Remove the `privilege` query parameter from Employee list and export endpoints. Keep pagination, search, source status, and ID sort. Keep legacy `privilege` field out of Employee list response unless another existing caller requires it.
</action>
<acceptance_criteria>
- `GET /api/employees` supports `page`, `page_size`, `search`, `source_status`, and `order`.
- `GET /api/employees/export` no longer accepts or applies `privilege`.
- Employee list behavior is unchanged for pagination/search/source status.
- Tests cover that privilege is not used as a list filter.
</acceptance_criteria>
</task>

<task id="15.3">
<title>Implement Hanvon Biometric Coverage</title>
<read_first>
- `research_hanvon_sdk/HANVON_PROTOCOL.md`
- `backend/src/features/hanvon/client.py`
- `backend/src/features/machines/service.py`
- `backend/src/features/employees/schema.py`
</read_first>
<action>
Replace fingerprint/ZKTeco coverage with Hanvon coverage. For each Attendance Machine, query employee IDs, face IDs, manager IDs, and manager details. Return per-machine role and face capability.
</action>
<acceptance_criteria>
- Coverage response includes `ip`, `status`, `registered`, `role`, `has_face`, and optional `error`.
- Role values are `not_registered`, `employee`, `admin`, `super_admin`.
- `employee` role comes from `GetEmployeeID`.
- `admin` and `super_admin` roles come from `GetManagerID` and `GetManager.authority`.
- Offline machines return `status=Offline` with error text.
- No ZKTeco fingerprint/template calls are used.
</acceptance_criteria>
</task>

<task id="15.4">
<title>Delete Employee and Machine Manager from all Hanvon machines</title>
<read_first>
- `research_hanvon_sdk/HANVON_PROTOCOL.md`
- `backend/src/features/hanvon/client.py`
- `backend/src/features/employees/service.py`
- `backend/src/features/machines/service.py`
</read_first>
<action>
Add `delete_manager` support to `HanvonClient` if missing. Update delete-all hardware flow to delete both Employee and Machine Manager identities for the same ID on every Attendance Machine.
</action>
<acceptance_criteria>
- If ID is in Employee IDs, call `DeleteEmployee`.
- If ID is in Manager IDs, call `DeleteManager`.
- If both exist on the same machine, attempt both and report both results.
- If Hanvon refuses to delete the last manager, return a per-machine failure instead of hiding it.
- The local registry row is not deleted by this operation.
- UI refresh shows the Employee no longer registered in Biometric Coverage on successful machines.
</acceptance_criteria>
</task>

<task id="15.5">
<title>Remove Employee UI privilege controls</title>
<read_first>
- `frontend/src/features/employees/index.vue`
- `frontend/src/features/employees/api.js`
- `frontend/src/features/employees/components/EmployeesTable.vue`
- `frontend/src/i18n/locales/vi.json`
- `frontend/src/i18n/locales/en.json`
- `frontend/src/i18n/locales/zh.json`
</read_first>
<action>
Remove the privilege filter, privilege export param, and privilege column from the Employee tab. Keep per-row actions: View Info, Biometric Coverage, Delete.
</action>
<acceptance_criteria>
- Employee tab shows a paginated table.
- Filters are search and source status only.
- Table actions include View Info, Biometric Coverage, and Delete.
- No global Admin/User/Special privilege labels are displayed in the Employee list.
- Bulk operations that are ZKTeco fingerprint-specific are removed or hidden from this tab.
</acceptance_criteria>
</task>

<task id="15.6">
<title>Update Biometric Coverage UI labels</title>
<read_first>
- `frontend/src/features/employees/components/BiometricCoverageModal.vue`
- `frontend/src/features/employees/api.js`
- `frontend/src/i18n/locales/vi.json`
- `frontend/src/i18n/locales/en.json`
- `frontend/src/i18n/locales/zh.json`
</read_first>
<action>
Render Hanvon role and face capability instead of fingerprint coverage. Use the resolved labels for Not registered, Employee, Admin, Super Admin, Offline/Error, Has face, and No face.
</action>
<acceptance_criteria>
- Modal shows one row per configured Attendance Machine.
- Each row shows machine IP, role label, and face status.
- Admin status is per-machine, not a global Employee property.
- Offline/error states remain visible and actionable.
</acceptance_criteria>
</task>

<task id="15.7">
<title>Retire or quarantine remaining ZKTeco-only runtime paths</title>
<read_first>
- `backend/src/features/machines/service.py`
- `backend/src/features/machines/router.py`
- `frontend/src/features/machines/components/*`
- `backend/scripts/test_zk.py`
</read_first>
<action>
Find runtime paths that still import or call ZKTeco/PyZK behavior. Remove them when they are no longer relevant, or quarantine them behind clearly named legacy scripts outside application runtime if they are kept for reference.
</action>
<acceptance_criteria>
- App startup does not require the `zk` package.
- Employee and logs workflows do not call PyZK APIs.
- ZKTeco-specific UI controls are no longer reachable in normal navigation.
- Any intentionally retained legacy script is clearly outside runtime.
</acceptance_criteria>
</task>

<task id="15.8">
<title>Verification</title>
<read_first>
- `backend/tests/test_hanvon_client.py`
- `backend/tests`
- `frontend/package.json`
</read_first>
<action>
Add focused tests for Hanvon manager deletion, coverage mapping, Employee list filter behavior, and no-ZKTeco runtime imports where practical. Run backend and frontend checks available in the repo.
</action>
<acceptance_criteria>
- Hanvon client tests cover `DeleteManager`.
- Coverage tests cover employee-only, admin, super admin, not registered, and offline.
- Employee API tests cover pagination and absence of privilege filtering.
- Frontend build/test passes or known unrelated failures are documented.
</acceptance_criteria>
</task>
</tasks>

## Deferred Cleanup

- Drop or migrate legacy DB fields like `privilege`.
- Replace `EmployeeFingerprints` with a Hanvon face-template storage model if the product needs local biometric backup.
- Remove old planning docs that describe ZKTeco as the primary hardware.
