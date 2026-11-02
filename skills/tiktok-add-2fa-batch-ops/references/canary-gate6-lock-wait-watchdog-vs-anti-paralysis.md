# Kỷ luật Chống Đóng Băng Khi Chờ Thiết Bị Canary (Anti-Paralysis: Lock-Wait Watchdog vs No-Canary Evasion)

## 1. Bản chất sự cố
- Khi sửa code repo Farm/Device qua pipeline cơ giới hóa (`unified_patch_pipeline.py`), hệ thống bắt buộc qua **S4: Canary Gate 6** trên thiết bị thật.
- Khi toàn bộ máy mục tiêu đang bận chạy ca (dính `SHIFT_BUFFER` 60 phút hoặc active lock) hoặc máy dự kiến 10-15 phút nữa mới xong ca (như M2 ca feed sáng nay):
  - **Hành vi sai phạm nghiêm trọng (Luna paralysis):** Coordinator nói mồm trong chat *"đang chờ máy M2 chạy xong lúc hh:mm rồi bắt M2 chạy"*, sau đó **ĐỨNG IM KHÔNG GỌI TOOL, TREO ĐƠ PHIÊN**.
  - Đây là sự trốn tránh trách nhiệm: không có tiến trình nào theo dõi, dễ bị lãng quên hoặc trôi qua các phiên/chat khác làm task bị bỏ dở.

## 2. Quy trình bắt buộc: Cài Watchdog Canh Nhả Lock Ngay Lập Tức
Khi máy mục tiêu sắp nhả lock hoặc toàn bộ máy đang bận ca:
1. **Tuyệt đối cấm đứng im trong chat**: Phải chuyển việc theo dõi sang cơ giới hóa tự động ngay trong turn hiện tại.
2. **Kích hoạt Watchdog Poller / Cronjob nền**:
   - Sử dụng `cronjob(action='create', ...)` hoặc script nền `terminal(background=True, notify_on_complete=True)` để kiểm tra trạng thái lock của máy mục tiêu theo chu kỳ (mỗi 60s - 120s).
   - Ngay khi file lock được giải phóng (`status != running` và không còn heartbeat): Tự động kích hoạt lệnh Canary runner cho repo mục tiêu.
   - Khi hoàn tất: Tự động thu thập bằng chứng nghiệm thu (`MEDIA:...png`), gửi thông báo kết quả và tự hủy/dừng watchdog.
3. **Báo cáo rõ ràng cho User**:
   - Nêu rõ: (a) Máy đang bận ca nào, (b) Đã cài watchdog/cronjob nào canh nhả lock, (c) Phiên chuyển sang chế độ theo dõi tự động, không gây nghẽn chat.

## 3. Cạm bẫy Tính Streak: Ngày Lịch (Calendar diff_days) vs Ca Chạy Liên Tiếp (Consecutive Sessions)
- **Điểm mù của `max_diff_days` (Grace window)**:
  - Khi code dùng khoảng cách ngày tuyệt đối `diff_days = (today - last_failed).days`:
    - Nếu máy nghỉ xoay tua > 7 ngày, khi chạy lại mà bị nhả thì bị reset về `streak 1` (mất lịch sử lỗi liên tiếp).
    - Ngược lại, nếu giữa 2 lần bị nhả có ca chạy follow thành công, nhưng lần sau cách lần trước <= 7 ngày, nó vẫn cộng dồn thành `streak 2`!
- **Chuẩn hóa logic**:
  - `fail_streak` bắt buộc phải tính theo **số ca chạy bị nhả liên tiếp**.
  - Ngay khi có ca chạy follow thành công (`used > 0` và có lượt follow thật được xác nhận), `fail_streak` phải được reset ngay lập tức.
