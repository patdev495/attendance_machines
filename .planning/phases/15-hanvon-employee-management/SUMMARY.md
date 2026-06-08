# Summary 15 - Hanvon Employee Management

Commit: `c474e79 Implement Hanvon employee management updates`

## Delivered

- Converted Employee Management and Raw Log device workflows to Hanvon-only behavior.
- Removed global Employee privilege filtering from the Employee tab.
- Added Hanvon Biometric Coverage with per-machine role and face status.
- Added deletion support for both Employee and Machine Manager identities.
- Kept bulk deletion scoped to the user-selected Attendance Machines.
- Added machine-detail edit flow for Employee/Machine Manager information.
- Fixed SQL Server overflow caused by casting large string Employee IDs to integer.
- Added i18n coverage for machine-detail table headings, actions, add/edit modals, sync modal, and machine card labels.

## Verification

- Backend tests passed with `uv run pytest backend/tests`.
- Frontend production build passed with `npm run build`.

## Follow-up Notes

- Legacy database fields such as `privilege` remain for compatibility; do not reintroduce them as global Employee UI concepts.
- ZKTeco references in old docs/scripts should be treated as legacy unless a runtime path still calls them.
- Future protocol-level decisions should be captured in `docs/adr/`.
