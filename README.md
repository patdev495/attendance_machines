# Time Attendance System

A modern Vue 3 + FastAPI system for managing employee attendance across multiple ZK protocol machines.

## Project Structure

```text
Time_Attendance_Machine/
├── backend/
│   ├── src/           # FastAPI application & business logic
│   ├── scripts/       # DB initialization & testing scripts
│   ├── config/        # Configuration management
│   ├── static/        # Compiled frontend assets
│   └── logs/          # Application logs (git-ignored)
├── frontend/          # Vue 3 Single Page Application
├── machines.txt       # List of machine IPs (one per line)
└── employee_work_shift.xlsx # Source for employee synchronization
```

## Setup & Running

### 1. Prerequisite
- Python 3.10+
- Node.js & npm (for frontend)
- [uv](https://github.com/astral-sh/uv) (recommended)
- MSSQL Server 2008+

### 2. Backend Setup
1. Create a `.env` file in the `backend/` directory based on `.env.template`.
2. Install dependencies: `uv pip install -r requirements.txt`
3. Initialize the database: `python backend/scripts/db_init.py`

### 3. Frontend Setup
1. `cd frontend`
2. `npm install`

### 4. Running the Application

#### Development Mode
- Backend: `uv run uvicorn backend.src.main:app --host 0.0.0.0 --port 8001 --reload`
- Frontend: `cd frontend && npm run dev`

#### Production (Single Port)
1. Build the frontend: `cd frontend && npm run build` (Output will be in `backend/static`)
2. Run backend: `uv run uvicorn backend.src.main:app --host 0.0.0.0 --port 8001`
3. Access via `http://localhost:8001`

## Synchronization
- Use the Dashboard UI to trigger synchronization from ZK machines.
- Employee metadata is synced from the root `employee_work_shift.xlsx` file.
