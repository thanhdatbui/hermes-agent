# Hotmail GPM Security Change Flow, 6H Reporting, and iec=500 Pitfalls

## 1. Chuẩn hóa 5 Bước Bảo Mật Hotmail qua GPM (100% PC, Không Dùng S7)
Quy trình đổi bảo mật trên profile GPM theo runner canonical `gpm_change_hotmail_security.py`:
- **Nguyên tắc ghi dữ liệu lũy tiến (Write-Through Persistence — Chống mất dữ liệu):**
  * TUYỆT ĐỐI KHÔNG gom lại chờ relogin hay chờ hết phiên mới ghi file Excel.
  * Làm tới đâu, thành công bước nào là BẮT BUỘC ghi ngay lập tức xuống ổ cứng bước đó để tránh mất dữ liệu nếu rớt mạng/crash ở bước sau:
    1. Vừa add mail khôi phục và xác minh OTP xong ➔ Ghi ngay vào Cột 5 `gmail_clean_v2.xlsx`.
    2. Vừa bóc Secret Key 2FA xong ➔ Ghi ngay vào Cột 4 `gmail_clean_v2.xlsx` trước khi kích hoạt.
    3. Microsoft vừa chấp nhận mật khẩu mới ➔ Ghi ngay vào Cột 3 `gmail_clean_v2.xlsx` và Cột G (Cột 7 - PASS MAIL) workbook farm `taikhoan_dat_v2_updated .xlsx`, xóa OAuth Cột 9, và ghi nhận state file TRƯỚC KHI Sign Out Everywhere hay Relogin.
- **Bản chất kỹ thuật kiểm chứng thực tế: Tại sao BẮT BUỘC có Mail Khôi Phục mới bật được 2FA?**
  * Thực nghiệm kiểm chứng: Nick Zin chỉ có Password khi cố nhảy cóc truy cập `https://account.live.com/proofs/EnableTfa`, Microsoft chặn cứng với thông báo: *"Để bật xác nhận hai bước, chúng tôi cần hai cách để chắc chắn bạn là bạn"* và hiển thị ô bắt buộc điền email `ai_do@example.com` (bản dịch của `someone@example.com`).
  * Microsoft từ chối mở wizard Authenticator nếu tài khoản chưa có tối thiểu 2 phương thức xác minh (Mật khẩu + Email khôi phục).
  * Quy tắc ngâm: Sau khi add email khôi phục và bóc OTP thành công (vài giây), tài khoản đủ điều kiện và Microsoft mở khóa cho add 2FA Authenticator liền tại chỗ, HOÀN TOÀN KHÔNG CẦN NGÂM THÊM 7 ngày.
- **Phân tách ngữ cảnh Interstitials (Proofs URL Isolation):**
  * Khi xử lý các popup chuyển tiếp Microsoft (`handle_microsoft_interstitials`), BẮT BUỘC kiểm tra URL: Nếu URL chứa `proofs`, TUYỆT ĐỐI KHÔNG tự động click các nút có text `Tiếp theo`, `Next` vì sẽ bấm nhầm vào form đang cấu hình. Chỉ xử lý interstitial khi ở trang login/interstitial thuần túy.
- **Telemetry & Structured Observability (Trace Correlation):**
  * Mọi bước quan trọng đều phát sinh sự kiện chuẩn JSON qua `log_telemetry_event(event_type, email, machine, **kwargs)`.
  * Deterministic `trace_id` (SHA-256 12 ký tự từ `email + YYYYMMDD`) giúp trace correlation liên thông toàn bộ lifecycle của nick trên farm scale lớn.
- **Phạm vi quản lý Dual-Farm (Kibe + Admin):**
  * Toàn bộ 2 farm gồm ~1.280 tài khoản (Kibe 1-80: 640 accounts, Admin 201-280: ~640 accounts). CẤM đếm thiếu cụm Admin khi đối soát số lượng và báo cáo.

