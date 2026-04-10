# Context: Phase 2 — Log Management

## Phase Domain
Ingestion and display of raw attendance records from ZKTeco hardware devices into the local SQL database.

## Decisions

### 1. Synchronization Behavior
- **Scope**: Always sync from ALL machines listed in configuration. No partial machine selection required. [LOCKED]
- **Auto-Refresh**: The Raw Log table must automatically refresh data once a background sync task completes. [LOCKED]
- **Error Visibility**: When machines fail to connect, display a summary count (e.g., "3 machines failed") in the progress banner rather than specific IP details. [LOCKED]

### 2. User Interface
- **Filter Layout**: Maintain the existing pattern of placing filters in a top bar above the data table. [LOCKED]

## Technical Implications (for Researcher/Planner)
- **State Management**: Need a way to signal the Logs view to refresh when the global sync status changes from `isRunning: true` to `false`.
- **Sync Logic**: Migrate `sync_all_machines` from `sync_service.py` but ensure it returns/tracks a failure count for the UI.
- **Scaffolding**: Use the `features/logs/` structure established in Phase 1.

## Deferred Ideas
- *N/A*

---
*Generated: 2026-04-09 — Discussion finalized*
