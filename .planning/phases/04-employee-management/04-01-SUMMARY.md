---
phase: "04"
plan: "01"
subsystem: "Backend"
tags:
  - schema
  - services
  - employees
requires: []
provides:
  - "Unified employee registry with dual-name and machine synchronization"
  - "Robust per-machine hardware deletion"
affects:
  - "database schema (EmployeeLocalRegistry)"
  - "employee synchronization flow"
tech-stack:
  added: []
  patterns:
    - "Upsert patterns"
    - "Parallel processing for machine operations"
key-files:
  created:
    - "backend/src/features/employees/service.py"
  modified:
    - "backend/src/database.py"
key-decisions:
  - "Added machine_name to EmployeeLocalRegistry to explicitly maintain the hardware name while emp_name handles Excel data."
duration: "3 min"
completed: "2026-04-10T02:22:28Z"
---

# Phase 04 Plan 01: Employee Management Backbone Summary

Started establishing a unified `EmployeeLocalRegistry` which merges three sources (Excel, machines, and logs) and isolates hardware constraints by managing `delete_user_from_hardware` operations centrally.

## Implementation Details

- **Database Schema**: Added the `machine_name` column to the `EmployeeLocalRegistry` in `backend/src/database.py` to allow side-by-side tracking of the formal name (`emp_name`) and the raw hardware name (`machine_name`).
- **Data Synchronization**: Created the `update_registry()` service function inside `backend/src/features/employees/service.py` to upsert users efficiently based on Excel (`EmployeeMetadata`), directly from machines (`machine_only`), and eventually from attendance logs (`log_only`).
- **Parallel Hardware Execution**: Implemented `delete_user_from_hardware()` and `update_employee_info()` using `ThreadPoolExecutor` for safe execution across multiple devices with parallel response tracking. Verified `init_db()` executes correctly with the updated models without syntax or structure failures.

## Verification

The schema changes executed correctly (`init_db()` passes without exceptions), confirming `machine_name` fits securely into the unified registry model.

## Issues Encountered

None - Plan executed exactly as written without blocking structural issues.

## Deviations from Plan

None.

## Requirements Met

*(No specific requirement IDs were listed in 04-01-PLAN.md)*

## Self-Check: PASSED
