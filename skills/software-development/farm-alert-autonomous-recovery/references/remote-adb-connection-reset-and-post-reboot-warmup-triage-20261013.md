# Remote ADB Connection Reset & Post-Reboot Warmup Buffer Protocol (2026-10-13)

## 1. Hiện tượng & Triệu chứng
- Ngay sau ca Auto-Reboot (ví dụ sau mốc 11:35), tại phiên chạy đầu tiên (12:00 / 12:07), một cụm remote (như Farm Admin máy 201–280) đồng loạt báo lỗi hàng loạt:
  - Watchdog báo: `Fail (69): M201..M279 Mất kết nối ADB/USB`.
  - Nhưng sau đó ở phiên kế tiếp (14:30), toàn bộ cụm lại tự động chạy thành công bình thường (60+ máy SUCCESS) mà không có bất kỳ can thiệp phần cứng nào.

## 2. Truy vết hiện trường O(1) & Root Cause
- Đọc `summary.txt` hoặc `run_manifest.json` của 1 máy bất kỳ trong cụm lỗi (ví dụ machine 201):
  ```text
  stop_reason: device is offline or ADB/USB disconnected for ce071827e07a093701: adb.exe: protocol fault (couldn't read status): connection reset
  ```
- **Cơ chế gây lỗi (Root Cause):**
  1. Phone farm mật độ cao (80 máy/host, chipset Intel X99): Sau khi PC reboot, Windows và XiaoWei cần 10–20 phút để hoàn tất USB descriptor enumeration cho đủ 80 cổng USB.
  2. Mạng nội bộ / VPN WireGuard giữa 2 host cần thời gian handshake lại sau khi cả 2 máy cùng reboot.
  3. Mốc reboot đặt quá sát giờ chạy ca (11:35 reboot -> 12:00 chạy ca, chỉ có 25 phút đệm):
     - Tại thời điểm 12:07, daemon ADB trên remote host (`192.168.110.119:5037`) vừa mở cổng và bus USB chưa hoàn toàn ổn định.
     - Runner trên Kibe spawn đồng loạt 25–40 workers kết nối tới port 5037 từ xa qua LAN -> **Concurrency spike** làm sập socket transport ADB -> `protocol fault: connection reset`.
     - Watchdog gom toàn bộ lỗi `connection reset` / `protocol fault` này vào nhãn `"Mất kết nối ADB/USB"`.

## 3. Quy tắc điều phối & Triage (Anti-Panic)
- **CẤM kết luận sập phần cứng / rớt farm:** Khi thấy cả cụm 60–80 máy đồng loạt offline ngay sau mốc reboot, BẮT BUỘC kiểm tra `summary.txt` xem có chữ `protocol fault: connection reset` hay không trước khi báo động hoặc can thiệp tay.
- **Không restart ADB thủ công giữa chừng:** Socket ADB từ xa sẽ tự hồi phục khi tiến trình runner kết thúc. Đến phiên tiếp theo trong ca, hệ thống sẽ tự chạy bình thường.
- **Quy chuẩn Warmup Buffer (Khắc phục triệt để):**
  - Mọi mốc reboot farm BẮT BUỘC phải cách giờ bắt đầu ca tối thiểu **35–45 phút** (thay vì 15–25 phút).
  - Khuyến nghị mốc chuẩn:
    - Ca 1 (06:00): Reboot lúc **05:20** (đệm 40 phút).
    - Ca 2 (12:00): Reboot lúc **11:20** (đệm 40 phút).
    - Ca 3 (18:00): Reboot lúc **17:20** (đệm 40 phút).
  - Khoảng đệm 40 phút đảm bảo:
    - Host khởi động xong và thông mạng WireGuard.
    - XiaoWei nhận diện đủ 100% cổng USB và giải phóng bus.
    - Daemon ADB server nguội máy, sẵn sàng nhận concurrency tải cao từ xa.
