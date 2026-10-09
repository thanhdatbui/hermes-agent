# Chẩn đoán & Cơ chế Farm Alert từ Cronjob (Taadaa Farm)

## 1. Cơ chế Bắn Alert khi Chạy Cron Nuôi Acc (`tiktok-luot nuoi acc`)
- **Producer:** Trong `python_runner/flows/multi_machine_feed_session.py`, khi thiết bị gặp lỗi dừng (`child.final_status not in ("success", "degraded")`) hoặc khi các hook (`follow-hook`, `upload-hook`) gặp timeout / launch error, hàm `send_farm_machine_alert` từ thư viện `automation-core` được gọi trực tiếp.
- **Consumer/Target:** Gửi tin cảnh báo kèm banner đỏ và ảnh hiện trường máy về Telegram group `Farm Alerts` (`-5373649734`).

## 2. Vì sao Cron báo lỗi mà Farm Alert không nhận được tin nhắn?
Khi quan sát thấy script cron chạy có lỗi (hoặc báo cáo phiên có máy lỗi) nhưng nhóm Farm Alert im lặng, cần kiểm tra 3 nguyên nhân cốt lõi sau:

### A. Phân biệt "Lỗi script/xác minh" trong Báo cáo Phiên vs "Lỗi Dừng Máy"
- Báo cáo tổng kết phiên do `scripts/hermes_cron/feed_session_watchdog.py` tổng hợp gửi về nhóm nuôi acc (`-5377611430`).
- Nếu máy hoàn thành chu trình lướt Feed thành công (`status == "success"`), nhưng đến bước Follow Hook hoặc Upload Hook gặp lỗi (rỗng danh sách nick, không tìm thấy nút follow, thiếu file video, sub-process timeout...):
  - Watchdog xếp máy đó vào dòng `Lỗi script/xác minh`.
  - Tuy nhiên, vì mục tiêu nuôi feed chính đã pass, runner không xếp máy vào nhóm lỗi dừng phiên khẩn cấp (`final_status == "failed"`), do đó **không kích hoạt `send_farm_machine_alert`**.

### B. Cơ chế Deduplication Claim (`_claim_machine_alert_once`) & Mạng Telegram Degraded
- Trong `multi_machine_feed_session.py`, hàm `_claim_machine_alert_once` tạo file khóa `D:/Taadaa/runtime/kibe/live/alert-claims/<session_key>/machine_<N>.claimed` trước khi gọi `send_farm_machine_alert`.
- Khi Telegram API bị nghẽn mạng, timeout (ví dụ lỗi `live adapter delivery to telegram failed: send_path_degraded; Timed out`):
  - Hàm `send_alert()` bắt Exception và fail.
  - Nhưng file `.claimed` vẫn tồn tại theo nguyên tắc fail-closed để chống spam kép.
  - Các lần quét / tick cron tiếp theo trong cùng ca/phiên thấy file `.claimed` đã tồn tại sẽ tự động bỏ qua, không thử gửi lại.

### C. Lỗi ở Cấp Launcher / Wrapper bên ngoài vòng lặp máy
- Nếu lỗi script xảy ra ở tầng launcher (như PowerShell wrapper `run-feed-session.ps1`, `tiktok_runner.py`, lỗi cú pháp, đọc workbook, manifest JSON hỏng...):
  - Tiến trình dừng ngay trước khi dispatch vào vòng lặp máy con.
  - Vì không có ngữ cảnh của thiết bị cụ thể (`machine=N`), hàm `send_farm_machine_alert(machine=N, ...)` không được gọi.
  - Hermes Cronjob có cấu hình `deliver: "local"` sẽ chỉ lưu log nội bộ trên máy host mà không tự động bắn Telegram nếu exit code != 0.
