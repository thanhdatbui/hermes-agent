# Machine Full 8 Accounts Mismatch & Hard Overwrite Guard

## Bối cảnh & Incident (2026-09-21)
- Khi app TikTok trên thiết bị đã đủ 8 nick (`MACHINE_FULL_8_ACCOUNTS`) nhưng file Excel tracking (`taikhoan_dat_v2_updated .xlsx`) bị thiếu dòng hoặc bị đè slot (ví dụ Máy 27 có đủ 8 nick nhưng Row 215 để trống):
  - Preflight reg (`_detect_clean.py`) đọc Excel thấy thiếu slot nên tiếp tục cấp target và cử máy đi reg.
  - TikTok app khi có đủ 8 nick sẽ tự động ẩn hoàn toàn nút "Thêm tài khoản".
  - Runner trước đây không phân biệt được nguyên nhân, chỉ văng lỗi `[04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)`.
  - User feedback: *"vấn đề là đã đủ 8 tài khoản mà excel ghi thiếu thì script phải báo về tao kiẻm tra chứ"*.

## Quy tắc Xử lý & Báo động Bắt buộc
1. **Tại tầng thiết bị (`social_reg_v1.py`)**:
   - Nhận diện đủ 8 nick qua resource-id của TikTok (bao gồm cả resource-id mới `ndk`).
   - Khi `count >= 8`: dismiss dropdown về Home và raise `RuntimeError("[04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok")`.
2. **Tại tầng báo động Telegram (`ensure_row_accounts.py` -> `_extract_reg_error`)**:
   - BẮT BUỘC parse lỗi `MACHINE_FULL_8_ACCOUNTS` thành cảnh báo đỏ trực diện:
     `"Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)"`
   - TUYỆT ĐỐI CẤM che giấu thành lỗi "Không tìm thấy nút" hoặc "Lỗi không xác định".
3. **Hard Guard Chống Ghi Đè Tài Sản Cũ (`deferred_tracking_writer.py` & `social_reg_v1.py`)**:
   - Điều kiện:
     ```python
     if (existing_id or existing_pass) and (not existing_mail or existing_mail != new_mail):
         raise RuntimeError(f"CRITICAL_OVERWRITE_PREVENTED: Cannot overwrite existing account @{existing_id} ({existing_mail})")
     ```
   - Chặn tuyệt đối kể cả khi `existing_mail` bị trống. Nếu hàng đã có username hoặc pass mà email khác hoặc email cũ trống -> FAIL-CLOSED cấm ghi đè.
4. **Quy chuẩn Folder Video Admin (Dải Chuẩn 1..640)**:
   - Dàn máy Admin (Máy 201..280) đánh số Folder Video liên tục theo thứ tự trong cụm:
     $$\text{Folder Video} = (\text{STT} - 201) \times 8 + \text{Slot (1..8)}$$
   - Tuyệt đối không dùng công thức tuyệt đối của Kibe `(STT - 1) * 8 + Slot` ghi đè vào Excel Admin làm sinh ra các số folder ảo `1624, 2106, 2108...`.
