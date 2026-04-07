# Project: Time Attendance Machine

## What This is
A professional time attendance management system that synchronizes logs from ZKTeco devices, calculates work hours based on complex shift rules, and provides reporting via Excel and a Vue-based UI.

## Context
The project is a brownfield application with an existing FastAPI (Python) backend and a Vue 3 frontend. It integrates with MSSQL for storage and uses the PyZK SDK for hardware communication. The current focus is on improving system quality, refactoring the legacy monolithic backend, and localizing the interface for international use.

## Core Value
To provide accurate, reliable, and user-friendly attendance tracking for diverse workforces, ensuring data integrity from hardware to report.

---

## Requirements

### Validated
- ✓ [Backend] FastAPI integration with MSSQL 2008.
- ✓ [Hardware] Synchronization with ZKTeco machines via PyZK.
- ✓ [Data Management] Excel-based employee metadata import.
- ✓ [Reporting] Attendance summary calculation with shift-aware logic.
- ✓ [Frontend] Vue 3 / Vite dashboard with real-time status updates.
- ✓ [Export] Asynchronous Excel export system with progress tracking.

### Active
- [ ] [Architecture] Refactor `main.py` into a service-oriented structure (Routers, Services, Utils).
- [ ] [Testing] Implement automated unit tests for shift calculations and integration tests for API endpoints.
- [ ] [Localization] Add multi-language support (English, Vietnamese, Chinese), default to English.
- [ ] [Refinement] Make shift rules configurable instead of hardcoded keywords.
- [ ] [Stability] Implement hardware simulation/mocking for reliable development without physical devices.

### Out of Scope
- [Mobile App] — Native mobile application is not currently planned; focus is on responsive web.
- [Cloud Hosting] — System is designed for on-premise deployment on Windows servers.

---

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Multi-language Support | Necessary for international operation across regions. | Added to Roadmap |
| Service Refactoring | Monolithic main.py (1000+ lines) is a maintenance risk. | Priority 1 |
| Automated Testing | Current lack of tests prevents safe refactoring. | Baseline Req |

---

## Evolution
This document evolves at phase transitions and milestone boundaries.

**After each phase transition**:
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions

**After each milestone**:
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-07 after mapping and initial goal alignment*
