# Scheduled Reboot Window Collision & Remote ADB Queue Timeout Triage (2026-10-10)

## Bối Cảnh Sự Cố & Hiện Tượng
- **Thời điểm**: 04:45 sáng Thứ Bảy (10/10/2026).
- **Quy mô batch**: Batch nuôi 80 máy Farm Admin (M201–M280) bị rớt 45/80 máy (56.2% thất bại).
- **Hai cụm lỗi vượt ngưỡng kép**:
  1. `[DEVICE_OFFLINE] device is offline or ADB/USB disconnected for <serial>: adb command timed out ('C:\Program Files (x86)\xiaowei\tools\adb.exe', '-s', '<serial>', 'shell', 'ip', 'addr...')` (10 máy: M204, M209, M211, M222, M223, M227, M231, M234, M277, M279).
  2. `required Android VPN/proxy is unreachable: proxy server port is closed/refused for <serial>; skipping recovery wait to unblock other machines immediately` (17 máy: M241–M248, M250, M253, M254, M256–M260, M271).

## Nguyên Nhân Gốc Rễ (Root Cause)
1. **Xung đột cửa sổ bảo trì định kỳ**: Cronjob `farm-scheduled-pc-reboot` chạy vào 04:45 sáng Thứ 2, 4, 7 để reboot bảo trì PC và làm mới bus USB/Router. Batch chạy đúng lúc hệ thống vừa boot lại.
2. **Nghẽn hàng đợi ADB Daemon trên Windows (Cụm 1)**:
   - Sau khi PC Admin vừa boot, 80 luồng shell đồng loạt gọi `adb.exe` qua daemon Xiaowei (`C:\Program Files (x86)\xiaowei\tools\adb.exe`).
   - Trong `python_runner/core/vpn_preflight.py`, `check_android_vpn` được truyền `timeout=6.0s` cả ở probe đầu và vòng retry sau reconnect.
   - Khi 80 lệnh `ip addr` cùng xếp hàng trên Windows, thời gian xử lý thực tế vượt ngưỡng 6s, kích hoạt `subprocess.TimeoutExpired` -> `adb command timed out`. Code bắt trúng marker mất kết nối và fail-closed giả mạo thành `[DEVICE_OFFLINE]` dù máy vật lý vẫn cắm cáp và sạc pin bình thường.
3. **Cơ chế Fast Fail-Closed khi PPPoE Renegotiation (Cụm 2)**:
   - Toàn bộ 17 máy ánh xạ vào dải cổng MikroTik PPPoE `10021–10027` và `10031` (`192.168.110.2`).
   - Router vừa khởi động lại đang trong quá trình quay số PPPoE (kéo dài 1–2 phút).
   - Hàm `_proxy_server_live` thực hiện probe socket TCP đơn lẻ với `timeout=1.5s` không retry, trả về `False` ngay lập tức để chống lộ IP WAN FPT gốc.

## Kỷ Luật Phản Xạ & Điều Phối (Bài Học "K fix đc lỗi à")
- **Không dừng lại ở việc giải thích hiện trường**: Khi thiết bị và cổng proxy đã tự hồi sinh sau đợt reboot, nếu Coordinator chỉ kết luận "hiện tại đã online, sẵn sàng resume" mà không rà soát điểm yếu trong code runner, User sẽ đánh giá là chưa giải quyết triệt để lỗi ("K fix đc lỗi à").
- **Hành động kép bắt buộc**:
  1. **Điều tra mã nguồn**: Phát hiện timeout quá ngắn (`6.0s`) hoặc thiếu cơ chế retry khi đối mặt với tải nặng 80 máy trên môi trường USB host Windows.
  2. **Vá O(1) mã nguồn**:
     - Nâng timeout probe retry trong `vpn_preflight.py` lên `12.0s` để buffer hàng đợi daemon Xiaowei.
     - Đồng bộ bản vá sang cả Kibe Controller và Admin PC (`192.168.110.119`).
     - Chuẩn hóa parser `inspect_machine.py` để chấp nhận tham số có tiền tố `M<N>` theo đúng định dạng Farm Alert.

## Checklist Đối Soát Nhanh Khi Gặp Lỗi Tương Tự
1. Kiểm tra lịch bảo trì hệ thống/cronjob: Xem `last_run_at` của `farm-scheduled-pc-reboot` hoặc các watchdog restart network.
2. Trích xuất hiện trường O(1): Dùng `python D:/Taadaa/tools/inspect_machine.py <N>` để xác minh trạng thái pin, màn hình, focus thực tế.
3. Probe socket TCP trực tiếp từ host: Kiểm tra `connect_ex` tới IP LAN `192.168.110.2:<PORT>` thay vì kết luận proxy chết vĩnh viễn.
