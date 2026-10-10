# Triage Lỗi Cấu Hình Proxy Trong Ca Chạy TikTok Farm

## 1. Tránh Lạc Hướng Điều Tra
- Khi nhận câu hỏi về "Lỗi cấu hình proxy" ngay sau báo cáo ca chạy hoặc watchdog (`feed_session_watchdog`), ngữ cảnh LUÔN LUÔN là Phone Farm (TikTok feed/upload).
- **CẤM TUYỆT ĐỐI**: Không tự tiện probe port LLM / OmniRoute / 9Router (`:20128`, `:20129`) trừ khi user nói rõ "OmniRoute" hoặc "proxy LLM".

## 2. Bản Chất Nhãn "Lỗi cấu hình Proxy" của Watchdog
Báo cáo watchdog gom chung mọi ca dừng ở `vpn_preflight.py` với trạng thái `blocked-proxy-vpn` vào nhãn "Lỗi cấu hình Proxy". Thực tế bao gồm 3 nhóm nguyên nhân riêng biệt:

### Nhóm 1: Rớt Wi-Fi (Wi-Fi not connected)
- Log máy thể hiện: `dumpsys connectivity: Wi-Fi not connected` hoặc `required router proxy is unreachable`.
- Thiết bị mất Wi-Fi nên không thể kết nối tới IP LAN của MikroTik/Singbox (`192.168.110.2`).
- **Cơ chế tự cứu 2 cấp (Stage 1 & Stage 2 Recovery)**:
  * Cấp 1: Radio toggle (`svc wifi disable` -> `svc wifi enable`).
  * Cấp 2: Tự tra cứu SSID/Pass theo số máy từ `PROXYgandienthoai.xlsx` (có in-memory cache), gọi `com.steinwurf.adbjoinwifi`, bấm HOME (`keyevent 3`), rồi probe lại qua `check_android_vpn`.
  * Nếu cả 2 cấp fail: fail-closed bảo vệ nick, cấm nhảy sang SSID ngoài farm.

### Nhóm 2: Lệch dải port MikroTik (Admin Farm M241-M280)
- Thiết bị bị gán port `10041` đến `10080` do script cũ cộng dồn tuyến tính.
- Router MikroTik chỉ mở tối đa 40 port PPPoE (`10001` đến `10040`). Port > 10040 sẽ trả về `Connection Refused`.
- Khắc phục: Chạy `set_proxy_farm_admin_adb.py` để phủ lại dải port chuẩn từ file Excel (`10008`..`10035`).

### Nhóm 3: Rớt kết nối phần cứng / ADB
- Máy báo `device offline`, `device not found`, mất cáp USB. Cần kiểm tra vật lý hoặc restart daemon ADB.
