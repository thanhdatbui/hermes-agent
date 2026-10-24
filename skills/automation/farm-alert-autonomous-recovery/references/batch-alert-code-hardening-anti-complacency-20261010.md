# Kỷ Luật Code Hardening Khi Xử Lý Batch Alert (Chống Bẫy "Chỉ Báo Online Ảo" / "K Fix Đc Lỗi À")

## 1. Bối Cảnh & Tình Huống Sai Lầm Phổ Biến
Khi hệ thống Farm Alert phát chuông cảnh báo lỗi hàng loạt (ví dụ: 45/80 máy thất bại trong batch nuôi/lướt feed):
- **Phản xạ sai lầm của Coordinator:**
  1. Chạy lệnh Canary trích xuất hiện trường trên 1 máy đại diện (`inspect_machine.py M204`).
  2. Thấy máy đại diện đang bật màn hình (`Awake`), pin sạc tốt, các cổng proxy PPPoE/Singbox hiện tại đã `OPEN` (`connect_ex == 0`).
  3. Vội vã kết luận: *"Hiện trường đã bình thường, lỗi do chớp mạng/reboot tạm thời, sẵn sàng resume lại batch."*
  4. **Hậu quả:** Người dùng phản ứng ngay lập tức: *"K fix đc lỗi à"*. Phản xạ chỉ báo online ảo mà không rà soát mã nguồn là biểu hiện của sự chủ quan, thiếu trách nhiệm, vì bản chất runner đã vội vã đánh rớt 45 máy do lỗ hổng timeout/retry thắt quá chặt.

## 2. Quy Tắc Bất Biến: Điều Tra Lỗ Hổng Runner Trước Khi Đề Xuất Resume
Khi máy và cổng proxy tự hồi phục sau sự cố, Coordinator **BẮT BUỘC** phải đặt câu hỏi ngược lại:
*Tại sao code runner lại vội vã đánh rớt hàng loạt thiết bị chỉ vì một đợt nghẽn mạng/socket tạm thời?*

### 2 Lỗ hổng kinh điển trong Batch Runner:
1. **Timeout ADB Probe quá chặt trên Host đông máy:**
   - Khi 80 máy cùng chạy batch song song trên 1 PC qua hub USB, lệnh `adb shell ip addr` hoặc `dumpsys connectivity` bị xếp hàng trong daemon ADB Windows.
   - Nếu code preflight đặt `timeout=6.0s` không có backoff/retry đủ dài, hàng đợi trễ > 6s sẽ kích hoạt `subprocess.TimeoutExpired`. Script bắt chuỗi `adb command timed out` và vội vã đánh rớt thiết bị thành `[DEVICE_OFFLINE]` dù máy vật lý không hề lỏng cáp.
   - **Vá bắt buộc:** Nâng timeout probe retry lên `12.0s - 15.0s`, thêm cơ chế auto-reconnect trước khi fail-closed.
2. **Fast Fail-Closed Socket Probe đơn lẻ không Retry:**
   - Các cổng proxy xoay IP (PPPoE / 4G dongle) có chu kỳ đổi IP kéo dài 1–2 phút hoặc chớp socket 2–3 giây.
   - Nếu hàm `_proxy_server_live` chỉ probe `socket.connect_ex` đúng 1 lần duy nhất trong `1.5s` rồi kết luận đóng cổng, hàng chục máy sẽ bị kill-switch ngắt phiên oan.
   - **Vá bắt buộc:** Thêm retry tối thiểu 3 lần (mỗi lần 1.5s, sleep 0.5s giữa các lần) trước khi đánh rớt thiết bị.

## 3. Quy Trình Khép Kín 4 Bước Khi Xử Lý Alert Diện Rộng
1. **Kiểm tra Lịch Trình & Cronjob Xung Đột:**
   - Kiểm tra `last_run_at` của các cronjob bảo trì hệ thống (như `farm-scheduled-pc-reboot` chạy lúc 04:45).
   - Nếu cronjob bảo trì định kỳ gây xung đột với các ca nuôi/upload, chủ động đề xuất hoặc thực hiện hủy bỏ (`cronjob action='remove'`) theo yêu cầu user.
2. **Canary Verification & Thẩm Định Hiện Trường O(1):**
   - Chạy `inspect_machine.py <N>` (hỗ trợ cả prefix `M<N>` và số thuần).
   - Soi WinRT OCR màn hình: CẤM gửi ảnh màn hình Home/Launcher làm bằng chứng lỗi.
3. **Thực Hiện Code Hardening (T1/L2):**
   - Rà soát `vpn_preflight.py` / `preflight.py` xem timeout/retry có phải là nguyên nhân khiến máy bị ngắt sớm không.
   - Vá ngay O(1) (< 15 dòng diff), chạy unit test focussed (< 30s) đảm bảo xanh 100%.
   - Đồng bộ file đã sửa sang các cụm remote (như Admin PC `192.168.110.119`) qua `scp`.
4. **Closeout Gate Thẩm Định Độc Lập:**
   - Chạy `closeout_gate.py --base HEAD~1 --files <modified_files> --json-output`.
   - Nếu Sol Reviewer reject do thiếu telemetry hoặc test regression: Dùng ngay `sol_repair.py` tạo proposal O(1), bổ sung `_log_vpn_timeout_event` và unit test, đạt điểm >= 85/100 mới hoàn tất.
