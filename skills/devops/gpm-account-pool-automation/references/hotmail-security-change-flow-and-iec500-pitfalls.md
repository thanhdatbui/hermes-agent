# Hotmail GPM Security Change Flow, 6H Reporting, and iec=500 Pitfalls

## 1. Chuẩn hóa 5 Bước Bảo Mật Hotmail qua GPM (100% PC, Không Dùng S7)
Quy trình đổi bảo mật trên profile GPM theo runner canonical `gpm_change_hotmail_security.py`:
1. **Bước 1 (Bật 2FA TOTP):** Sinh Secret Key offline (`pyotp`), nạp xác thực vào Microsoft proofs, lưu Secret Key vào Cột 4 Excel `gmail_clean_v2.xlsx`.
   *BẮT BUỘC add 2FA thành công mới được sang Bước 2. CẤM đổi pass mù khi chưa có 2FA.*
2. **Bước 2 (Đổi Mật khẩu):** Sinh pass mạnh ngẫu nhiên $\ge 14$ ký tự, đổi pass thành công ghi ngay vào Cột G `taikhoan_dat_v2_updated .xlsx` và Cột 3 `gmail_clean_v2.xlsx`.
3. **Bước 3 (Sign Out Everywhere):** Bấm "Đăng xuất khỏi mọi nơi" và xác nhận dialog để thu hồi token bên bán trên toàn cầu.
4. **Bước 4 (Relogin Live pass mới + TOTP):** Điều hướng trực tiếp `login.live.com`, đăng nhập lại bằng email + pass mới + giải 2FA TOTP, tích "Không hỏi lại trên thiết bị này".
5. **Bước 5 (KMSI - Duy trì đăng nhập):** Đóng Cookie consent banner và bấm [Có] tại màn hình "Duy trì đăng nhập?" để lưu sống cookie/phiên vĩnh viễn trên profile GPM.
6. **Xóa Token Cột 9 & Cooldown:** Xóa trắng Cột 9 (`token = None`) trong `gmail_clean_v2.xlsx`, gán cooldown 24h cho Egress IP và Proxy port.

## 2. Kỷ Luật Báo Cáo Định Kỳ 6H (cron_hotmail_gpm_lifecycle_6h_report.py)
- **Tách riêng lỗi BLOCKED:** TUYỆT ĐỐI KHÔNG gộp số nick bị lỗi/kẹt vào hàng đợi đang chờ (`CHANGE_INFO`). Báo cáo bắt buộc phải có dòng riêng:
  `⚠️ Lỗi / Kẹt cần cứu (BLOCKED): N (Kibe: X | Admin: Y)`
- **Hàng đợi CHANGE_INFO:** Chỉ tính các nick có status bình thường (`PENDING`, `WAITING`, `COMPLETED`), đã ngâm đủ $\ge 7$ ngày, đã reg TikTok và ChatGPT thành công.

## 3. Pitfall Lớn: Microsoft `iec=500` & Phân Loại Nick Có/Không Có Mail Khôi Phục
Khi gọi CDP nạp 2FA Authenticator tại `https://account.live.com/proofs/manage/additional`:
- **Nhóm nick ĐÃ CÓ mail khôi phục (e.g. fviainboxes.com):**
  Microsoft cho phép click `#AddProofLink` -> `#Add_msAuthApp` ("Sử dụng ứng dụng") để hiện ngay khóa bí mật `#iPlainTextData`.
- **Nhóm nick CHỈ CÓ mật khẩu (chưa có mail khôi phục hay SĐT):**
  Microsoft backend từ chối thêm app đơn lẻ và tự động redirect về:
  `https://account.live.com/proofs/Manage?iec=500&apt=3`
  Hệ quả: Modal không hiển thị khóa bí mật, script đợi `#iPlainTextData` quá 35s sẽ timeout và bị set `BLOCKED`.
- **Giải pháp xử lý chuẩn (User Invariant):**
  - **Tự động Add Mail Khôi Phục fviainboxes.com trước:**
    Đối với các nick chỉ có Password, KHÔNG cố ép bấm Authenticator để bị `iec=500`. Bắt buộc chọn `#Add_email` ("Gửi mã qua email") -> sinh địa chỉ mail `{username}{suffix}@fviainboxes.com` -> gọi `mail_domain_otp_helper.fetch_recovery_email_otp()` để lấy OTP qua API -> nhập mã xác minh.
    Sau khi thêm thành công mail khôi phục, Microsoft đã có anchor proof hợp lệ -> tiếp tục quy trình B1 thêm Authenticator TOTP như bình thường. Đồng thời lưu mail khôi phục vừa thêm vào Cột 5 `gmail_clean_v2.xlsx`.
  - **Re-authentication Challenge & Form Submission Pitfall:**
    - Khi vào các trang bảo mật nhạy cảm (`EnableTfa` / `manage/additional` / `password/change`), Microsoft thường đòi đăng nhập lại.
    - CẢNH BÁO FORM MỚI: Microsoft cập nhật input từ `#i0116` / `#i0118` sang `#usernameEntry` / `#passwordEntry`.
    - CẤM TUYỆT ĐỐI chỉ dùng `press("Enter")` vì form mới không submit! Bắt buộc phải click tường minh nút submit: `button[type="submit"], #idSIButton9, input[value="Tiếp theo"]` / `input[value="Đăng nhập"]`, kèm click nút KMSI `button[type="submit"], #idSIButton9, input[value="Có"]`.

## 4. GPMLogin Windows Boot Autostart & Local API Recovery
- **Tự động mở khi khởi động máy (Boot Startup):**
  File VBS đặt tại `C:\Users\Kibe\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\start_gpmlogin.vbs`:
  ```vbs
  Set WshShell = CreateObject("WScript.Shell")
  WshShell.CurrentDirectory = "C:\Users\Kibe\AppData\Local\Programs\GPMLogin"
  WshShell.Run """C:\Users\Kibe\AppData\Local\Programs\GPMLogin\GPMLogin.exe""", 1, False
  Set WshShell = Nothing
  ```
- **Self-Healing trong Code (`ensure_gpm_running`):**
  Trước khi gọi start/list profile, kiểm tra `check_health()`. Nếu port 19995 không phản hồi (GPMLogin bị tắt), client tự động khởi chạy và chờ tối đa 15s cho API sẵn sàng thay vì dừng báo lỗi làm gián đoạn cronjob.
  - **Điều kiện sàng lọc CHANGE_INFO trong Supervisor:**
    Đã BỎ hoàn toàn điều kiện Dual OAuth (OmniRoute + 9Router). CHỈ GIỮ 2 điều kiện tiên quyết: (1) Đã reg TikTok thành công (có ID & PASS) VÀ (2) Đã reg ChatGPT (có PASS CHATGPT Cột 12 hoặc `chatgpt_registered_at`).
  - **Kỷ luật bóc tách trạng thái trong Báo Cáo 6H:**
    Báo cáo 6H (`cron_hotmail_gpm_lifecycle_6h_report.py`) bắt buộc lọc sạch danh sách `CHANGE_INFO` (chỉ đếm các nick sẵn sàng, loại trừ các nick `BLOCKED/FAILED/ERROR`), và hiển thị dòng cảnh báo riêng `⚠️ Lỗi / Kẹt cần cứu (BLOCKED): N` để người vận hành nắm bắt ngay hiện trường lỗi thay vì giấu trong hàng đợi.
