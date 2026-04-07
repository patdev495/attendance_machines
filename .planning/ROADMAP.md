# Roadmap: Time Attendance Machine

## Milestone 1: Refactor & Localize (v1.1)
Goal: Modularize the backend, establish core quality through testing, and implement multi-language support.

### Phase 1: Backend Modularization
- **Goal**: Decompose monolithic `main.py` into routers and services.
- **Depends on**: None
- **Plans**:
  - [ ] Initialize router structure (APIRouter)
  - [ ] Migrate device management logic
  - [ ] Migrate employee management logic
  - [ ] Migrate attendance processing logic

### Phase 2: Core Business Logic Testing
- **Goal**: Verify attendance calculation accuracy with unit tests.
- **Depends on**: Phase 1
- **Plans**:
  - [ ] Setup pytest infrastructure
  - [ ] Write unit tests for `compute_day_stats`
  - [ ] Implement mocks for MSSQL and ZK Protocol

### Phase 3: Multi-language Support
- **Goal**: Implement English, Vietnamese, and Chinese UI.
- **Depends on**: Phase 1
- **Plans**:
  - [ ] Setup vue-i18n in frontend
  - [ ] Create translation bundles (en, vi, zh)
  - [ ] Implement language switcher UI
  - [ ] Update labels and components across the app

### Phase 4: Configurable Rules & Polish
- **Goal**: Remove hardcoded shift rules and finalize the v1.1 release.
- **Depends on**: Phase 2, Phase 3
- **Plans**:
  - [ ] Implement shift configuration API/DB table
  - [ ] Refactor shift calculation to use dynamic rules
  - [ ] Final UI/UX polish and validation
