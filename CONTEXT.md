# Time Attendance Machine

A system designed to synchronize employee biometric data, track daily work shifts, and calculate attendance and canteen meal usage records.

## Language

**Attendance Machine**:
A physical biometric terminal used by employees to clock in/out. The supported vendor protocol is Hanvon.
_Avoid_: Terminal, scanner, clocking machine

**Employee**:
A unified record in the **Employee Local Registry** representing an individual, categorized by sources (Excel-synced, Machine-only, Log-only).
_Avoid_: User, staff, registry list

**Biometric Coverage**:
A per-machine view of whether an **Employee** is registered on each **Attendance Machine** and what machine role or biometric capability exists there.
_Avoid_: Coverbio, fingerprint coverage, device presence

**Machine Manager**:
An administrator identity registered directly on a Hanvon **Attendance Machine**.
_Avoid_: Dashboard admin, operator, ZKTeco privilege

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

**BarTender Print Agent**:
A lightweight client-side background service (running locally on port 8080) that automates BarTender card printing via COM.
_Avoid_: Print service, local printer driver

**Employee Card Printing**:
The process of generating layout data (6-slot grid of name, ID, department, group, and photo URLs) to print employee badges on A4 templates.
_Avoid_: Badge maker, card printing


## Relationships

- An **Employee** registry entry is linked to many **Raw Logs**
- An **Employee** can have **Biometric Coverage** on zero or more **Attendance Machines**
- An **Employee** can also be a **Machine Manager** on zero or more **Attendance Machines**
- A **Daily Summary** is computed for exactly one **Employee** on a specific date
- A **Daily Summary** uses **Raw Logs** and the active **Shift Definition** to calculate hours
- A **Meal Tracking** history log records a canteen event for one **Employee**

## Example dialogue

> **Dev:** "If an **Employee** has a **Raw Log** but no matching record in the Excel roster, how are they represented?"
> **Domain expert:** "They are saved in the **Employee Local Registry** with a source status of 'machine_only'."

## Flagged ambiguities

- "privilege" was used for ZKTeco-style employee permissions; resolved: Employee Management no longer uses global privilege filters, and Hanvon admin status is represented as per-machine **Machine Manager** coverage.

- "user" was used to mean both **Employee** in the registry and **Operator** managing the dashboard — resolved: we use **Employee** for attendance/biometric tracking and **Operator** for system management.

- "giờ quẹt trưa / lunch swipes": user requested monitoring lunch start and return times without changing existing work hour / payroll formulas — resolved: lunch swipes are captured as supplementary monitoring fields (`lunch_out`, `lunch_in`, `lunch_duration`, `lunch_status`) on **Daily Summary** and do not alter `work_hours` or `first_tap`/`last_tap` calculation. `lunch_out` is defined as the first **Raw Log** between 11:20 and 12:40. `lunch_in` is defined as the first **Raw Log** after `lunch_out` with a minimum 5-minute separation (`timestamp >= lunch_out + 5 min`). System explicitly separates work shift statuses (`MISSING_WORK_IN`, `MISSING_WORK_OUT`) from lunch break monitoring statuses (`MISSING_LUNCH_OUT`, `MISSING_LUNCH_IN`, `NO_LUNCH_SWIPE`, `OK`).

