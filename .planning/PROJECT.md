# Project: Time Attendance Machine

## What This Is
A professional time attendance management system that synchronizes logs from ZKTeco devices, calculates work hours based on complex shift rules, and provides reporting via Excel and a Vue-based UI.

## Context
The project is a brownfield application with a FastAPI (Python) backend and a Vue 3 frontend. It integrates with MSSQL for storage and uses the PyZK SDK for hardware communication. The system has been partially refactored (routers/services split from main.py) but sync_service.py remains monolithic (~647 lines). The current milestone (v2.0) is a full feature-based architecture refactor across both backend and frontend.

## Core Value
To provide accurate, reliable, and user-friendly attendance tracking for diverse workforces, ensuring data integrity from hardware to report.

---

## Current Milestone: v3.0 — Comprehensive Multi-language Support (i18n)

**Goal:** Chuyển đổi toàn bộ 100% giao diện sang đa ngôn ngữ (English, Vietnamese, Chinese), đảm bảo đồng nhất và không còn text cứng.

**Target features:**
- **Layout & Shared** — Đa ngôn ngữ cho Header, Sidebar, Pagination, Toasts, Modals.
- **Log Management** — Đa ngôn ngữ cho LogsView, Table, Filters và status messages.
- **Daily Summary** — Đa ngôn ngữ cho SummaryView, Table, Filters, Export/Sync dialogs.
- **Employee Management** — Đa ngôn ngữ cho EmployeesView, Table, Edit/Details/Biometric modals.
- **Machine Management** — Đa ngôn ngữ cho Machine Views, Cards, terminal actions.

**Tooling note:** Python packages → `uv pip install`

---

## Requirements

### Validated
- ✓ [Backend] FastAPI integration with MSSQL 2008.
- ✓ [Hardware] Synchronization with ZKTeco machines via PyZK.
- ✓ [Data Management] Excel-based employee metadata import.
- ✓ [Reporting] Attendance summary calculation with shift-aware logic.
- ✓ [Frontend] Vue 3 / Vite dashboard with real-time status updates.
- ✓ [Export] Asynchronous Excel export system with progress tracking.
- ✓ [Backend] Routers/Services split from main.py completed.
- ✓ [Architecture] Feature-layered backend and frontend (Vertical Slices) (v2.0).
- ✓ [Employee] Unified EmployeeLocalRegistry with source_status differentiation (v2.0).
- ✓ [Feature] Full Log, Summary, Employee, and Machine feature implementations (v2.0).

### Active (v3.0)
- [ ] [i18n] 100% UI hardcoded strings removed and replaced with `$t()`.
- [ ] [Local] Complete English (en.json), Vietnamese (vi.json), and Chinese (zh.json) dictionaries.
- [ ] [Feature] Multi-language support for Layout, Shared Components, and all 4 main features.
- [ ] [UI] Language selector in AppHeader with persistence.

### Out of Scope
- [Mobile App] — Native mobile application not planned; focus on responsive web.
- [Cloud Hosting] — Designed for on-premise deployment on Windows servers.
- [Automated Testing] — Deferred to a future milestone.
- [Multi-language i18n] — Deferred to a future milestone.

---

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Multi-language Support | Necessary for international operation | v3.0 priority |
| Service Refactoring | Monolithic main.py was a maintenance risk | Completed in v1.x |
| Feature-Based Architecture | sync_service.py (647 lines) unscalable, frontend needs clear boundaries | v2.0 priority |
| EmployeeLocalRegistry | Need to unify Excel/Machine/Log-only employees in one registry | New DB table in v2.0 |
| uv pip for Python deps | Faster, reproducible installs | Project convention |
| **DB Immutability** | Existing tables (ShiftRules, AttendanceLogs, EmployeeMetadata, EmployeeFingerprints) must NOT be altered — only new tables may be added | Hard constraint — enforced throughout v2.0 |

---

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:**
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone:**
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-10 — Milestone v3.0 started*
