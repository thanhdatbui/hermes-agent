# Triage Case: Bỏ Qua Đăng Video Diện Rộng Trên Báo Cáo Watchdog Feed Session (Row >= 5) & Chính Sách Để Trống Ngày Tạo

## 1. Hiện Tượng Thực Tế
Trên báo cáo tổng kết watchdog `📊 [TIKTOK NUÔI ACC] Ca 3 - Phiên 1/2 (Tối) hoàn tất (Row 5)`:
- **Farm Kibe (Máy 1-80):** Đăng Video Success (25), Lỗi script/xác minh (6), **Bỏ qua (46): Khác (46)**.
- **Farm Admin (Máy 201-280):** Đăng Video Success (0), Lỗi script/xác minh (0), **Bỏ qua (48): Chưa render/thiếu video (6); Khác (42)**.
- Người vận hành đặt câu hỏi: *"Sao bỏ qua video nhiều vậy?"*

---

## 2. Quy Trình Điều Tra O(1) Bóc Tách Root Cause
Không đoán mò hay quét đĩa diện rộng, kiểm tra trực tiếp qua 2 nguồn dữ liệu:
1. **Kiểm tra `upload_result.json` trong thư mục run live:**
   - Thư mục: `D:/Taadaa/runtime/kibe/live/<date>/row-<R>-<time>/.../upload_result.json`
   - Bóc tách theo `(status, reason)`:
     - `('skipped', 'account_creation_date_unverifiable')`: 45 máy (Kibe).
     - `('skipped', 'missing_account_id')`: 42 máy (Admin).
     - `('skipped', 'video_not_rendered')`: 6 máy (Admin).
     - `('skipped', 'account_cooling_period_until_...')`: 1 máy.
2. **Kiểm tra file master workbook `taikhoan_dat_v2_updated .xlsx` & `Tik5.xlsx`:**
   - **Kibe:** Ở Slot 5 (Row 5), có 41/80 máy có ID tài khoản nhưng cột `NGÀY TẠO` (cột 8) để trống (`None`).
   - **Admin:** Ở Slot 5 (Row 5), chỉ có 13/80 máy có tài khoản, 67 máy còn lại chưa reg đến Row 5 (`missing_account_id`). Với 13 máy có tài khoản, thư mục video tương ứng trên máy Admin (`D:\TIKTOK-videonuoinick-admin\<folder>`) chưa render sẵn file video `.mp4`.

---

## 3. Cơ Chế Ban Đầu vs Chỉ Đạo Vận Hành Mới

### Thiết kế cũ (Fail-Closed):
- Theo logic trong `python_runner/flows/upload_preflight.py` (`check_upload_cooldown_eligibility`):
  - Hàng cũ (**Row 1..4**): Nick trưởng thành -> Luôn cho phép đăng.
  - Hàng mới (**Row >= 5**, bao gồm Tik 5, Tik 6...): Bắt buộc kiểm tra ngày tạo tài khoản.
  - Nếu cột ngày tạo trong Excel bị `None` hoặc không thể xác minh: Kích hoạt cơ chế **Fail-Closed**, trả về `account_creation_date_unverifiable` và chặn đăng video để tránh vi phạm chính sách đăng video trên nick non/chưa ngâm.

### Chỉ đạo vận hành từ User (2026-09-21):
- *"Để trống ngày tạo thì đc phép đăng luôn vì các nick đó reg lâu r. K thì m gán đại ngày tạo vào để đủ điều kiện đăng cho t"*
- **Quy tắc mới áp dụng:**
  - Với các tài khoản để trống ngày tạo trong master workbook (`created_date is None`): **Coi như tài khoản cũ đã reg từ lâu**, lập tức cho phép đăng video:
    ```python
    if created_date is not None:
        min_allowed_date = max(
            created_date + timedelta(days=CREATION_COOLDOWN_DAYS),
            BENCHMARK_MIN_UPLOAD_DATE,
        )
    else:
        # Để trống ngày tạo: cho phép đăng luôn (coi như nick cũ reg lâu rồi)
        return True, "ok", current_date
    ```
  - Trả về `(True, "ok", current_date)` thay vì `(False, "account_creation_date_unverifiable", None)`.

---

## 4. Kiểm Thử Nghiệm Thu (Verification)
- Đơn vị test: `tests/test_upload_age_gate_focused.py` và `tests/test_upload_preflight_col_fallback.py`.
- Trường hợp `created_date = None`: assert `ok is True`, `reason == "ok"`.
