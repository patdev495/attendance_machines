# Time Attendance Machine

A system designed to synchronize employee biometric data, track daily work shifts, and calculate attendance and canteen meal usage records.

## Language

**Attendance Machine**:
A physical biometric terminal used by employees to clock in/out. The default supported vendor protocol is Hanvon; ZKTeco is treated as a legacy override during migration.
_Avoid_: Terminal, scanner, clocking machine

**Employee**:
A unified record in the **Employee Local Registry** representing an individual, categorized by sources (Excel-synced, Machine-only, Log-only).
_Avoid_: User, staff, registry list

**Raw Log**:
A timestamped entry representing a physical check-in or check-out event on an **Attendance Machine**, regardless of which supported vendor protocol produced it.
_Avoid_: Punch log, swipe record

**Daily Summary**:
Calculated attendance metrics (work hours, late arrival, early departure, overtime) for a single **Employee** on a given calendar day.
_Avoid_: Workday report, calculated log

**Shift Definition**:
A set of rules defining work time windows, break durations, and overtime categories (Normal, Rest, Holiday) for a specific shift code.
_Avoid_: Work shift, schedule

**Meal Tracking**:
A verification system checking meal registration status for canteen pickups on canteen-enabled **Attendance Machines**.
_Avoid_: Lunch log, food kiosk

## Relationships

- An **Employee** registry entry is linked to many **Raw Logs**
- A **Daily Summary** is computed for exactly one **Employee** on a specific date
- A **Daily Summary** uses **Raw Logs** and the active **Shift Definition** to calculate hours
- A **Meal Tracking** history log records a canteen event for one **Employee**

## Example dialogue

> **Dev:** "If an **Employee** has a **Raw Log** but no matching record in the Excel roster, how are they represented?"
> **Domain expert:** "They are saved in the **Employee Local Registry** with a source status of 'machine_only'."

## Flagged ambiguities

- "user" was used to mean both **Employee** in the registry and **Operator** managing the dashboard — resolved: we use **Employee** for attendance/biometric tracking and **Operator** for system management.
