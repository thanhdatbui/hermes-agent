# Wi-Fi Toggle Recovery, Dual-Cluster Parity & TikTok Following Tab False Network Diagnosis (2026-09-24)

## 1. Hiện tượng & Bối cảnh Sự cố (Incident 2026-09-24 Ca Row 8)
- Farm Alert ghi nhận tỷ lệ lỗi toàn farm 23.1% (37/160 máy), trong đó có:
  - Cụm Admin: 5 máy bị chặn `blocked-proxy-vpn` do lỗi `dumpsys connectivity: Wi-Fi not connected` (`M268, M275, M278, M279, M280`).
  - Cụm Kibe: 3 máy bị `manual-needed:network` do `network/error/retry marker detected` (`M4, M32, M77`).
- Người vận hành thắc mắc: *"ủa t có thiết kế cơ chế rớt wifi bật lại r mà, hay này là do bên proxy k phải wifi"*.

## 2. Nguyên nhân Gốc rễ (Root Cause Analysis)

### A. Vì sao không phải lỗi Proxy?
- Kiểm tra trực tiếp các cổng proxy MikroTik được map cho các máy Admin (`10030, 10033, 10034, 10035` trên `192.168.110.2` và domain `mirotik1.taadaa.click`):
  `socket.connect_ex` trả về `0` (OPEN, phản hồi ngay lập tức trong < 10ms).
- Chuỗi thông báo `required router proxy is unreachable for <serial> (kill switch active or no connection)` là wrapper bảo vệ an toàn của `vpn_preflight.py` khi phát hiện điều kiện mạng trên thiết bị không đạt yêu cầu. Nguyên nhân thực tế nằm ở vế sau dấu hai chấm: `dumpsys connectivity: Wi-Fi not connected`.

### B. Vì sao cơ chế tự bật lại Wi-Fi trong Runner không cứu được?
- Trong `python_runner/core/vpn_preflight.py`:
  ```python
  wifi_res = adb.shell(["svc", "wifi", "enable"], timeout=5, check=False)
  ```
- **Hạn chế kỹ thuật của Android (đặc biệt Samsung S7 Android 7/8)**:
  Khi máy bị ngắt kết nối với AP (do sóng Wi-Fi suy hao, AP đá kết nối, hoặc kẹt DHCP), switch Wi-Fi trong hệ điều hành Android thực tế **vẫn đang ở trạng thái BẬT (ON)**. Lệnh `svc wifi enable` không làm mới driver hay kích hoạt chu kỳ quét mạng mới.
- **Giải pháp**:
  Bắt buộc phải thực hiện cycle:
  ```bash
  svc wifi disable && sleep 1 && svc wifi enable
  ```
  Sau đó sleep 3–4 giây để Android quét SSID và nhận lại IP từ router/DHCP.

### C. Vì sao Watchdog Nền (`farm_wifi_auto_healer.py`) bỏ sót Cụm Admin & Nghẽn Quét Tuần Tự?
- Watchdog cronjob `farm-wifi-auto-healer` chạy mỗi 5 phút có code toggle rất chuẩn:
  `svc wifi disable && sleep 1 && svc wifi enable`.
- **Nhược điểm kiến trúc 1 (Thiếu Dual-Cluster Parity)**: File này trước đây chỉ gọi `adb devices` cục bộ và chỉ đọc file `kibe\PROXYgandienthoai.xlsx`.
  Nó hoàn toàn không kết nối tới Remote ADB của Admin (`-H 192.168.110.119 -P 5037`) và không đọc `admin\PROXYgandienthoai.xlsx`, vi phạm nguyên tắc **Dual-Cluster Parity** (Kibe có gì Admin phải có nấy). Khi máy Admin rớt Wi-Fi, watchdog không quét tới.
- **Nhược điểm kiến trúc 2 (Nghẽn quét tuần tự trên 160 máy)**:
  Quét tuần tự 160 máy (mỗi máy probe ADB 3–4s, toggle 8s) làm watchdog ngốn tới 500–600s, dễ bị timeout hoặc kẹt lịch cron.
  **Giải pháp bắt buộc**: Sử dụng `concurrent.futures.ThreadPoolExecutor(max_workers=20)` để dispatch đồng thời các probe ADB. Thời gian quét toàn bộ ~160 máy giảm từ >500s xuống chỉ còn **~6.3 giây**, hoàn thành êm đềm trong 1 tick cron.

### D. Hiện tượng Báo Giả Rớt Mạng Trên Tab "Đã follow" (Following Tab)
- Trên Farm Kibe, máy `M4, M32, M77` bị dừng với lỗi `network/error/retry marker detected`:
  - Kiểm tra `ui.xml` và `screen.png`: Thiết bị có sóng Wi-Fi 3 vạch đầy đủ (`Tín hiệu Wi-Fi ba vạch`).
  - Máy đang ở tab `Đã follow` (Following) tại bước `switch_following`. Do tài khoản nuôi chưa follow ai (danh sách follow trống), TikTok hiển thị màn hình rỗng: *"Đã xảy ra lỗi. Vui lòng thử lại."* kèm nút *"Thử lại"*.
  - Hàm `classify_screen` quét thấy text này nên phân loại nhầm thành `manual-needed:network`.
  - Thực tế không có sự cố mạng. Ở ca kế tiếp, cả 3 máy đều chạy lại và đạt kết quả `success` 100%.

## 3. Checklist Khắc phục & Điều phối (Actionable SOP)
1. **Kiểm tra phân định Wi-Fi vs Proxy**:
   - Chạy O(1): `inspect_machine.py <N>` để xem focus và trạng thái ADB.
   - Chạy socket test port proxy từ host: `python -c "import socket; s=socket.socket(); s.settimeout(2); print(s.connect_ex(('<host>', <port>)))"`.
2. **Khôi phục Wi-Fi thủ công hoặc tự động**:
   - Không chỉ gõ `svc wifi enable`.
   - Luôn toggle: `adb [-H IP -P 5037] -s <serial> shell "svc wifi disable && sleep 1 && svc wifi enable"`.
3. **Đồng bộ Watchdog**:
   - Khi chỉnh sửa bất kỳ watchdog phần cứng/mạng nào, bắt buộc hỗ trợ cả 2 cluster: Kibe (Local) và Admin (Remote `192.168.110.119:5037`).
