# Testing State

## Current Coverage
- **Automated Tests**: None. The `backend/tests` directory is currently empty.
- **Manual Testing**:
  - The system relies on manual verification of API endpoints via the Swagger UI (`/docs`).
  - Frontend verification via browser interaction.
  - Hardware integration testing using `backend/scripts/test_zk.py`.

## Testing Infrastructure
- **Tools**: `pytest` is likely intended for the backend (standard for FastAPI), but not yet implemented.
- **Mocking**: No mocks exist for the ZKTeco hardware or the MSSQL database.

## Improvement Areas
- [ ] Implement unit tests for shift calculation logic (`compute_day_stats`).
- [ ] Implement integration tests for API endpoints using a test database.
- [ ] Create hardware simulators or mocks to test `sync_service.py` without physical devices.
- [ ] Set up frontend unit testing (e.g., Vitest).
