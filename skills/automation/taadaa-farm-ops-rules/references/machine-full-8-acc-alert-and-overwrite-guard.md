# Quy tắc Cảnh báo Mất cân bằng Máy Đủ 8 Acc vs Excel Thiếu Slot & Hard Guard Ghi đè

## 1. Bối cảnh & Hiện tượng (Incident 2026-09-21)
- Khi máy thực tế trên TikTok app đã đạt đủ 8 tài khoản nhưng file Excel tracking bị thiếu dòng hoặc bị đè slot (ví dụ Máy 27 có 8 nick nhưng Row 215 để trống do ghi đè nhầm lên Row 211):
  + Preflight reg (`_detect_clean.py`) đọc Excel thấy máy thiếu nick nên tiếp tục cấp target và cử máy đi reg.
  + TikTok app khi đã có đủ 8 nick trong switcher sẽ tự động ẩn hoàn toàn nút *"Thêm tài khoản"* (hoặc đổi resource-id dropdown sang `ndk`).
  + Runner trước đây không phân biệt được nguyên nhân, chỉ văng lỗi: `[04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)`.
  + Hậu quả: Người vận hành tưởng app bị crash UI/timeout và tiếp tục retry mù, trong khi thực tế máy đã full 8 nick và tài sản cũ có nguy cơ bị ghi đè.

## 2. Quy tắc Xử lý & Báo động Bắt buộc (User Invariant)
1. **Tại tầng thiết bị (`social_reg_v1.py`)**:
   - Khi tìm nút thêm tài khoản trong dropdown, đếm số node tài khoản hiện có qua các resource-id: `["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"]`.
   - Nếu `count >= 8`:
     + Log rõ ràng: `Máy đã có {count} tài khoản — đạt giới hạn tối đa 8`.
     + Dismiss dropdown về màn hình Home: `keyevent 4` (Back) + `keyevent 3` (Home).
     + Ném mã lỗi chuẩn: `RuntimeError("[04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok")`.
2. **Tại tầng Telegram Alert (`ensure_row_accounts.py` hàm `_extract_reg_error`)**:
   - BẮT BUỘC parse mã lỗi `MACHINE_FULL_8_ACCOUNTS` thành cảnh báo đỏ trực diện:
     `"Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)"`
   - TUYỆT ĐỐI CẤM che giấu thành lỗi "Không tìm thấy nút" hoặc "Lỗi không xác định".
3. **Hard Guard Chống Ghi Đè Tài Sản Cũ (`_validate_tracking_overwrite_guard` & `deferred_tracking_writer.py`)**:
   - Điều kiện kiểm tra chống ghi đè:
     ```python
     if (existing_id or existing_pass) and (not existing_mail or existing_mail != new_mail):
         raise RuntimeError(f"CRITICAL_OVERWRITE_PREVENTED: Cannot overwrite existing account @{existing_id} ({existing_mail})")
     ```
   - Chặn cả khi `existing_mail` bị trống: Nếu hàng đã có username hoặc mật khẩu mà email bị trống hoặc khác email mới -> FAIL-CLOSED tuyệt đối, cấm ghi đè.

## 3. Quy chuẩn Folder Video Admin (Dải Chuẩn 1..640)
- Dàn máy Admin (Máy 201..280) đánh số Folder Video liên tục theo thứ tự trong cụm:
  $$\text{Folder Video} = (\text{STT} - 201) \times 8 + \text{Slot (1..8)}$$
- Tuyệt đối không dùng công thức tuyệt đối của Kibe `(STT - 1) * 8 + Slot` ghi đè vào Excel Admin làm sinh ra các số folder ảo `1624, 2106, 2108...` gây lệch pha kho video render.
