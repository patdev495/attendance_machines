# Project State: Time Attendance Machine

## Current Milestone
- **Name**: v3.0 — Comprehensive Multi-language Support (i18n)
- **Status**: Starting
- **Progress**: 0% (Requirements defined)

## Active Phase
- **Phase**: None
- **Goal**: Initialize milestone v3.0.

## Accumulated Context

### Project Vision
Refactor completed (v2.0). Now focusing on professionalizing the application with full internationalization (i18n) support for English, Vietnamese, and Chinese.

### Architecture
- Feature-based vertical slices in both backend and frontend.
- `EmployeeLocalRegistry` unifies Excel, Machine, and Log-only sources.
- `i18n` setup exists in `frontend/src/i18n`.

### Key Constraints
- Windows OS deployment.
- MSSQL 2008 compatibility.
- Hardware dependency on ZKTeco (PyZK).
- `uv pip` for Python packages.
- **i18n**: English is the default and fallback.

### Roadmap Evolution
- v1.x: Backend modernization.
- v2.0: Feature-based architecture refactor (Completed 2026-04-10).
- v3.0: Comprehensive Multi-language Support (Started 2026-04-10).

---
*Last updated: 2026-04-10*
