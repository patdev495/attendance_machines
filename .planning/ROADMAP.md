# Roadmap: Time Attendance Machine — v3.0

## Milestone v3.0: Comprehensive Multi-language Support (i18n)
Goal: Chuyển đổi toàn bộ giao diện dự án sang đa ngôn ngữ (EN, VI, ZH), đảm bảo không còn chuỗi text cứng.

**Numbering:** Phases 7–12 (Continuing from v2.0)
**Strategy:** Chuyển đổi theo từng feature slice. Mỗi phase hoàn thiện bản dịch và code cho 1 feature.

---

### Phase 7: i18n Foundation & Layout
- **Goal**: Hoàn thiện bộ từ điển chung, setup language switcher trong Header và chuyển đổi layout.
- **Requirements**: I18N-01, I18N-02, I18N-03, I18N-04, I18N-05
- **Plans**:
  - [ ] **7-01** — Cập nhật `en.json`, `vi.json`, `zh.json` với các chuỗi common (Pagination, Modals, Nav, Toasts).
  - [ ] **7-02** — Chuyển đổi `AppSidebar.vue`: Sử dụng `$t('nav...')` cho tất cả menu items.
  - [ ] **7-03** — Chuyển đổi `AppHeader.vue`: Thêm dropdown chọn ngôn ngữ (EN/VI/ZH). Tích hợp logic `setLanguage` từ `i18n/index.js`.
  - [ ] **7-04** — Chuyển đổi shared components: `PaginationBar.vue`, `ConfirmModal.vue`, `ToastNotification.vue`.

---

### Phase 8: Employee Management i18n
- **Goal**: Chuyển đổi toàn bộ Registry nhân viên sang đa ngôn ngữ.
- **Requirements**: I18N-06, I18N-07, I18N-08, I18N-09
- **Plans**:
  - [ ] **8-01** — Cập nhật dictionaries với keys cho `employees` feature (Headers, Actions, Statuses).
  - [ ] **8-02** — Chuyển đổi `EmployeesView.vue`: Header, Filter bar, Search placeholder, Sync/Bulk buttons.
  - [ ] **8-03** — Chuyển đổi `EmployeesTable.vue`: Headers và action buttons/tooltips. Chuyển đổi source status badges logic.
  - [ ] **8-04** — Chuyển đổi các Modals: `EditEmployeeModal.vue`, `EmployeeDetailsModal.vue`, `BiometricCoverageModal.vue`.

---

### Phase 9: Daily Summary i18n
- **Goal**: Chuyển đổi báo cáo ngày và các filters.
- **Requirements**: I18N-10, I18N-11, I18N-12, I18N-13
- **Plans**:
  - [ ] **9-01** — Cập nhật dictionaries cho `attendance` feature (Summary cụ thể).
  - [ ] **9-02** — Chuyển đổi `DailySummaryView.vue`: Page title và Layout.
  - [ ] **9-03** — Chuyển đổi `SummaryFilters.vue`: Toàn bộ labels, placeholders và select options (Shift types, Employee statuses).
  - [ ] **9-04** — Chuyển đổi `SummaryTable.vue`: Headers, Status badges ("Late", "Early"), và các ghi chú tính toán.

---

### Phase 10: Log Management i18n
- **Goal**: Chuyển đổi Raw Log view và quá trình đồng bộ.
- **Requirements**: I18N-14, I18N-15, I18N-16, I18N-17
- **Plans**:
  - [ ] **10-01** — Cập nhật dictionaries cho `logs` feature.
  - [ ] **10-02** — Chuyển đổi `LogsView.vue`: Header và sync banners.
  - [ ] **10-03** — Chuyển đổi `LogsFilters.vue`: Labels cho Date/IP filters.
  - [ ] **10-04** — Chuyển đổi `LogsTable.vue`: Headers.

---

### Phase 11: Machine Management i18n
- **Goal**: Chuyển đổi quản lý thiết bị và thông số kỹ thuật.
- **Requirements**: I18N-18, I18N-19, I18N-20
- **Plans**:
  - [ ] **11-01** — Cập nhật dictionaries cho `machines` và `device` features.
  - [ ] **11-02** — Chuyển đổi `MachineListView.vue` và `MachineCard.vue`: Chi tiết cấu hình terminal.
  - [ ] **11-03** — Chuyển đổi `MachineDetailView.vue`: Toàn bộ thông số capacity và action buttons.

---

### Phase 12: Final Audit & Verification
- **Goal**: Kiểm tra lại toàn màn hình ở cả 3 ngôn ngữ, đảm bảo không còn string nào bị sót.
- **Plans**:
  - [ ] **12-01** — Sử dụng script scan để tìm các chuỗi text nằm ngoài `$t()`.
  - [ ] **12-02** — Verify UI Alignment: Kiểm tra các button và label ở tiếng Trung (ngắn) và tiếng Việt (dài) để đảm bảo layout không bị vỡ.
  - [ ] **12-03** — Final Walkthrough: Kiểm tra trải nghiệm người dùng khi chuyển đổi ngôn ngữ nóng (hot-reload language).

### Phase 13: Điều chỉnh cách tính công và tăng ca

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 12
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 13 to break down)

---

## Phase Summary

| Phase | Goal | Requirements | Effort |
|-------|------|--------------|--------|
| 7 | Foundation & Layout | I18N-01 to I18N-05 | Medium |
| 8 | Employee Management | I18N-06 to I18N-09 | High |
| 9 | Daily Summary | I18N-10 to I18N-13 | Medium |
| 10 | Log Management | I18N-14 to I18N-17 | Low |
| 11 | Machine Management | I18N-18 to I18N-20 | Medium |
| 12 | Audit & Verification | All | Low |

**Total**: 6 phases for Milestone v3.0
