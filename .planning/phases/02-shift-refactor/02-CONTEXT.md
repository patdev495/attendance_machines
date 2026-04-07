# Phase 2 Context: Shift Refactor & Testing

This phase addresses the technical debt of hardcoded shift rules in [shift_utils.py](file:///d:/Workspace/Time_Attendance_Machine/backend/src/utils/shift_utils.py) and ensures the precision of the attendance system through automated testing.

## 🎯 Objectives
- **Dynamic Configuration**: Shift patterns should be configurable via the database, not hardcoded.
- **Automated Verification**: Stats calculation must be covered by unit tests to prevent regressions.
- **Scalability**: Prepare the system for more complex shift patterns (e.g., rotating shifts, breaks) in future milestones.

## 🏗️ Architecture Design

### 1. ShiftRule Model
The `ShiftRule` table will store the mapping between department/shift-code and the specific work parameters:

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | PK |
| `dept_keyword` | String | Keyword to match in employee's department (e.g., "Xưởng 1") |
| `shift_code` | String | Shift identifier (e.g., "D", "N") |
| `official_start` | Time | Working start time |
| `official_end` | Time | Working end time |
| `end_next_day` | Boolean | Whether the shift ends on the following day (night shifts) |
| `max_hours` | Float | Maximum work hours allowed (null for no limit) |
| `standard_hours` | Float| Standard shift duration (e.g., 8.0, 12.0) |
| `deduct_break` | Boolean | Whether to subtract 1 hour for lunch/rest |
| `has_overtime` | Boolean | Whether hours beyond standard count as OT |

### 2. Logic Migration
`get_shift_rules` will be refactored to query `ShiftRule`:
1. Find a rule matching the `dept_keyword` in the employee's department.
2. Fall back to a default rule (where `dept_keyword` is NULL) if no specific match is found.

### 3. Testing Layer
Tests will be implemented using `pytest` in a new `backend/tests/` directory:
- `conftest.py`: Shared fixtures (database sessions, mock data).
- `test_shift_utils.py`: Unit tests for rule retrieval logic.
- `test_stats_utils.py`: Unit tests for `compute_day_stats` with various tap scenarios (late, early, OT, missing taps).

## 📊 Deployment Strategy
We will execute in 3 waves:
- **Wave 1**: Migration & Seed data (prepopulating with current "Xưởng 1" rules).
- **Wave 2**: Business Logic update (maintaining current behavior via DB).
- **Wave 3**: Full Testing Suite deployment.
