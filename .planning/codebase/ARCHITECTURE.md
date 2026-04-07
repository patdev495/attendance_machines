# Architecture

## System Overview
The Time Attendance System is a decoupled web application with a FastAPI backend and a Vue 3 frontend. It manages real-time data from ZKTeco attendance machines and synchronizes it with a central SQL Server database.

## Backend Architecture
- **API Framework**: FastAPI (Asynchronous REST API).
- **Concurrency**:
  - Uses `BackgroundTasks` for long-running operations like database synchronization and Excel generation.
  - Threading is used specifically for the Excel export status management.
- **Data Access Layer**:
  - SQLAlchemy ORM for database interactions.
  - PyODBC as the low-level driver for MSSQL.
- **Business Logic**:
  - `sync_service.py`: Contains hardware-specific logic for communicating with ZKTeco devices (via PyZK) and handling file-based sync (Excel).
  - `main.py`: Contains API endpoints and complex shift/attendance calculation logic (e.g., `compute_day_stats`).

## Frontend Architecture
- **Framework**: Vue 3 with Single File Components (SFCs).
- **State Management**: Pinia (Modules for device status, attendance data, and sync progress).
- **Build System**: Vite.
- **UI Components**: Native HTML/CSS (Vanilla) with a focus on responsiveness.

## Data Flow
1. **Device -> Backend**: `sync_service.py` connects to machines via IP, downloads logs, and inserts them into `AttendanceLogs`.
2. **Backend -> Database**: SQLAlchemy persists logs and updates employee metadata.
3. **User -> Frontend**: Users request reports or trigger syncs.
4. **Backend -> User**: FastAPI computes statistics on-the-fly or serves exported Excel files.

## Shift Rules
The system implements custom shift rules based on department keywords (e.g., "Xưởng 1"). It handles both Day (8 AM - 5/8 PM) and Night (8 PM - 5/8 AM next day) shifts with logic for late arrivals, early departures, and overtime calculation.
