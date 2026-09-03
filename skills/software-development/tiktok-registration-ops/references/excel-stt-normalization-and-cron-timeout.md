# Excel STT Normalization, Deferred Tracking Apply & Hermes Cron Timeout

## 1. Excel STT Type Mismatch Pitfall (String vs Integer)
- **Vấn đề:** Trong các file workbook như `taikhoan_dat_v2_updated .xlsx`, cột `Máy` (STT) có thể bị lưu dưới dạng chuỗi (ví dụ: `'78'`) thay vì số nguyên (`78`).
- **Hậu quả:** Các phép so sánh trực tiếp như `ws.cell(row_idx, 1).value == stt` hoặc `row_stt != stt` trong Python sẽ trả về `False` / `True` sai lệch (`'78' != 78`), dẫn đến:
  - `find_deferred_tracking_slot` không tìm thấy slot trống cho máy, trả về `("", "")` -> `RESULT_MISSING_ROW_OR_TIK`.
  - `deferred_tracking_writer` báo lỗi xung đột giả: `BLOCKED_DATA_CONFLICT` kèm blocker `EXPECTED_STT_78_GOT_78`.
- **Quy chuẩn sửa bắt buộc:** Luôn chuẩn hóa STT trước khi so sánh hoặc ghi:
  ```python
  def _int_or_none(val):
      try:
          return int(val) if val not in (None, "") else None
      except (ValueError, TypeError):
          return None

  if _int_or_none(ws.cell(row_idx, 1).value) == stt:
      ...
  ```

## 2. Hermes Cronjob `no_agent` Timeout Pitfall
- **Vấn đề:** Hermes scheduler mặc định giới hạn thời gian chạy của script trong `no_agent=True` là 3600 giây (60 phút). Nếu một chuỗi batch dài (ví dụ: Reg Gmail + Reg TikTok 22+ targets qua 4 batch) chạy mất > 60 phút (như 64 phút), Hermes scheduler sẽ ngắt timeout tiến trình launcher tại đúng mốc 1 giờ và gửi thông báo lỗi:
  `⚠️ Cron '<name>' failed: provider timeout. Fallback chain was exhausted or unavailable. Full details saved in cron output.`
- **Giải pháp:**
  - Cấu hình tăng timeout script trong Hermes config:
    `hermes config set cron.script_timeout_seconds 10800` (3 giờ).
  - Đảm bảo launcher script có logic tự động chạy `apply_deferred_tracking_results.py` và sync `taikhoan_run_safe.xlsx` ngay sau khi runner hoàn tất.

## 3. Quy chuẩn định dạng báo cáo Batch / Cron cho User
- **Tuyệt đối không spam:** Cấm in từng dòng `[OK] Machine X...` hoặc văn xuôi dài dòng.
- **Định dạng chuẩn:**
  - Tách rõ từng Phase (Phase 1: Reg Gmail, Phase 2: Reg TikTok).
  - Báo đúng 3 dòng tóm tắt:
    • **Tổng máy:** <Số lượng>
    • **Thành công (<Số lượng>):** <Danh sách STT máy>
    • **Thất bại (<Số lượng>):** <Danh sách STT máy kèm lỗi cụ thể>
