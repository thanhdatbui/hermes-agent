# Chẩn đoán Hiện tượng Mù Request trên OmniRoute & Chuỗi Zero-Token (TI: 0 | TO: 0)

## 1. Triệu chứng Hiện trường (Dashboard Forensics)
Khi quan sát giao diện Web OmniRoute (ví dụ `http://192.168.110.123:20129`):
* **Khoảng mù (Blind Window):** Đồng hồ client/điện thoại đã trôi qua 2–5+ phút nhưng bảng log không có thêm bất kỳ request mới nào từ Hermes Gateway.
* **Vệt Zero-Token (`TI: 0 | TO: 0`):** Ngay trước khoảng mù, xuất hiện một chuỗi request liên tiếp trong vài giây với Tokens Input = 0, Tokens Output = 0, TPS = `-`.
* **Người dùng Telegram:** Thấy tin nhắn gửi đi đã hiện 2 dấu tick `✓✓` nhưng bot im lặng hoàn toàn, tạo cảm giác bot bị treo hoặc OmniRoute bị sập.

---

## 2. Bản chất Kỹ thuật & Bằng chứng Đối soát

### A. Tại sao OmniRoute hoàn toàn không có request?
* **Khẳng định tiên quyết:** Nếu OmniRoute không có log, **Hermes Gateway chưa hề gửi request nào sang**. Đây 100% không phải do OmniRoute bị treo hay đơ tiến trình.
* **Nguyên nhân cốt lõi ở Tầng Long-Polling (`getUpdates`):**
  1. Kết nối TCP giữa Gateway và máy chủ Telegram API Singapore bị ngắt ngầm (silent TCP drop bởi ISP DPI hoặc SOCKS5 proxy jitter) mà không có cờ `FIN`/`RST`.
  2. Phía Hermes Gateway rơi vào trạng thái **Half-Open Socket (zombie socket)**, tiếp tục chờ phản hồi từ Telegram cho đến khi chạm trần `ReadTimeout` (30s–60s) hoặc Heartbeat probe timeout liên tiếp 3 lần ($30\text{s} \times 3 = 90\text{s}$).
  3. Tin nhắn người dùng nằm chờ trên cụm máy chủ Telegram; Gateway ở local chưa kéo được update về nên không kích hoạt turn mới và không có bất kỳ request nào được sinh ra để bắn lên OmniRoute.

### B. Vệt `TI: 0 | TO: 0` là gì?
* Các request có `Tokens Input = 0` và `Tokens Output = 0` là những connection bị ngắt kết nối ngay tại tầng handshake/đầu vào:
  * Model pool trên OmniRoute trả về HTTP 429 (Rate Limit / Quota Exceeded) hoặc 503 (No healthy upstream provider).
  * Socket streaming bị abort ngay lập tức khi client hoặc proxy reset kết nối.
  * Hermes Client khi gặp lỗi này sẽ rơi vào chuỗi retry nhanh (Fast-Retry / Backoff), tạo thành chùm 4–5 dòng request 0 token cách nhau 2–4 giây trước khi kiệt sức hoặc fallback thành công.

### C. Độ trễ Tool Execution trong Coordinator Turn
* Nếu ở turn trước đó, Coordinator đang bận thực thi một lệnh script nặng, wait subprocess, hoặc chuỗi tool call tuần tự:
* Trong suốt thời gian tool đang chạy, LLM không được gọi. Bảng log OmniRoute sẽ đứng im tương ứng với thời gian tool thực thi.

---

## 3. Quy chuẩn Khắc phục & Điều phối

1. **Khắc phục triệt để Tầng Long-Polling:**
   * Di chuyển sang Webhook qua Cloudflare Tunnel (`cloudflared` + domain riêng) để Telegram chủ động Push tin nhắn về local qua HTTP POST (< 50ms), loại bỏ hoàn toàn bẫy Half-Open Socket của Long-Polling.
   * Nếu vẫn dùng Polling: Siết trần `HERMES_TELEGRAM_HTTP_READ_TIMEOUT=30.0` và `HERMES_TELEGRAM_HEARTBEAT_INTERVAL=30` để watchdog phát hiện và giật đứt socket chết trong vòng <= 45s.

2. **Khắc phục chùm lỗi `TI: 0 | TO: 0`:**
   * Kiểm tra tab `Error` trên OmniRoute để đối soát chính xác mã lỗi (429 hay 503).
   * Đảm bảo pool model có cơ chế fallback nội bộ lành mạnh, tránh để Hermes retry dồn dập vào upstream provider đã cạn quota.
