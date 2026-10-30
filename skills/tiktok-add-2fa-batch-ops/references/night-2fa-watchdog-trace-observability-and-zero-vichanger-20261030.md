# Night 2FA Watchdog Trace Observability & Zero ViChanger Policy (2026-10-30)

Đúc kết từ sự cố báo cáo 2FA ban đêm (`night-tiktok-2fa-watchdog`), phản hồi chấn chỉnh của Operator và bản vá toàn diện kiến trúc 2FA hai cụm.

---

## 1. Bản Chất Kiến Trúc Farm: Zero ViChanger & Không Dùng Outlook Trên S7
- **Bỏ hoàn toàn ViChanger:**
  * Toàn bộ 80 máy Kibe chạy proxy tĩnh qua Wi-Fi Aruba kết hợp Container Sing-box trên router MikroTik (`192.168.110.2:20001..20080`), gán qua `global http_proxy`.
  * Dàn Admin (201..280) chạy qua cổng LAN MikroTik PPPoE.
  * Thiết bị điện thoại hoàn toàn KHÔNG có app ViChanger, không tạo VPN card `tun0`, không dùng watcher cấp lại IP.
  * Mọi tàn dư code như `VICHANGER_SERIAL_HEADERS` hay tiền tố `VICHANGER_` trong runner đều là rác cũ và đã bị loại bỏ triệt để.
- **Đọc Hotmail OTP 100% Trên PC (Microsoft Graph API & GPM):**
  * Mã OTP Hotmail/Outlook được lấy trực tiếp trên PC qua Microsoft Graph API Token lưu trong `gmail_clean_v2.xlsx` (Cột 9 Token, Cột 10 Client ID) hoặc GPM Profile.
  * Tuyệt đối CẤM gọi `read_tiktok_otp_from_outlook_app`, cấm mở package `com.microsoft.office.outlook` trên điện thoại S7 vì làm lệch focus màn hình TikTok và vi phạm kiến trúc vận hành.

---

## 2. Kỷ Luật Chống Suy Diễn & Đoán Mò (Anti-Hallucination Invariant)
- **Cạm bẫy:** Khi nhận báo cáo forward có máy lỗi (ví dụ: `Lỗi 36`), Coordinator không có log trace nhưng tự ý bịa ra nguyên nhân ("timeout account switcher", "trùng lock với ca khác").
- **Quy tắc bất biến:**
  * Nếu không có log trace trên đĩa, Coordinator BẮT BUỘC phải thừa nhận chưa có trace do watchdog nuốt output, tuyệt đối không được tự suy diễn.
  * Nhiệm vụ lúc này là vá ngay tính năng ghi log trace của script watchdog, không giải thích quanh co.
  * Cấm lạm dụng Persistent Memory để ghi nhớ quy tắc thừa thãi khi User yêu cầu dọn dẹp; phải dọn sạch từ tầng code và skills.

---

## 3. Khế Ước Ghi Vết & Bóc Tách Lỗi Watchdog (Watchdog Observability Contract)
- **Vấn đề cũ:** `cron_night_tiktok_2fa_watchdog.py` chỉ dùng regex bóc 4 con số (`TOTAL`, `SUCCESS`, `FAILED`, `SKIP`) từ stdout của runner rồi vứt bỏ toàn bộ output thô, khiến khi có máy lỗi thì không thể tra cứu.
- **Quy chuẩn mới:**
  1. **Lưu vết thô đầy đủ:** Toàn bộ stdout/stderr của cả hai cụm Kibe và Admin bắt buộc phải được ghi ra file trace:
     `D:/Taadaa/reports/night_2fa_trace_{today_str}.log`.
  2. **Bóc tách lỗi chi tiết (`parse_2fa_breakdown_from_text`):** Tự động phân tích bảng kết quả runner (`machine | row | user | status | reason`), đếm số lượng theo từng mã lỗi cụ thể (ví dụ: `POST_SUCCESS_VERIFICATION_FAILED: 20`, `DEVICE_NOT_CONNECTED: 5`).
  3. **Báo cáo Telegram minh bạch:** Báo cáo gửi nhóm Telegram bắt buộc kèm:
     - Dòng thống kê lỗi: `• Lỗi chi tiết: <total> (<mã_lỗi_1: số_lượng>, ...)`
     - Dòng đường dẫn trace: `• Trace: D:/Taadaa/reports/night_2fa_trace_{date}.log`
  4. **State JSON phong phú:** Lưu `failure_breakdown` và `trace_path` vào `night_tiktok_2fa_state.json` để các công cụ tự động hóa và Coordinator phiên sau tra cứu tức thì O(1).
