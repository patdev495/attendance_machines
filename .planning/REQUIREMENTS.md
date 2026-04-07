# Project: Time Attendance Machine - Requirements

## 1. Localization (i18n)
Full support for multiple languages in the web interface and API error messages.

- **Must Have**:
  - Support for English (default), Vietnamese, and Chinese.
  - Language switcher in the frontend header.
  - Persist language preference (Local Storage or user profile).
  - Localization for all labels, menus, and table headers.
- **Should Have**:
  - Localized date/time formats based on locale.
  - Translated backend validation messages.
- **Complexity**: Medium (requires setting up vue-i18n or equivalent).

## 2. Backend Refactoring
Improve the maintainability of the legacy codebase.

- **Must Have**:
  - Split `main.py` into routers (devices, attendance, employees).
  - Extract business logic (calculations) into a `Service` layer.
  - Standardize API response structures.
- **Should Have**:
  - Use Pydantic models for all request/response objects.
  - Cleanup unused code and legacy functions.
- **Complexity**: High (requires understanding 1000+ lines of monolithic logic).

## 3. Automated Testing
Establish a safety net for development.

- **Must Have**:
  - Unit tests for shift and work hour calculation logic (`compute_day_stats`).
  - Integration tests for core API endpoints (device list, attendance retrieval).
  - Setup CI-ready testing environment (pytest).
- **Should Have**:
  - Hardware mocks for ZKTeco machine communication to allow testing without physical devices.
- **Complexity**: Medium.

## 4. Configurable Shift Rules
Transition from hardcoded logic to a dynamic rule system.

- **Must Have**:
  - Database table or config file for shift definitions (Start/End times, break durations).
  - Remove hardcoded "Xưởng 1" keyword logic from `main.py`.
- **Complexity**: Medium.
