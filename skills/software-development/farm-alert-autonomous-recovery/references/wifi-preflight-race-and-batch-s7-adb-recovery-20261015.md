# Wi-Fi Preflight Race vs Watchdog Healer & Batch S7 ADB Recovery (2026-10-15)

## 1. Bối cảnh & Hiện tượng
Khi kết thúc phiên nuôi acc TikTok (ví dụ Ca 1 / Ca 2):
1. **Máy rớt Wi-Fi (ví dụ M7)**: Báo cáo `final_status: blocked-proxy-vpn` kèm lý do `required router proxy is unreachable ... dumpsys connectivity: Wi-Fi not connected`. User thắc mắc: *"M7 sao rớt wifi có script auto reconnect rồi mà?"*
2. **Loạt máy rớt ADB / USB (ví dụ M10, M30, M38, M56, M59, M74)**: Báo `adb command timed out: ('adb.exe', '-s', ..., 'shell', 'settings', 'get', 'global', 'http_proxy')`.

## 2. Nguyên nhân gốc rễ
- **Race condition giữa Runner Preflight & Periodic Healer**:
  - `tiktok_runner` / `feed_swipe_smoke` kiểm tra tính sẵn sàng của mạng (`dumpsys connectivity` & proxy) ngay tại thời điểm bắt đầu phiên của máy. Nếu phát hiện mất kết nối Wi-Fi, runner **bắt buộc fail-closed lập tức** để chống rò rỉ IP trực tiếp ra ngoài.
  - Cronjob `farm-wifi-auto-healer` chạy theo chu kỳ 5 phút/lần. Nếu máy bị chập chờn rớt sóng đúng thời điểm runner chạy, runner sẽ ghi nhận thất bại của phiên đó trước khi watchdog kịp kích hoạt ở tick kế tiếp.
- **Nghẽn tải ADB Daemon khi khởi động đồng loạt 80 máy**:
  - Việc 80 tiến trình con đồng thời gọi lệnh adb shell query `settings get global http_proxy` làm nghẽn bus I/O và daemon ADB của Tiểu Vi (xiaowei adb), dẫn đến timeout giả dù thiết bị phần cứng vẫn gắn cáp.

## 3. Quy trình xử lý chủ động (Coordinator Active Triage)
Tuyệt đối không trả lời bị động kiểu "chờ cron tự xử lý" hay chỉ liệt kê lỗi. Khi user yêu cầu *"Fix mấy máy còn lại luôn đi"*, Coordinator kích hoạt ngay các công cụ cứu hộ chuẩn:

### A. Cứu hộ máy rớt Wi-Fi đơn lẻ
1. **Chạy cứu hộ phân tầng ngay**:
   ```bash
   python D:/Taadaa/tools/recover_stuck_s7.py --machine <N>
   ```
   - Cấp 1 (`recovered_soft`): Đưa máy về HOME, wake screen, giải phóng ứng dụng treo.
   - Nếu radio Wi-Fi chưa bật: toggle `svc wifi disable` -> `svc wifi enable`.
2. **Nếu dính AP rejection**: Ép re-join qua `adb-join-wifi` theo đúng quy hoạch AP (M1-40: `kibe 1`, M41-80: `kibe 2`, M201-240: `admin 1`, M241-280: `admin 2`).

### B. Cứu hộ loạt máy dính ADB Timeout / Kẹt app
Chạy batch cứu hộ đa luồng với giới hạn reboot an toàn (cooldown 300s):
```bash
python D:/Taadaa/tools/batch_recover_s7.py --cluster <kibe|admin> --machines <danh_sách_máy> --max-workers 6 --max-reboots 1
```
- Công cụ tự động:
  - Khôi phục soft qua HOME + force-stop.
  - Tự động kiểm tra `reboot_cooldown_<serial>.json` để không reboot liên tục gây hại pin/phần cứng.
  - L3 Reconnect cho các thiết bị chập chờn kết nối transport.
