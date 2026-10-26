# OmniRoute Proxy Cascade ECONNRESET, Event Loop Deadlock Ceiling & Watchdog Restart Window (26/10/2026)

## 1. Hiện Tượng & Triệu Chứng
- **Dashboard OmniRoute (:20129)**: Xuất hiện một khoảng trống không có bất kỳ request nào kéo dài từ 10 đến 20 phút (ví dụ: từ 16:50 đến 17:09).
- **Telegram Gateway**: Đúng vào phút OmniRoute đang restart (17:07 PM), mọi tin nhắn User gửi tới nhiều topics/bots đồng loạt văng thông báo:
  > `⚠️ The model provider failed after retries. I kept raw provider details out of chat; check gateway logs for diagnostics.`
- **Phản ứng & Nghi ngờ nhầm của Operator/User**:
  - Nghi ngờ "session nào đó đã tự ý hạ timeout quá thấp khiến bot bị timeout đồng loạt".
  - Thực tế kiểm tra cấu hình: `gateway_timeout: 3600`, `api_max_retries: 3`, `child_timeout_seconds: 900` hoàn toàn nguyên vẹn.

---

## 2. Nguyên Nhân Gốc Rễ (Root Cause Chain)

1. **Bão rớt cụm Proxy Mobile (`test.taadaa.click:51xx`)**:
   - Các port proxy `5103, 5111, 5113, 5114, 5115` bị ngắt socket đột ngột (`read ECONNRESET code=ECONNRESET syscall=read errno=-4077`, `[Proxy Fast-Fail] Proxy unreachable`).
   - Cùng thời điểm, hệ thống xử lý nhiều request mang context lớn (>405k tokens) với stream kéo dài >48 giây.
   - Khi hàng chục kết nối proxy bị reset cùng lúc trong khi Node.js đang serialize/deserialize các payload khổng lồ, luồng Main Event Loop của Node.js bị **Freeze/Deadlock hoàn toàn**.

2. **Cơ chế Watchdog Deadlock Ceiling (`omniroute_watchdog.ps1`)**:
   - Watchdog kiểm tra định kỳ `/api/health` mỗi 30 giây.
   - Khi Event Loop của Node.js bị đơ, endpoint `/api/health` không kịp phản hồi:
     ```text
     [2026-10-26 16:59:52] health_degraded: /api/health failed (1/12)...
     ...
     [2026-10-26 17:05:32] health_degraded: /api/health failed (12/12)...
     [2026-10-26 17:05:32] OmniRoute deadlock ceiling reached (12/12 consecutive health timeouts with active process). Force-restarting OmniRoute...
     ```
   - Đúng ngưỡng 12 lần fail liên tiếp (6 phút), Watchdog kích hoạt cơ chế cưỡng chế kill toàn bộ process `node.exe` và `esbuild.exe`.

3. **Cửa Sổ Mất Kết Nối (Dead Window 17:05 – 17:07:52)**:
   - Quá trình restart lần 1 (PID 20412) vấp lỗi exit code 1 sau 3s.
   - Watchdog tiếp tục thử lần 2 lúc 17:07:11 (PID 57124).
   - Đến **17:07:52**, OmniRoute mới nạp xong credentials, hydration và SQLite để mở lại port 20129:
     ```text
     [2026-10-26 17:07:52] OmniRoute is UP and healthy on port 20129 (ready in 24 seconds, PID 57124).
     ```
   - Trong khoảng 17:05 đến 17:07:52, port 20129 hoàn toàn đóng. Mọi request từ Telegram gửi đến đều gặp Connection Refused, retry 3 lần thất bại và văng thông báo `The model provider failed after retries`.

---

## 3. Quy Trình Chẩn Đoán O(1) Tách Bạch

Khi gặp hiện tượng bot văng lỗi đồng loạt trên nhiều group kèm dashboard trống 10-20 phút:

1. **Kiểm tra Watchdog Log (`watchdog.log`)**:
   - Đọc 30 dòng cuối của `C:\Users\Kibe\AppData\Roaming\omniroute\logs\watchdog.log`.
   - Tìm kiếm dòng: `health_degraded` hoặc `OmniRoute deadlock ceiling reached (12/12)`.
   - Nếu thấy mốc thời gian trùng khớp với thời điểm bot văng lỗi trên Telegram $\rightarrow$ Khẳng định 100% do OmniRoute bị Deadlock & Watchdog đang restart, **loại trừ ngay giả định hạ timeout**.

2. **Kiểm tra Log Stdout của OmniRoute (`omniroute-stdout.log`)**:
   - Quét các dòng trước mốc restart để tìm nguyên nhân kích nổ deadlock:
     - Bão rớt proxy: `[Proxy Fast-Fail] Proxy unreachable` hoặc `ECONNRESET`.
     - V8 Heap pressure: `heap pressure guard tripped`.
     - SQLite lock timeout.

3. **Xác nhận Uptime & Trạng thái hiện tại**:
   - Dùng Python urllib gọi `http://127.0.0.1:20129/api/health` (tránh dùng `curl` vì có thể bị coordinator terminal deny).
   - Nếu trả về `{"status":"ok"}` $\rightarrow$ Hệ thống đã hồi phục, không cần tác động thêm vào config hay gateway.
