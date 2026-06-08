# Agent Session Bootstrap

Purpose: give a new coding agent enough context to start work in this repo without rereading the entire project. Read this file first, then use Codegraph for the specific area being changed.

## Start Here

1. Read `CONTEXT.md` for domain vocabulary and resolved ambiguities.
2. Read this file for architecture, commands, and navigation.
3. Use Codegraph before broad file search:
   - `codegraph_status` to confirm the index is present.
   - `codegraph_context` for a task-level map.
   - `codegraph_trace` for a concrete flow between two symbols.
   - `codegraph_node` only when one symbol body is needed.
4. Search/read only the files in the feature being changed.

Current Codegraph snapshot from 2026-06-08: 154 indexed files, 4100 nodes, 9415 edges. Languages: Python, Vue, JavaScript, C#, YAML.

## Product And Domain

This is a Time Attendance Machine system for Hanvon attendance hardware, employee registry management, raw attendance logs, daily attendance summaries, shift definitions, biometric coverage, and canteen meal tracking.

Use the vocabulary from `CONTEXT.md`:

- Attendance Machine: physical biometric terminal. Supported runtime protocol is Hanvon.
- Employee: unified row in the Employee Local Registry.
- Raw Log: physical check-in/check-out event.
- Daily Summary: calculated attendance metrics for one Employee on one date.
- Shift Definition: rules for work windows, break durations, leave, and overtime.
- Biometric Coverage: per-machine registration/role/face capability for an Employee.
- Machine Manager: Hanvon administrator identity on an Attendance Machine.
- Meal Tracking: canteen verification and pickup history.

Avoid introducing new product-facing ZKTeco terminology. Some legacy code/comments may still mention ZKTeco; treat those as historical unless they are reachable runtime behavior.

## Runtime Architecture

Backend:

- Stack: FastAPI, SQLAlchemy, Python 3.12, uv.
- Main app: `backend/src/main.py`.
- DB/session/models: `backend/src/database.py`.
- Config/env: `backend/src/config.py`, loading `backend/.env`.
- Shared hardware/socket helpers: `backend/src/shared/`.
- Feature modules live under `backend/src/features/<feature>/` and usually have `router.py`, `service.py`, and `schema.py`.
- Tests: `backend/tests/`, using in-memory SQLite through `backend/tests/conftest.py`.

Frontend:

- Stack: Vue 3, Vite, Pinia, Vue Router, vue-i18n.
- Entry: `frontend/src/main.js`.
- Router: `frontend/src/router/index.js`.
- Feature pages: `frontend/src/features/<feature>/`.
- Shared layout/components: `frontend/src/components/`.
- Global stores: `frontend/src/stores/`.
- Translations: `frontend/src/i18n/locales/{vi,en,zh}.json`.

Deployment/package shape:

- Built SPA is served by FastAPI from `backend/static`.
- Standalone Windows packaging uses `build_standalone.bat` and `TimeAttendance.spec`.
- Demo mode uses SQLite in `demo_data/attendance.db` and disables real hardware monitoring.

## Important Files

- `machines.txt`: Attendance Machine IPs, optional canteen URL, optional tags such as `nolive`.
- `employee_work_shift.xlsx`: source roster/shift spreadsheet.
- `research_hanvon_sdk/HANVON_PROTOCOL.md`: read before changing Hanvon protocol behavior.
- `.planning/phases/*/PLAN.md` and `SUMMARY.md`: read when continuing a planned phase.
- `docs/agents/domain.md`: agent-facing doc entry points.
- `docs/agents/handoff-2026-06-05-hanvon-employee-management.md`: latest Hanvon Employee Management handoff.

## Backend Routes By Feature

The API is split by feature routers. Use Codegraph route manifest or inspect only the relevant router:

- Logs: `backend/src/features/logs/router.py`
  - raw log listing, date range, sync start/status.
- Daily Summary: `backend/src/features/daily_summary/router.py`
  - summary list, detail view, export, Excel sync.
- Employees: `backend/src/features/employees/router.py`
  - Employee Local Registry list, registry update, export, update/delete, biometric coverage.
