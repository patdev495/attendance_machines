# Project: Time Attendance Machine

## What This Is
A professional time attendance management system that synchronizes logs from ZKTeco devices, calculates work hours based on complex shift rules, and provides reporting via Excel and a Vue-based UI.

## Context
The project is a brownfield application with a FastAPI (Python) backend and a Vue 3 frontend. It integrates with MSSQL for storage and uses the PyZK SDK for hardware communication. The system has been partially refactored (routers/services split from main.py) but sync_service.py remains monolithic (~647 lines). The current milestone (v2.0) is a full feature-based architecture refactor across both backend and frontend.

## Core Value
To provide accurate, reliable, and user-friendly attendance tracking for diverse workforces, ensuring data integrity from hardware to report.

---

## Current Milestone: v2.0 — Feature-Based Architecture Refactor

**Goal:** Refactor toàn bộ backend và frontend sang kiến trúc vertical feature slices, nâng cấp Employee registry để hỗ trợ "ghost employees" từ máy chấm công và log cũ.

**Target features:**
- **Log Management** — Sync log từ máy → DB, hiển thị/filter raw logs
- **Daily Summary** — Báo cáo ngày, filter đầy đủ, Export Excel, Sync Excel nâng cấp (merge machine users)
- **Employee Management** — Registry thống nhất: Excel + Machine + Log-only. Status phân biệt. Xóa/đổi tên/biometric
- **Machine Management** — Quản lý máy chấm công giống hiện tại

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

### Active (v2.0)
- [ ] [Architecture] Feature-based backend: `features/{logs,daily_summary,employees,machines}/`
- [ ] [Architecture] Feature-based frontend: `src/features/{logs,daily_summary,employees,machines}/`
- [ ] [DB] EmployeeLocalRegistry table: unified employee source tracking
- [ ] [Log] Log sync + raw log view with full filters
- [ ] [Summary] Daily summary with upgraded Excel sync (machine users merged)
- [ ] [Employee] Unified employee list with source_status differentiation
- [ ] [Machine] Machine management (feature-sliced, same behavior)

### Out of Scope
- [Mobile App] — Native mobile application not planned; focus on responsive web.
- [Cloud Hosting] — Designed for on-premise deployment on Windows servers.
- [Automated Testing] — Deferred to a future milestone.
- [Multi-language i18n] — Deferred to a future milestone.

---

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Multi-language Support | Necessary for international operation | Deferred to v3.0 |
| Service Refactoring | Monolithic main.py was a maintenance risk | Completed in v1.x |
| Feature-Based Architecture | sync_service.py (647 lines) unscalable, frontend needs clear boundaries | v2.0 priority |
| EmployeeLocalRegistry | Need to unify Excel/Machine/Log-only employees in one registry | New DB table in v2.0 |
| uv pip for Python deps | Faster, reproducible installs | Project convention |

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
*Last updated: 2026-04-09 — Milestone v2.0 started*
