# Night Pipeline Timeout, Report Format, and Tracking Resolution

## 1. Báo cáo Chuỗi/Batch (User Preference Format)
- Tuyệt đối KHÔNG in từng dòng trạng thái `[OK] Machine N...` gây spam.
- Định dạng chuẩn:
  • **Tổng máy:** <Số lượng>
  • **Success (<Số lượng>):** <Danh sách STT máy>
  • **Fail (<Số lượng>):** <Danh sách STT máy kèm mã lỗi ngắn gọn>

## 2. Hermes Cron Timeout Invariant
- Mặc định scheduler Hermes giới hạn `script_timeout_seconds` ở 3600s (60 phút).
- Chuỗi đêm kết hợp `run_night_chain_pipeline.py` (Phase 1 Reg Gmail + Phase 2 Reg TikTok 20+ targets) chạy 4 batches (6 workers/batch) mất > 60 phút.
- BẮT BUỘC cấu hình: `hermes config set cron.script_timeout_seconds 10800` (3 giờ) để scheduler không kill tiến trình giữa chừng.

## 3. Cạm bẫy Type-Mismatch STT trong Excel Tracking Workbook
- Trong `taikhoan_dat_v2_updated .xlsx`, cột STT (`Máy`) có thể chứa cả số nguyên (`78`) lẫn chuỗi (`'78'`).
- `find_deferred_tracking_slot` và `_check_expected_row` BẮT BUỘC ép kiểu `_int_or_none(ws.cell(row, 1).value)` trước khi so sánh `== stt`.
- Nếu so sánh trực tiếp không ép kiểu, Python trả về `False` (`'78' != 78`), dẫn đến lỗi `RESULT_MISSING_ROW_OR_TIK` hoặc `EXPECTED_STT_78_GOT_78` làm block ghi workbook.

## 4. Triage Lỗi Không Nhận Được OTP
- **Hotmail (Graph API):** Khi Graph API trả về HTTP 200 nhưng không có mail mới từ TikTok, token vẫn sống 100% nhưng TikTok đã rate-limit/chặn gửi OTP về phía máy chủ Microsoft.
- **Gmail app trên máy:** Cần chú ý 2 nguyên nhân:
  1. Tính năng auto-sync của Google Account/Gmail trên thiết bị bị tắt.
  2. Xuất hiện popup che giao diện ("Tăng cường bảo vệ trước lừa đảo", "Mới có trong Gmail") làm che kết quả tìm kiếm OTP.