1. **Bước 1 (Add Mail Khôi Phục nếu chưa có):** Sinh mail tạm `<username><3_rand>@fviainboxes.com`, điền Microsoft, bóc OTP qua API `fviainboxes.com/messages` xác minh thành công -> Ghi ngay Cột 5 Excel. (Nếu nick đã có mail kp sẵn thì skip bước này).
2. **Bước 2 (Bật 2FA TOTP):** Sinh/bóc Secret Key offline (`pyotp`), ghi ngay Cột 4 Excel, nạp xác thực vào Microsoft proofs và kích hoạt công tắc Two-step verification tổng qua `EnableTfa`.
   *BẮT BUỘC add 2FA thành công mới được sang Bước 3. CẤM đổi pass mù khi chưa có 2FA.*
3. **Bước 3 (Đổi Mật khẩu):** Sinh pass mạnh ngẫu nhiên $\ge 14$ ký tự, đổi pass thành công -> Ghi ngay vào Cột G `taikhoan_dat_v2_updated .xlsx` và Cột 3 `gmail_clean_v2.xlsx` kèm xóa token Cột 9.
4. **Bước 4 (Sign Out Everywhere):** Bấm "Đăng xuất khỏi mọi nơi" và xác nhận dialog để thu hồi token bên bán trên toàn cầu.
5. **Bước 5 (Relogin Live pass mới + TOTP):** Điều hướng trực tiếp `login.live.com`, đăng nhập lại bằng email + pass mới + giải 2FA TOTP, tích "Không hỏi lại trên thiết bị này" (KMSI) để lưu sống cookie/phiên vĩnh viễn trên profile GPM.
6. **Cooldown IP & Proxy:** Gán cooldown 24h cho Egress IP và Proxy port sau khi hoàn tất.

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
    Đối với các nick chỉ có Password, KHÔNG cố ép bấm Authenticator để bị `iec=500`. Bắt buộc thực hiện luồng:
    1. Tại `https://account.live.com/proofs/manage/additional`: click `#AddProofLink` -> click `#Add_email` (`a#Add_email.box.passkey`).
    2. Trang điều hướng sang `https://account.live.com/proofs/Add?mpsplit=2&apt=2`: sinh mail `{username}{suffix}@fviainboxes.com` -> điền vào `#EmailAddress` (`input[type="email"]#EmailAddress`) -> click `#iNext` (`input[type="submit"]#iNext`).
    3. Trang chuyển tiếp sang `https://account.live.com/proofs/Verify?...`: gọi `mail_domain_otp_helper.fetch_recovery_email_otp(rec_email, timeout_seconds=40)` (API `https://fviainboxes.com/messages?username={u}&domain=fviainboxes.com`) lấy mã OTP 6 số.
    4. Điền mã OTP vào ô `#iOttText` (`input[type="tel"]#iOttText`) -> click `#iNext` (`input[type="submit"]#iNext`).
    5. Lưu ngay địa chỉ mail khôi phục vào Cột 5 `gmail_clean_v2.xlsx`.
    Sau khi thêm thành công mail khôi phục, Microsoft đã có anchor proof hợp lệ -> tiếp tục quy trình B1 thêm Authenticator TOTP như bình thường.
  - **Phân loại nguồn gốc từ đơn hàng mua Hotmail:**
    - Đơn hàng xuất kho 4 trường (`email|pass|token|client_id` trong `latest_bought_70.txt`, `hotmail_all_60_bought.txt`) là sản phẩm KHÔNG kèm mail khôi phục từ bên bán.
    - Đơn hàng xuất kho 5 trường (`email|pass|token|client_id|recovery_email` trong `latest_bought_8_m76_79.txt`) là sản phẩm ĐÃ CÓ sẵn mail khôi phục.
    - Khi kiểm tra đơn hàng thấy chỉ có 4 trường, xác nhận ngay là bên bán giao không kèm mail khôi phục, tự động kích hoạt luồng tạo mail khôi phục `fviainboxes.com` nêu trên.
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
