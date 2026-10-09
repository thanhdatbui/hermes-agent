# Dual-Cluster Batch Alert: [DEVICE_OFFLINE] ADB Timeout & PPPoE Port Closed Triage (2026-10-10)

## 1. Hiện Tượng Thực Tế
Trong ca nuôi lướt feed batch quy mô 80 máy trên Farm Admin (M201–M280), hệ thống ghi nhận tỷ lệ lỗi vượt ngưỡng kép (56.2% thất bại: 45/80 máy):
1. **Cụm 1 (10 máy - 12.5% batch):** `UploadScriptError:UploadHook: [DEVICE_OFFLINE] device is offline or ADB/USB disconnected for <serial>: device offline or ADB/USB disconnected: adb command timed out: ('C:\\Program Files (x86)\\xiaowei\\tools\\adb.exe', '-s', '<serial>', 'shell', 'ip', 'addr...`
   - Danh sách: M204, M209, M211, M222, M223, M227, M231, M234, M277, M279.
2. **Cụm 2 (17 máy - 21.2% batch):** `proxy-vpn:required Android VPN/proxy is unreachable: proxy server port is closed/refused for <serial>; skipping recovery wait to unblock other machines immediately`
   - Danh sách: M241-M248, M250, M253, M254, M256-M260, M271.

## 2. Bản Chất Sự Cố Kép

### Cụm 1: Nghẽn Daemon Socket Transport trên Host Admin
- **Hiện tượng:** Hook kiểm tra `is_connection_lost` bắt chuỗi `adb command timed out` và phân loại đúng thành `[DEVICE_OFFLINE]`.
- **Cơ chế:** Toàn bộ 80 máy Farm Admin cắm qua 4 Box hub USB vào một PC duy nhất (`192.168.110.119`). Khi batch khởi chạy đồng loạt 80 tiến trình shell (`ip addr`, `dumpsys`), binary ADB (`C:\Program Files (x86)\xiaowei\tools\adb.exe`) bị bão hòa buffer I/O socket transport. Lệnh shell bị nghẽn quá thời gian timeout (5-10s).
- **Thực tế vật lý:** Cáp USB và nguồn điện thoại không bị rớt. Sau khi batch kết thúc, daemon ADB tự giải phóng kết nối, 100% thiết bị (M204, M209...) tự hồi phục về trạng thái `device`, pin sạc tốt, màn hình Awake ở LauncherActivity.

### Cụm 2: PPPoE Renegotiation Fast Fail-Closed Chống Direct IP Leak
- **Hiện tượng:** Tất cả 17 máy trong cụm này đều ánh xạ vào các cổng MikroTik PPPoE `10021–10027` và `10031` trên `mirotik1.taadaa.click` (`192.168.110.2`).
- **Cơ chế:** Các đường truyền PPPoE trên router xoay IP định kỳ lúc rạng sáng (kéo dài 1–2 phút). Trong cửa sổ này, socket TCP proxy bị đóng/refused (`connect_ex != 0`). Hàm `_proxy_server_live` fast probe phát hiện cổng đóng và lập tức kích hoạt fail-closed trong <=1.5s để bảo vệ tài khoản không lướt feed bằng Direct IP FPT.
- **Thực tế:** Sau khi PPPoE renegotiation hoàn tất, toàn bộ các cổng 10021-10027 và 10031 tự động OPEN trở lại (`connect_ex == 0`).

## 3. Quy Trình Phục Hồi & Triage O(1)

1. **Khóa batch an toàn:** Cấm can thiệp vật lý đồng loạt hoặc reboot toàn dàn khi chưa xác minh canary.
2. **Canary Test O(1) trên 1 máy đại diện:**
   - Chạy lệnh trích xuất nhanh: `python D:/Taadaa/tools/inspect_machine.py M204`.
   - Lưu ý tiền tố `M`: Công cụ `inspect_machine.py` đã được chuẩn hóa để strip tiền tố `M`/`m` trước khi kiểm tra số máy (`sys.argv[1].lstrip("Mm")`), tránh rơi nhầm về lệnh liệt kê toàn fleet.
3. **Kiểm tra socket proxy từ LAN:**
   - Probe trực tiếp bằng Python `socket.connect_ex` từ host tới các cổng MikroTik LAN `192.168.110.2:<port>`.
   - Nếu `connect_ex == 0` và thiết bị ở trạng thái `LauncherActivity`, fleet đã sẵn sàng mở lại batch.
4. **Kỷ luật bằng chứng hình ảnh (Gate 6):**
   - Chụp ảnh màn hình qua ADB và kiểm tra bằng WinRT OCR.
   - Nếu màn hình là Home/Launcher, **CẤM TUYỆT ĐỐI** gửi ảnh Home/Launcher làm bằng chứng sau teardown/lỗi.
