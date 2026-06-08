# Domain Docs

This is a single-context repo.

## Read first

- `docs/agents/session-bootstrap.md` for session startup context, architecture, commands, and feature entry points.
- `CONTEXT.md` at the repo root for domain vocabulary and resolved ambiguities.
- `.planning/phases/*/PLAN.md` and `SUMMARY.md` when working in an existing phase.
- `research_hanvon_sdk/HANVON_PROTOCOL.md` before changing Hanvon device behavior.

There is currently no `docs/adr/` directory. If an architectural decision needs to be preserved, create an ADR under `docs/adr/`.

## Vocabulary rules

Use the terms from `CONTEXT.md` in code review notes, issue titles, PRDs, plans, and tests.

Important current terms:

- **Attendance Machine**: physical biometric terminal. The supported runtime protocol is Hanvon.
- **Employee**: unified row in the Employee Local Registry.
- **Biometric Coverage**: per-machine registration, role, and face capability for an Employee.
- **Machine Manager**: Hanvon administrator identity registered directly on an Attendance Machine.

Avoid reviving ZKTeco vocabulary in new work. Legacy names may still exist in old code or planning files, but new product-facing behavior should use Hanvon terms.
