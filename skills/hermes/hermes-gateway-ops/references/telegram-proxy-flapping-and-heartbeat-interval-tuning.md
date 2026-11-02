# Telegram Proxy Flapping & Heartbeat Interval Tuning (2026-11-03)

## 1. Triệu chứng Sự cố (Incident Symptoms)
* OmniRoute Dashboard / SQLite `call_logs` ghi nhận các khoảng mù 6–13 phút hoàn toàn không có request nào từ Telegram.
* Trên Telegram client, tin nhắn gửi đi hiện 2 dấu tick `✓✓` nhưng bot im lặng (không typing, không phản hồi).
* Sau 6–13 phút, kết nối hồi phục và toàn bộ tin nhắn bị nghẽn đồng loạt ùa về dồn toa (burst).

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Flapping giữa Primary (WARP) và Fallback (LAN Proxy):**
   * WARP desktop daemon (`127.0.0.1:40000`) thường xuyên bị rớt gói hoặc silent TCP stall với máy chủ Telegram Singapore.
   * `TelegramMultiISPTransport` phát hiện lỗi chuyển sang Fallback (Viettel LAN `:10001`).
   * Tuy nhiên, background probe (`_probe_primary_recovery`) chỉ cần 2 lần thành công (sau 60s) là vội vàng trả về Primary (WARP). Khi vừa về Primary, WARP lại nghẽn tiếp, tạo chu kỳ flapping liên tục khiến kết nối `getUpdates` bị gián đoạn.
2. **Heartbeat Interval quá dài (`HERMES_TELEGRAM_HEARTBEAT_INTERVAL=180`):**
   * Khoảng cách giữa các lần thăm dò `get_me()` là 180s (3 phút).
   * Khi gặp silent TCP stall, watchdog mất từ 3 đến 6 phút (sau 2-3 lần probe thất bại) mới giật đứt socket để tái kết nối.

## 3. Quy chuẩn Khắc phục & Cấu hình Bền vững
1. **Ưu tiên tuyến LAN vật lý làm Primary:**
   * Trong `.env`, gán `TELEGRAM_PROXY=http://192.168.110.2:10001` (Viettel LAN proxy ổn định, không rớt gói ngầm).
   * Gán `TELEGRAM_FALLBACK_PROXY=socks5://127.0.0.1:40000` làm tuyến phụ khi LAN gặp sự cố.
2. **Khóa cứng Heartbeat Interval 30s:**
   * Ghi rõ `HERMES_TELEGRAM_HEARTBEAT_INTERVAL=30` trong `.env`.
   * Đảm bảo watchdog phát hiện socket chết và force-reconnect trong vòng 30–45s thay vì ngâm 6–10 phút.
3. **Kỷ luật Điều phối Tool-Use Enforcement:**
   * Khi đã phân tích rõ nguyên nhân kỹ thuật và có quyền xử lý hạ tầng O(1), CẤM dùng câu từ hứa hẹn tương lai ("để em triển khai...") mà không kích hoạt tool. Phải chủ động cập nhật config/code và kiểm chứng test ngay trong turn.
