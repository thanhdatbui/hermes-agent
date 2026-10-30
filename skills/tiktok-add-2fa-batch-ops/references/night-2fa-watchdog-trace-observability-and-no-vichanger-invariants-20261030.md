# Night 2FA Watchdog Trace Observability & No-ViChanger Invariants (30/10/2026)

## 1. Cấm Tuyệt Đối Viện Dẫn Logic Cũ (Invariants)
- **ViChanger đã bị loại bỏ hoàn toàn khỏi Farm:** Cấm tuyệt đối Coordinator viện dẫn ViChanger, lỗi VPN ViChanger, hay profile ViChanger khi giải trình sự cố.
- **Đọc OTP Hotmail 100% trên PC (Graph API & GPM):** Mọi mã OTP Hotmail đều được trích xuất qua Microsoft Graph API Token từ `gmail_clean_v2.xlsx` hoặc GPM Profile trên PC. **Tuyệt đối không có chuyện mở app Outlook trên thiết bị Android S7** để đọc mail.
- **Tính tuần tự của Night Chain:** Watchdog ban đêm (`cron_night_tiktok_2fa_watchdog.py`) kích hoạt Phase 1 (Reg Gmail) trước, đợi hoàn tất mới kích hoạt Phase 2 (2FA TikTok). Hai phase này chạy tuần tự, không bao giờ chạy song song gây xung đột Device Lock giữa các máy.

---

## 2. Tiêu Chuẩn Quan Sát Bắt Buộc (Watchdog Observability Contract)
- **Vấn đề đã khắc phục:** Runner in bảng kết quả chi tiết từng máy ra stdout (`machine | source_row | username | status | reason`), nhưng watchdog cũ chỉ bóc 4 số đếm (`TOTAL`, `SUCCESS`, `FAILED`, `SKIP`) rồi vứt bỏ stdout. Khi có lỗi, báo cáo chỉ hiện con số chung chung khiến Coordinator không có bằng chứng thực tế và dễ suy đoán mò.
- **Quy chuẩn mới trong `cron_night_tiktok_2fa_watchdog.py`:**
  1. **Ghi Trace ra đĩa:** Toàn bộ stdout/stderr của cả hai cụm Kibe và Admin bắt buộc phải được lưu nối tiếp vào file:
     `D:/Taadaa/reports/night_2fa_trace_{today_str}.log`
  2. **Bóc tách lỗi chi tiết (`parse_2fa_breakdown_from_text`):** Tự động phân tích các mã lỗi thật (vd `POST_SUCCESS_VERIFICATION_FAILED`, `DEVICE_NOT_CONNECTED`, `ACCOUNT_NOT_IN_SWITCHER`) và gom nhóm theo số lượng.
  3. **Đính kèm Trace trong báo cáo Telegram:**
     * Bổ sung dòng: `• Lỗi chi tiết: <tổng> (<mã_lỗi_1: N>, <mã_lỗi_2: N>...)`
     * Bổ sung dòng: `• Trace: D:/Taadaa/reports/night_2fa_trace_{today_str}.log`
     * Lưu `failure_breakdown` và `trace_path` vào state JSON (`night_tiktok_2fa_state.json`) để phục vụ đối soát O(1).
