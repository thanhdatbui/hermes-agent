# Phân tích kết quả Watchdog & Upload Skip Tránh nhầm lẫn "Khác"

Khi Watchdog tổng kết ca (`feed_session_watchdog.py`) báo cáo:
`• Đăng Video (2/2 - X video đã đăng): ... Bỏ qua (N): Đang dưỡng sinh (A); Khác (B)`

Không được kết luận vội là lỗi kẹt hệ thống hay lỗi script. Hầu hết các ca rơi vào nhãn **Khác** đều là **Gate an toàn chủ động bảo vệ nick** do chính runner kích hoạt.

## 1. Các lý do Skip hợp lệ thường gặp trong nhãn "Khác"
- `account_creation_date_unverifiable`: Nick chưa xác minh được ngày tạo tài khoản trên sheet/workbook -> Age Gate kích hoạt từ chối đăng để chống chết nick non.
- `account_cooling_period_until_YYYY-MM-DD`: Nick đang trong thời gian ngâm cooldown bắt buộc (vừa reg hoặc login chưa đủ số ngày an toàn).
- `already_uploaded_in_shift`: Đã hoàn tất đăng video ở phiên trước của cùng ca chạy.
- `organic-rest-day-no-upload`: Máy rơi vào diện nghỉ dưỡng sinh (~33% organic rest).
- `video_not_rendered` / `missing_video_folder`: Thiếu video trong folder đích.

## 2. Cách kiểm tra O(1) nguyên nhân Skip (CẤM quét đĩa toàn cục)
Cấu trúc thư mục runtime output của mỗi ca:
`D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/row-<row_id>-<run_id>/<batch_id>/machines/machine_<id>/<batch_id>/upload_result.json`

Đọc trực tiếp file `upload_result.json` của máy cần kiểm tra để lấy `status` và `reason` chuẩn xác:
```python
import json

path = r"D:/Taadaa/runtime/kibe/live/2026-09-17/row-7-013052/20260917-015416/machines/machine_1/20260917-015416/upload_result.json"
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
    print(data.get("status"), "|", data.get("reason"))
```
