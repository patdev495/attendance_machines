# Agent Instructions

This repo is `Time_Attendance_Machine`, a FastAPI + Vue 3 system for Hanvon Attendance Machines, Employee management, Raw Logs, Daily Summary, Shift Definitions, Biometric Coverage, and Meal Tracking.

## First Read

At the start of a new coding session, read these before broad exploration:

1. `docs/agents/session-bootstrap.md` for architecture, commands, Codegraph usage, and feature entry points.
2. `CONTEXT.md` for domain vocabulary and resolved ambiguities.
3. `docs/agents/domain.md` for agent-facing documentation conventions.

If working in an existing planned phase, also read `.planning/phases/*/PLAN.md` and `SUMMARY.md` for that phase.

## Codegraph

Use Codegraph before large grep/read passes:

- `codegraph_status` to confirm the index exists.
- `codegraph_context` for task-level architecture.
- `codegraph_trace` for one concrete call flow.
- `codegraph_node` for one symbol body.

Do not load the whole project into context. Start from the feature entry point listed in `docs/agents/session-bootstrap.md`, then read only the files needed for the task.

## Domain Language

Use the terms from `CONTEXT.md`:

- Attendance Machine
- Employee
- Raw Log
- Daily Summary
- Shift Definition
- Biometric Coverage
- Machine Manager
- Meal Tracking

Avoid introducing new product-facing ZKTeco vocabulary. Treat older ZKTeco references as historical unless they are reachable runtime behavior.

## Repo Boundaries

- Backend entry: `backend/src/main.py`
- Backend models/session: `backend/src/database.py`
- Backend features: `backend/src/features/<feature>/`
- Frontend entry: `frontend/src/main.js`
- Frontend router: `frontend/src/router/index.js`
- Frontend features: `frontend/src/features/<feature>/`
- Translations: `frontend/src/i18n/locales/{vi,en,zh}.json`

Feature changes should usually stay inside the matching backend/frontend feature folder. Keep router, service, schema, UI, store, and i18n changes aligned.

## Commands

Use `rtk` command prefixes when `rtk` is installed in PATH. If it is unavailable, use raw commands.

Common checks:

```powershell
uv run pytest backend/tests
cd frontend
npm run build
```

Common dev entry points:

```powershell
uv run python backend/src/main.py --host 0.0.0.0 --port 8001
cd frontend
npm run dev
.\dev.bat
```

## Safety

- Preserve existing user changes in the worktree.
- Do not read or edit generated/vendor folders unless required: `frontend/node_modules`, `.venv`, `dist`, `build`, `.pytest_cache`, `backend/static/assets`.
- Prefer additive database changes compatible with MSSQL and SQLite demo/test mode.
- For visible frontend text, update all three locale files: `vi`, `en`, and `zh`.
- Before changing Hanvon protocol behavior, read `research_hanvon_sdk/HANVON_PROTOCOL.md` and add focused tests.

