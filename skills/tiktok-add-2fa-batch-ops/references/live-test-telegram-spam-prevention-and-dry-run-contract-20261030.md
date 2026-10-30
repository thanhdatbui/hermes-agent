# Kỷ Luật Nghiệm Thu Watchdog & Chống Bão Spam Báo Cáo Telegram (30/10/2026)

## 1. Bản Chất Sự Cố
- **Hiện tượng:** Nhóm Telegram nghiệp vụ `Tiktok add 2fa` (`-5468653590`) bị dội 3 bản tin liên tiếp lúc 07:54, 07:59 và 08:10 với nội dung:
  ```text
  ⏰ [FARM REPORT][TOÀN FARM] BÁO CÁO 2FA TIKTOK CA SÁNG:
  • Farm Kibe (Máy 1-80): Hoàn tất 0 | Bỏ qua 0 | Lỗi 0
  • Farm Admin (Máy 201-280): Hoàn tất 0 | Bỏ qua 0 | Lỗi 0
  • Lỗi runner: mã thoát 5 (kẹt Workbook lock hoặc OneDrive chưa hydrate)
  ```
- **Nguyên nhân gốc rễ (Root Cause):**
  * Không phải do scheduler cronjob kích hoạt (vì khung giờ 05:05 - 09:30 bị chặn cứng bởi `is_safe_rolling_window`).
  * Khi Agent ở phiên trước sửa script `cron_night_tiktok_2fa_watchdog.py` để bổ sung tính năng ghi trace log và bóc tách `failure_breakdown`, Agent đã kích hoạt test nghiệm thu nhưng **quên truyền cờ `--dry-run`**.
  * Trong khung giờ này, Ca 1 nuôi feed đang chạy và giữ lock trên các file Excel / OneDrive. Khi runner kiểm tra hydration, nó nhận diện `WORKBOOK_HYDRATION_FAILED` và trả về mã thoát `5`.
  * Hàm `dispatch_report()` vì không có cờ `--dry-run` đã gọi thẳng Telegram Bot API bắn thông báo lỗi thật vào nhóm chat. Việc Agent retry test 2-3 lần đã tạo ra một đợt bão spam tin nhắn lỗi giả lập.

---

## 2. Rào Chắn Nghiệm Thu Bắt Buộc (Dry-Run Enforcement Contract)
1. **Quy tắc Bất Biến khi Test Watchdog / Runner Có Bắn Tin Nhắn:**
   * Mọi lệnh chạy thử, nghiệm thu script watchdog gửi tin Telegram (như `cron_night_tiktok_2fa_watchdog.py`, `post_noon_chain_watchdog.py`, `post_morning_gmail_2fa_watchdog.py`) **BẮT BUỘC PHẢI KÈM CỜ `--dry-run`**.
   * Ở chế độ `--dry-run`, hàm `dispatch_report` chỉ in nội dung ra stdout/terminal để kiểm tra định dạng và dữ liệu bóc tách, **TUYỆT ĐỐI KHÔNG GỌI API TELEGRAM**.
2. **Kỷ Luật Giờ Nuôi Acc (Feed Hours Invariant):**
   * Trong các khung giờ nuôi acc (Ca 1: 05:05-09:30, Ca 2: 11:45-15:30, Ca 3: 17:45-21:30):
     - Tuyệt đối cấm chạy bất kỳ lệnh test nào không có `--dry-run`.
     - Tuyệt đối không dùng cờ `--force` khi không có chỉ thị trực tiếp từ người vận hành.
3. **Phân Biệt Lỗi Thật vs Báo Cáo Rác:**
   * Khi kiểm tra lỗi runner exit 5 trong khung giờ nuôi acc, việc đầu tiên là kiểm tra xem có ai hoặc phiên agent nào đang gọi script thủ công bằng cách kiểm tra trace log `D:/Taadaa/reports/night_2fa_trace_{date}.log` và log tiến trình hệ thống, tránh suy diễn sai lệch về tình trạng thiết bị.
