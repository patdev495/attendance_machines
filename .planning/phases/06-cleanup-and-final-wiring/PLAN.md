# Plan: Phase 6 — Cleanup & Final Wiring

Finalize the v2.0 refactor by removing all legacy code, updating documentation, and verifying the end-to-end functionality.

## Waves

### Wave 1: Backend Cleanup
- [ ] **6-01-01** — Delete `backend/src/routers/`
- [ ] **6-01-02** — Delete `backend/src/services/`
- [ ] **6-01-03** — Delete `backend/src/sync_service.py`
- [ ] **6-01-04** — Update `backend/src/main.py` cleanup

### Wave 2: Frontend Cleanup
- [ ] **6-02-01** — Delete `frontend/src/api/`
- [ ] **6-02-02** — Delete `frontend/src/views/` (Legacy views)
- [ ] **6-02-03** — Update `frontend/src/router/index.js` cleanup

### Wave 3: Final Documentation & Verification
- [ ] **6-03-01** — Update `ROADMAP.md` and `STATE.md`
- [ ] **6-03-02** — Verify all features work end-to-end

## Verification
- `uv run uvicorn backend.src.main:app --reload`
- `npm run dev`
- Manual check of all 4 features.
