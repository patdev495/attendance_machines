# Research: Phase 2 — Log Management

## Phase Domain
Ingestion and display of raw attendance records from ZKTeco hardware devices.

## Existing Logic Map

### Backend
- **Service (`sync_service.py`)**:
  - `sync_all_machines()`: Monolithic function connecting to all IPs, fetching logs, deduplicating via `existing_keys` set, and batch committing to `AttendanceLog` table.
  - `get_machine_list()`: Reads `machines.txt`.
  - `sync_status`: Global dict for tracking progress.
- **Router (`routers/attendance.py`)**:
  - `GET /api/attendance`: Handles logs with filtering (`employee_id`, `machine_ip`, `start_date`, `end_date`) and pagination.
  - `GET /api/attendance/date-range`: Summarizes available log dates.

### Frontend
- **Views**: `RawLogsView.vue` (Legacy).
- **Components**: `AttendanceFilters.vue` (Legacy), `RawLogsTable.vue` (Legacy).
- **Stores**: `attendance.js` (Handles fetching logs) and `sync.js` (Handles triggering the sync task).

## Proposed Feature Slice Migration

### 1. Backend Service (`features/logs/service.py`)
- **Extraction Targets**:
  - `get_machine_list()`
  - `sync_all_machines()`
  - `sync_status` and `status_lock`
- **Improvements**:
  - Add `fail_count` to `sync_status`.
  - Increment `fail_count` in the `except` block of the IP connection loop.

### 2. Backend Router (`features/logs/router.py`)
- **Move Endpoints**:
  - `/api/logs` (from `/api/attendance`)
  - `/api/logs/date-range` (from `/api/attendance/date-range`)
  - `/api/logs/sync` (new endpoint, currently triggers via legacy `machines` router)
  - `/api/logs/sync/status` (new endpoint)

### 3. Frontend Component Migration
- **New Feature Entry Point**: `features/logs/index.vue`
- **Refactored Components**:
  - `features/logs/components/LogsFilters.vue` (Top bar layout as requested).
  - `features/logs/components/LogsTable.vue` (Standard paginated table).
  - `features/logs/components/SyncStatus.vue` (Integrated status display).

## Risks & Mitigations
- **Deduplication Logic**: Ensure the existing set-based deduplication in `sync_all_machines` is preserved exactly to avoid data corruption.
- **Auto-Refresh**: Use a watcher on `syncStore.syncRunning` or a message bus to trigger `loadData()` after the background task completes.
