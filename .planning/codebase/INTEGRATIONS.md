# Integrations

## Internal Integrations

### Database (Microsoft SQL Server)
- **Primary Server**: `192.168.209.18`
- **Database Name**: `MIS`
- **Tables**:
  - `AttendanceLogs`: Stores raw punch-in/out data.
  - `EmployeeMetadata`: Stores employee names, departments, shifts, and status.
- **Mechanism**: SQLAlchemy ORM via ODBC Driver 18 for SQL Server.

### File System
- **`machines.txt`**: Flat file listing IP addresses and names of attendance machines.
- **`employee_work_shift.xlsx`**: Excel file used for importing/exporting employee schedules and master data.

## External Integrations

### Attendance Machines (ZKTeco)
- **Protocol**: ZK Protocol (via PyZK SDK).
- **Functionality**:
  - Real-time data synchronization.
  - User management (downloading/uploading finger templates).
  - Device status monitoring (capacity, serial number).
- **Mechanism**: Direct socket connection via IP (port 4370 usually).

## Frontend-Backend Communication
- **API Style**: RESTful JSON API.
- **Endpoints**:
  - `/api/devices/*`: Device management.
  - `/api/attendance/*`: Attendance data retrieval and syncing.
  - `/api/employees/*`: Employee metadata management.
