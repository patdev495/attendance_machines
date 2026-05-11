# Technical Concerns & Debt

## High Priority
- **Lack of Automated Testing**: The absence of tests for critical business logic (attendance calculation) and API endpoints makes the system fragile during refactoring.
- **Monolithic `main.py`**: At nearly 1000 lines, `main.py` contains too much logic. It handles routing, database aggregation, complex shift math, and Excel generation. This should be broken down into routers, services, and utils.
- **Hardware Coupling**: The system depends on physical ZKTeco devices for testing. A mock SDK or hardware simulator is needed for isolated development.

## Medium Priority
- **Shift Rule Hardcoding**: Shift rules are currently hardcoded based on department string keywords (e.g., "Xưởng 1"). This is inflexible if business rules change.
- **State Management in Export**: The Excel export process uses a global `export_status` dictionary with a threading lock. While sufficient for a small number of users, it could lead to race conditions or memory issues if significantly expanded.

## Low Priority / Future-Proofing
- **Database Dependency**: The system is tightly coupled to MSSQL 2008 and specific ODBC drivers. Upgrading the database or moving to a different platform would require significant changes.
- **Sync Performance**: Syncing many machines sequentially could be slow. Parallelizing machine syncs within `sync_all_machines` might be necessary as the number of devices grows.
- **Frontend/Backend Synchronization**: Ensure that the frontend's interpretation of "Work Date" matches the backend's (especially for night shifts).
