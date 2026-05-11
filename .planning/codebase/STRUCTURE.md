# Project Structure

```text
Time_Attendance_Machine/
├── .planning/                  # GSD Project planning and codebase mapping
│   └── codebase/               # [CURRENT] Structure, stack, and arch docs
├── backend/                    # FastAPI Backend
│   ├── scripts/                # Database initialization and testing utilities
│   ├── src/                    # Core backend logic
│   │   ├── config.py           # Configuration and environment loading
│   │   ├── database.py         # SQLAlchemy models and connection
│   │   ├── main.py             # API endpoints and business logic
│   │   └── sync_service.py     # Device and hardware integration SDK
│   ├── static/                 # Static files for production serving
│   ├── tests/                  # Unit and integration tests
│   ├── .env                    # Local environment variables (not in git)
│   └── requirements.txt        # Python dependencies
├── frontend/                   # Vue 3 Frontend
│   ├── src/
│   │   ├── api/                # API client interface
│   │   ├── components/         # Reusable UI components
│   │   ├── stores/             # Pinia state management
│   │   ├── views/              # Page components
│   │   ├── App.vue             # Root component
│   │   └── main.js             # Frontend entry point
│   ├── package.json            # Frontend dependencies
│   └── vite.config.js          # Vite configuration
├── employee_work_shift.xlsx    # Employee schedule data file
├── machines.txt                # List of attendance machine IPs
└── README.md                   # Project overview
```

## Key Directories

### `backend/src/`
The heart of the system. `main.py` is currently a combined endpoint and logic file (approx 1000 lines), while `sync_service.py` handles the complexities of the ZK Protocol.

### `frontend/src/`
Organized following Vue best practices. Views are separated from components, and state is localized in Pinia stores.

### Root Directory
Contains configuration files (`machines.txt`) and data sources (`employee_work_shift.xlsx`) that are critical for the synchronization process.
