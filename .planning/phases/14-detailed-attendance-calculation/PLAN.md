# Plan: Phase 14 — Detailed Attendance Calculation & Categorization

Bóc tách chi tiết giờ làm việc và tăng ca thành 3 loại: Thường, Nghỉ luân phiên, Ngày lễ. Hỗ trợ bóc tách Tăng ca đêm dựa trên tính chất ca làm việc.

## 1. Database & Persistence
- **File**: `backend/src/database.py`
- **Task**: Thêm cột `shift_category` vào model `ShiftDefinitions`.
  ```python
  shift_category = Column(Unicode(50), nullable=True, default="NORMAL") # NORMAL, REST, HOLIDAY
  ```
- **Action**: Chạy `init_db()` hoặc dùng script migration (nếu cần) để cập nhật DB.

## 2. Logic tính toán (Core Engine)
- **File**: `backend/src/utils/stats_utils.py`
- **Task 2.1**: Cấu trúc lại dữ liệu trả về của `compute_day_stats`. Trả về một dictionary chứa đầy đủ các "giỏ" giờ:
  - `std_normal`, `std_rest`, `std_holiday`
  - `ot_day_normal`, `ot_day_rest`, `ot_day_holiday`
  - `ot_night_normal`, `ot_night_rest`, `ot_night_holiday`
  - `leave_p`, `leave_r`
- **Task 2.2**: Cập nhật logic phân phối OT:
  - Nếu `is_night_shift == True`: 100% OT -> `ot_night`.
  - Nếu `is_night_shift == False`: 100% OT -> `ot_day`.
  - Phân loại vào cột Thường/Nghỉ/Lễ dựa trên `shift_category` của mã ca.

## 3. Backend Service Integration
- **File**: `backend/src/features/daily_summary/service.py`
- **Task**: Cập nhật `process_summary_rows` để bóc tách các trường mới từ dictionary trả về của `compute_day_stats`.

## 4. Excel Export Service
- **File**: `backend/src/features/daily_summary/export_service.py`
- **Task**: Cấu trúc lại Sheet 2 (Chi tiết) để bao gồm 13+ cột chỉ số:
    1. Đi muộn, Về sớm
    2. Giờ công tiêu chuẩn (8/12)
    3. Giờ làm việc ngày thường
    4. Giờ làm việc ngày nghỉ luân phiên
    5. Giờ làm việc ngày lễ
    6. Tăng ca ngày (thường)
    7. Tăng ca ngày (nghỉ)
    8. Tăng ca ngày (lễ)
    9. Tăng ca đêm (thường)
    10. Tăng ca đêm (nghỉ)
    11. Tăng ca đêm (lễ)
    12. Nghỉ phép (P)
    13. Việc riêng (R)

## 5. Frontend Admin UI
- **File**: `frontend/src/features/admin/components/EditShiftModal.vue`
- **Task**: Thêm trường Select `shift_category` vào form quản lý mã ca.

## Verification Checklist
- [ ] DB `ShiftDefinitions` có cột `shift_category`.
- [ ] Ca ngày (`is_night_shift=False`) chỉ tính OT vào cột tăng ca ngày.
- [ ] Ca đêm (`is_night_shift=True`) chỉ tính OT vào cột tăng ca đêm.
- [ ] Mã ca `NLPN` (Rest) đẩy giờ vào đúng các cột `_rest`.
- [ ] Mã ca `NLN` (Holiday) đẩy giờ vào đúng các cột `_holiday`.
- [ ] File Excel xuất ra có đầy đủ 13+ cột ở Sheet 2.