- Machines: `backend/src/features/machines/router.py`
  - Attendance Machine list/config/capacity/live status, machine employee CRUD, fingerprint sync/push, global deletes.
- Shift Definitions: `backend/src/features/shift_definitions/router.py`
  - shift definition administration.
- Meal Tracking: `backend/src/features/meal_tracking/router.py`
  - canteen verification and meal kiosk support.

## Frontend Routes

Defined in `frontend/src/router/index.js`:

- `/logs` -> Raw Logs feature.
- `/summary` -> Daily Summary feature.
- `/employees` -> Employee management.
- `/machines` -> machine list.
- `/machines/:ip` -> machine detail.
- `/shifts` -> shift management.
- `/meal` -> meal kiosk.

When changing a page, update the feature view/component, its `api.js`, any Pinia store it uses, and all three locale files if visible text changes.

## Data Model Landmarks

Core SQLAlchemy models are in `backend/src/database.py`:

- `AttendanceLog`
- `EmployeeMetadata`
- `EmployeeLocalRegistry`
- `EmployeeFingerprint`
- `EmployeeDailyShifts`
- `ShiftRule`
- `ShiftDefinition`
- `MealTrackingHistory`
- Demo-only meal tables when `DEMO_MODE=true`

Database changes should be additive and compatible with MSSQL and SQLite demo/test mode. The existing project often uses separate migration scripts under `backend/src/` or `backend/scripts/`.

## Hardware Notes

- Runtime hardware protocol is Hanvon.
- Hanvon client code: `backend/src/features/hanvon/client.py`.
- Machine services: `backend/src/features/machines/service.py`, `biometric_service.py`, `live_monitor.py`, `demo_simulator.py`.
- Real hardware is skipped in `DEMO_MODE=true`; demo live events come from `demo_simulator`.
- Before changing protocol commands, read `research_hanvon_sdk/HANVON_PROTOCOL.md` and add focused tests.

## Commands

Prefer `rtk` prefixes when available because `AGENTS.md` requests it. If `rtk` is not installed in the session PATH, use raw commands.

Backend:

```powershell
uv sync
uv run pytest backend/tests
uv run python backend/src/main.py --host 0.0.0.0 --port 8001
uv run python backend/scripts/db_init.py
```

Frontend:

```powershell
cd frontend
npm install
npm run build
npm run dev
```

Full local dev:

```powershell
.\dev.bat
```

Packaging:

```powershell
.\build_standalone.bat
```

## Testing Guidance

- Backend behavior change: add or update `backend/tests/test_*.py`, then run `uv run pytest backend/tests`.
- Frontend UI/API wiring change: run `npm run build` from `frontend`.
- Shift/date/time calculations: add focused unit tests around `backend/src/utils/shift_utils.py` or `stats_utils.py`.
- Hardware behavior: prefer tests with fake sockets/clients; do not require real Attendance Machines in CI-style tests.
- Database queries should work against test SQLite unless explicitly MSSQL-only.

## Working Conventions

- Keep feature boundaries intact: router handles HTTP, service handles behavior, schema handles request/response shape.
- Prefer existing helpers and feature-local patterns over new abstractions.
- Preserve existing user work in the worktree; this repo often has active uncommitted changes.
- Do not bulk-read `frontend/node_modules`, `.venv`, `dist`, `build`, `.pytest_cache`, or generated static assets.
- If changing domain terminology, update `CONTEXT.md` and consider an ADR under `docs/adr/`.
- If creating GitHub issues, use repo `patdev495/attendance_machines` and conventions in `docs/agents/issue-tracker.md`.

## Fast Task Routing

- Raw Log problem: start with `features/logs`.
- Attendance calculation problem: start with `features/daily_summary`, `utils/shift_utils.py`, and `utils/stats_utils.py`.
- Employee registry problem: start with `features/employees` and `EmployeeLocalRegistry`.
- Machine/biometric/fingerprint problem: start with `features/machines` plus `features/hanvon`.
- Meal kiosk problem: start with `features/meal_tracking`.
- UI route/page problem: start with `frontend/src/router/index.js` and the matching `frontend/src/features/<feature>`.
- Startup/static serving problem: start with `backend/src/main.py` and `backend/src/config.py`.

