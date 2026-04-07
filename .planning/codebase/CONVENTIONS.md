# Coding Conventions

## Python (Backend)
- **Style Guide**: Follows PEP 8 for the most part.
- **Naming**:
  - Functions/Variables: `snake_case` (e.g., `get_db`, `employee_id`).
  - Classes: `PascalCase` (e.g., `AttendanceLog`).
  - Constants: `UPPER_SNAKE_CASE`.
- **API Response**: Standard JSON objects. Error handling uses FastAPI `HTTPException`.
- **Database**:
  - Tables: `PascalCase` (e.g., `AttendanceLogs`).
  - Columns: `snake_case` (e.g., `employee_id`, `work_date`).
- **Logic**: Critical business logic (shift math) is currently embedded in API route handlers; consider refactoring to service layers in the future.

## JavaScript/Vue (Frontend)
- **Framework**: Vue 3 with Composition API (`<script setup>`).
- **Naming**:
  - Components: `PascalCase` (e.g., `AttendanceTable.vue`).
  - Variables/Functions: `camelCase`.
- **State**: Centralized in Pinia stores under `src/stores/`.
- **Styling**: Global styles in `src/styles/` and component-scoped CSS.

## File Handling
- Configuration via `.env` file and `config.py`.
- Path management using `pathlib.Path`.
- Logging: Basic logging to files in `backend/logs/` and standard output.

## Documentation
- Self-documenting code with clear variable names.
- OpenAPI/Swagger automatically generated for API endpoints.
