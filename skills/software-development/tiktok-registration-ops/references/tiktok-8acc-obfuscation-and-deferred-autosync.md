# TikTok 8-Account Obfuscation & Deferred Auto-Sync (17/09/2026)

## 1. TikTok Obfuscated Resource-IDs (Trần cứng 8 tài khoản)
- **Hiện tượng**: Khi máy đã đủ 8 nick, app TikTok ẩn nút "Thêm tài khoản".
- **Lỗi cũ**: Hàm `tap_add_account` đếm số nick bằng ID `n72` và `lkp`. Trên app TikTok mới, ID bị obfuscate thành:
  `["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli"]`
  Nếu thiếu các ID này, code đếm ra 0 nick và raise lỗi sai cấu trúc `[04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)`.
- **Giải pháp chuẩn**: Match đầy đủ tập `any(k in rid for k in ["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli"])`. Nếu `>= 8`: raise `MACHINE_FULL_8_ACCOUNTS`, gửi keyevent 4 (Back) thoát sheet và keyevent 3 (Home).

## 2. Auto-Sync Deferred Tracking JSON to Excel (`_run_all_targets.py`)
- **Nguyên nhân gốc rễ lệch pha Excel ↔ Máy thật**:
  Khi chạy batch với `--defer-tracking-write`, worker con chỉ ghi file tạm `tracking_result_stt*.json`.
  Runner batch coi mình là `proof-only launcher` nên đặt cờ `target['workbook_write'] = 'NOT_ATTEMPTED_BY_LOCAL_LAUNCHER'` và không sync vào file Excel `taikhoan_dat_v2_updated .xlsx`.
  Hậu quả: Máy thật có nick nhưng Excel bỏ trống → Ca nuôi đọc Excel thấy thiếu lại đòi reg tiếp → Đụng trần 8 nick trên máy.
- **Quy trình Auto-Sync sau batch**:
  Ngay sau khi tất cả worker con hoàn thành, launcher tự động gom các file `result_json` thành công và gọi `write_deferred_results_sequential` với exclusive write lease và backup workbook trước khi ghi.

## 3. Dynamic Slot Fallback trong `deferred_tracking_writer.py`
- Khi apply deferred json, nếu `tracking_row`/`tik` bị trống hoặc dòng mong muốn bị drift do batch cũ/đã có nick khác:
  `_check_expected_row` tự động gọi `resolve_tracking_slot(ws, stt, email_l)` để tìm slot trống hợp lệ tiếp theo của máy và điền vào thay vì chặn bằng lỗi `BLOCKED_DATA_CONFLICT (RESULT_MISSING_ROW_OR_TIK)` hoặc `EXPECTED_EMAIL_...`.
