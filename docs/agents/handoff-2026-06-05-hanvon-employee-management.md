# Handoff: Hanvon Employee Management

Date: 2026-06-05

Latest relevant commit: `c474e79 Implement Hanvon employee management updates`

## Scope completed

The Employee Management work has been implemented and committed. Use the commit and `.planning/phases/15-hanvon-employee-management/PLAN.md` as the source of truth for the full change set.

Key outcomes:

- Runtime and UI behavior now target Hanvon-only Attendance Machines for Employee and Raw Log workflows.
- Employee list no longer exposes global ZKTeco-style privilege filtering.
- Biometric Coverage now reports per-machine registration, role, and face capability.
- Employee and Machine Manager deletion paths delete both Hanvon identities where applicable.
- Machine detail management supports adding, editing, syncing, and deleting Employees/Managers with i18n coverage.
- SQL Server Employee ID sorting no longer casts large string IDs to integer.

## Verification already run

- `uv run pytest backend/tests` passed during implementation.
- `npm run build` passed after the final i18n changes.

## Known remaining documentation and cleanup targets

- Legacy ZKTeco references may still exist in older planning docs or scripts. Treat them as historical unless they are reachable at runtime.
- `CONTEXT.md` already records Hanvon-only domain vocabulary and the resolved `privilege` ambiguity.
- No ADR exists yet. If future work changes the supported device protocol again, create an ADR under `docs/adr/`.
- The repo did not have `AGENTS.md` or `CLAUDE.md` when this handoff was written, so no root agent instruction file was created.

## Suggested skills for the next session

- Use `diagnose` for runtime/device bugs.
- Use `grill-with-docs` before changing domain behavior around Employees, Biometric Coverage, or Machine Managers.
- Use `tdd` for risky backend behavior changes.
- Use `to-issues` if the remaining cleanup needs to be split into GitHub issues.
