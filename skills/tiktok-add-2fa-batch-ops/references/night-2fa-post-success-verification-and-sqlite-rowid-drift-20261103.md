# Night 2FA Post-Success Verification & SQLite RowID Drift Triage (2026-11-03)

## 1. Triệu Chứng Sự Cố (Báo Cáo 2FA Ban Đêm 03/11/2026)
- **Số liệu Telegram Farm Report:**
  * Farm Kibe (Máy 1-80): Hoàn tất 0 | Bỏ qua 58 | Lỗi 51
  * Farm Admin (Máy 201-280): Hoàn tất 0 | Bỏ qua 10 | Lỗi 75
  * Lỗi chi tiết: 126 (`POST_SUCCESS_VERIFICATION_FAILED: 69`, `WORKBOOKERROR: 43`, `PROFILE_NOT_REACHED: 6`, `CONSUMERPREFLIGHTERROR: 5`, `UI_TARGET_AMBIGUOUS:NEXT:0: 2`)
  * File trace: `D:\Taadaa\reports\night_2fa_trace_2026-11-03.log`

---

## 2. Root Cause 1: `POST_SUCCESS_VERIFICATION_FAILED` (69 Máy Cụm Admin)
### Cơ Chế Lỗi:
1. Các tài khoản mục tiêu trên Admin đã có Secret 2FA nhưng mật khẩu rỗng (`blank_pass=True`, `has_2fa=True`), được runner kích hoạt cờ `--password-only`.
2. Trong `run_capture_phase_b.py`:
   ```python
   if cfg.password_only:
       adapter.ensure_account_password_saved()
       goal_completed = True
       print(json.dumps({"status": "success", "phase": "password-only", ...}))
       return 0
   ```
   Worker không hề gọi hàm điều hướng mở TikTok hay mở trang cài đặt tài khoản (`navigate_and_verify_account`).
3. Khi app đang ở Home hoặc tắt ngầm, `ensure_account_password_saved()` quét UI 8 lần không thấy từ khóa "mật khẩu" hay "xác minh danh tính" nên thoát êm (silent return).
4. Worker in `status: "success"` giả tạo và exit 0.
5. Tại parent runner `run_batch_live_2fa.py`, cổng hậu kiểm `_verification()` kiểm tra:
   ```python
   password_saved = not password_is_blank(cfg.workbook_path, workbook_target)
   verified = has_2fa and password_saved and journal_purged and released
   ```
   Do mật khẩu trên Excel/DB vẫn rỗng (`password_saved = False`), runner lật kết quả thành `failed` với mã `POST_SUCCESS_VERIFICATION_FAILED`.

### Nguyên Tắc Bắt Buộc:
- Trong luồng `--password-only`, worker BẮT BUỘC phải thực hiện điều hướng vào Settings/Account/Password của TikTok trước khi quét form.
- CẤM TUYỆT ĐỐI worker trả về `status: "success"` khi chưa thực sự thay đổi/lưu mật khẩu thành công vào hệ thống.

---

## 3. Root Cause 2: `WorkbookError` / `SOURCE_ROW_IDENTITY_MISMATCH` (43 Máy Cụm Kibe)
### Cơ Chế Lỗi:
Sau bản vá chuyển nạp mục tiêu sang SQLite `farm_master.db` (`freeze_targets_from_sqlite`):
1. **Thiếu bộ lọc cụm máy (Cluster Boundary Filter):**
   - Query `SELECT ... FROM tiktok_accounts` lấy toàn bộ máy farm. Cụm Kibe (máy 1–80) bị nạp các máy của Admin (máy 204, 272 với rowid 888, 910...). File Excel của Kibe chỉ có ~640 dòng nên khi kiểm tra các dòng >640 lập tức văng `WorkbookError`.
2. **Đồng nhất sai `a.rowid` với Excel Row (RowID vs Slot Drift):**
   - SQLite `rowid` là ID tự tăng nội bộ (bắt đầu từ 1 cho row đầu tiên chèn vào DB).
   - Trong file Excel `taikhoan_dat_v2_updated .xlsx`, dòng 1 là Header, các dòng tài khoản được mapping theo `video_slot` (`source_row = video_slot + 1` trên cụm Kibe).
   - Ví dụ thực tế máy 3: DB `rowid = 24` là `@oanhuong7758`, nhưng Excel dòng 24 lại là `@brifeqme954`.
   - Khi parent runner kiểm tra `_validate_identity(ws, target, ...)`, thấy username trên Excel khác với username mục tiêu $\rightarrow$ ném `WorkbookError("SOURCE_ROW_IDENTITY_MISMATCH_USERNAME")`.

### Nguyên Tắc Bắt Buộc:
- Truy vấn nạp mục tiêu từ SQLite BẮT BUỘC phải lọc theo dải máy của host thực thi:
  * Kibe: `WHERE CAST(a.machine_id AS INTEGER) BETWEEN 1 AND 80`
  * Admin: `WHERE CAST(a.machine_id AS INTEGER) BETWEEN 201 AND 280`
- `source_row` gửi sang worker để đối soát Excel BẮT BUỘC phải tính từ `a.video_slot + 1` (đối với schema 1-based video slot) hoặc bảng mapping chính xác, TUYỆT ĐỐI KHÔNG dùng bare `a.rowid`.

---

## 4. Kỷ Luật Giữ Khung Giờ Nuôi Feed (Rolling Block Windows)
- Khung giờ 05:05 – 09:30 là **Ca nuôi sáng** của Farm (hàng trăm device lock đang được giữ bởi `tiktok-luot nuoi acc`).
- Khi phát hiện farm alert 2FA ban đêm vào sáng sớm, Coordinator BẮT BUỘC kiểm tra trạng thái lock và khung giờ (`is_safe_rolling_window`).
- TUYỆT ĐỐI CẤM chạy Canary máy thật đè lock thiết bị trong ca nuôi sáng, tránh làm hỏng session lướt feed của farm.
