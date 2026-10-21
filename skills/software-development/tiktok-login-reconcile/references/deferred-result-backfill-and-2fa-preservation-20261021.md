# Cứu Hộ Nick Thiếu Pass/Mail Từ Deferred Result JSON, Bẫy Đè Mất 2FA Secret & Kỷ Luật Guard Điều Phối (21/10/2026)

## 1. Hiện Tượng & Chẩn Đoán Lỗi Mất Phiên Ảo (`ACCOUNT_MISSING`)
- **Triệu chứng**: Batch alert hoặc ca nuôi lướt Feed báo P0 văng account:
  `[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found. Cần MANUAL_REVIEW: kiểm tra TikTok đã login chưa`
- **Khám nghiệm hiện trường O(1)**:
  1. Mở UI XML hoặc dùng WinRT OCR đọc ảnh Switcher tại thời điểm dừng ca (`profile_preflight_switcher_1_guard/attempt_1/screen.png`).
  2. Nếu màn hình Switcher hiển thị đủ 7 nick cũ và hàng thứ 8 là nút `Thêm tài khoản` (bounds `[0, 1788][1080, 1920]`):
     * **Khẳng định 100%**: Toàn bộ nick cũ trên máy vẫn nguyên vẹn.
     * Đây là lỗi **Slot-Fill (Nạp thiếu nick mục tiêu)** của ca chạy (ví dụ Row 7), KHÔNG PHẢI lỗi văng nick cũ.
  3. Kiểm tra danh sách tracking: `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --list`:
     * Nếu thấy dòng: `- [CHECK] tik=... id=<USER> email=- login_email=- issues=missing_tiktok_pass,missing_mail_pass,missing_email`
     * Nguyên nhân cốt lõi: Dòng tracking trong `taikhoan_dat_v2_updated .xlsx` có ID và 2FA nhưng để trống cột D (PASS) và cột F (GMAIL). Runner cha gọi `tiktok_login_v1.py` tự cứu hộ nhưng vì thiếu cả pass lẫn email nên kẹt tại form đăng nhập cho đến khi timeout 388s.

---

## 2. Truy Xuất Nguồn Gốc & Khôi Phục Thông Tin Xác Thực (Zero-Hallucination)
- **CẤM TUYỆT ĐỐI** tự bịa pass hoặc điền password tạm vào file production.
- **Truy xuất Source of Truth**:
  1. Tìm file kết quả đăng ký deferred:
     `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\*\batch_*\stt_<STT>\tracking_result_stt<STT>_*.json`
  2. Đối chiếu nhật ký đăng ký gốc: `D:/Taadaa/Tiktok_Reg/social_reg_log.txt`:
     Tìm dòng `[ACCOUNT_RECORD] STT: <STT> | ... | Email: ... | TikTok: @<USER> | TT_Pass: ... | Mail_Pass: ...`
  3. Lấy chính xác bộ 3 thông tin: `password`, `email`, `mail_password`.

---

## 3. Bẫy Nguy Hiểm Khi Ghi Đè Workbook (`deferred_tracking_writer.py`)
Khi dùng công cụ có sẵn `apply_deferred_tracking_results.py` / `deferred_tracking_writer.py`, cẩn thận 2 bẫy chết người:
1. **Bẫy `OVERWRITE_REJECTED` (Line 273)**:
   ```python
   if (existing_id or existing_pass) and (not existing_mail or existing_mail != new_mail):
       return TrackingWriteResult("BLOCKED_DATA_CONFLICT", blocker=f"OVERWRITE_REJECTED_EXISTING_ACCOUNT_{existing_id}_{existing_mail}")
   ```
   Nếu trên Excel ô email đang rỗng (`not existing_mail`), hàm sẽ chặn đứng không cho ghi đè.
2. **Bẫy Xóa Mất 2FA Secret (Line 288)**:
   ```python
   result.get("twofa") or None
   ```
   File JSON đăng ký từ đợt reg ban đầu thường chưa có 2FA (`"twofa"` rỗng). Nếu chạy ghi đè mù quáng, giá trị `None` sẽ **xóa sạch mã bí mật 2FA TOTP (`TYYJ...`)** đã được thêm vào cột E ở các đợt chạy bảo mật sau!
3. **Quy tắc an toàn**:
   * Luôn backup file Excel trước khi chỉnh sửa (`.bak_<timestamp>`).
   * Khi backfill, BẮT BUỘC giữ nguyên 100% cột E (`twofa`), chỉ điền bù vào cột 4 (`PASS`), cột 6 (`GMAIL`), cột 7 (`PASS MAIL`).
   * Chạy kiểm tra hậu kiểm: `python D:/Taadaa/tools/excel_preflight_validator.py` phải đạt `PASS 100%`.

---

## 4. Kỷ Luật Terminal Guard Của Coordinator
1. **`python -c` chỉ dùng read-only**: Guard chặn mọi lệnh `python -c` chứa thao tác ghi (`shutil`, `open(..., 'w')`, `subprocess`). Muốn thực thi logic ghi/sửa data, phải tạo script Python dưới `D:/Taadaa/tools/` hoặc tái sử dụng script tạm.
2. **Tránh tiền tố `env -u PYTHONPATH`**: Guard Coordinator chặn tiền tố `env` vì nằm ngoài allowlist `python ...`. Chạy trực tiếp `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <USER> --ss`.
3. **Event-Driven Background cho tác vụ > 30s**: Quá trình đăng nhập TikTok kéo dài 30s - 90s, vượt quá ngân sách foreground 60s của guard. Bắt buộc khởi chạy với `background=True, notify_on_complete=True, timeout=300`.
