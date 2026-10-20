# Kỷ luật Cập nhật Script Watchdog & Toán học Chu kỳ 4 Ngày (96h)

## 1. Kỷ luật Bắt buộc: Script-First over Memory-Only
- **Sự cố điển hình:** Khi Operator chỉ thị: *"Các nick mới bị chậm 1 ca thì không cần báo trong report đâu"*, Agent vội vã lưu ghi chú vào `memory` rồi báo cáo xong việc.
- **Nguyên nhân sai lầm (Anti-Pattern):** 
  - Cronjob watchdog trên farm chạy độc lập với cờ `no_agent: True`. Scheduler chỉ bắt `stdout` từ script Python để gửi thẳng lên Telegram channel.
  - Ghi chú vào `memory` của Coordinator hoàn toàn không có tác dụng đối với output của cronjob. Ngày hôm sau, watchdog vẫn in 108 cảnh báo ảo như cũ!
- **Invariant bắt buộc:**
  - Mọi yêu cầu thay đổi logic lọc/ngưỡng/định dạng báo cáo bắt buộc phải **sửa trực tiếp vào codebase / script lõi** (`audit_stale_upload_accounts.py` và `cron_stale_upload_watchdog.py`).
  - Phải chạy unit test tập trung (`pytest tests/test_audit_stale_upload_accounts.py`) để kiểm chứng trước khi kết luận.

---

## 2. Toán Học Chu Kỳ 4 Ngày (96h) và Ngưỡng Cảnh Báo Trễ
Mỗi slot tài khoản (Tik 1 đến Tik 8) trên một máy Samsung S7 tuân thủ nghiêm ngặt chu kỳ xoay vòng 4 ngày (96h):
- **Khoảng cách tự nhiên:** 4 ngày giữa 2 lần chạy liên tiếp của cùng một slot.
- **Bóc tách mức độ trễ:**
  - $\le 4$ ngày: Đang chạy đúng nhịp chu kỳ bình thường.
  - $5 - 8$ ngày (hoặc $\le 9$ ngày tính cả ngày dưỡng sinh / jitter): **Mới chỉ chậm 1 ca**. Đây là dao động tải thông thường (do lag UI, timeout gallery, rớt mạng tạm thời, hoặc chờ cữ reboot 11:35). Nick sẽ tự động đăng bù ở ca tiếp theo $\rightarrow$ **CẤM đưa vào danh sách cảnh báo trễ**.
  - $9 - 14$ ngày: **Trễ $\ge 2$ ca liên tiếp** $\rightarrow$ Đây mới là ngưỡng thực sự cần theo dõi (`days_threshold = 9`).
  - $> 14$ ngày: **Nguy cơ đóng băng** ($\ge 3 - 4$ ca không có video mới) $\rightarrow$ Ngưỡng báo động đỏ (`critical_threshold = 14`).
- **Hiệu quả thực tế:**
  - Nâng `days_threshold` từ 7 lên 9 ngày giúp loại bỏ 65 cảnh báo ảo, đưa số nick "đang đăng đều" từ 788 lên 853 nick và giảm cảnh báo trễ từ 108 xuống 43 nick.

---

## 3. Chẩn đoán & Phục hồi ADB Transport Socket Freeze (M74 Pattern)
- **Dấu hiệu nhận biết:**
  - Lệnh inspect máy (`inspect_machine.py <N>`) bị timeout sau 30s – 60s.
  - Thiết bị vẫn có mặt trong danh sách `adb devices` (trạng thái `device`).
  - Mở socket tới port 5037 gửi `host:transport:<serial>` trả về `OKAY`, nhưng lệnh `shell:` hoặc `exec:` tiếp theo bị treo vĩnh viễn do nghẽn buffer daemon `adbd` trên điện thoại.
- **Quy trình cứu hộ $O(1)$ không cần reboot máy:**
  1. Gửi lệnh `host-serial:<serial>:reconnect` (hoặc `adb -s <serial> reconnect`).
  2. Chờ 2–3 giây để daemon tái thiết lập transport layer.
  3. Kiểm tra lại bằng lệnh nhẹ `shell getprop ro.product.model` $\rightarrow$ thiết bị phản hồi ngay lập tức.
  4. Chụp ảnh màn hình kiểm chứng (bắt buộc WinRT OCR kiểm tra màn hình đích trước khi gửi `MEDIA:`).
