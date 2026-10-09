# Google 2FA TOTP Localization, Re-Auth Password Challenge & GPM Concurrency Rules (2026-09-04)

## 1. Google 2FA UI Localization Pitfall (Tiếng Việt vs Tiếng Anh)
- **Triệu chứng:** Khi chạy script tự động bật 2FA trên các profile Google tạo tại Việt Nam / proxy Mobile Farm S7, script dùng text tiếng Anh (`text="2-Step Verification"`, `text="Authenticator app"`, `text="Set up authenticator"`) bị timeout `Timeout 30000ms exceeded` 100%.
- **Nguyên nhân:** Giao diện Google hiển thị hoàn toàn bằng tiếng Việt:
  - *"2-Step Verification"* hiển thị là *"Xác minh 2 bước"* (href: `signinoptions/twosv`).
  - *"Authenticator"* giữ nguyên nhưng nút thiết lập là *"Thiết lập"* hoặc *"Thêm ứng dụng Authenticator"*.
- **Khắc phục chuẩn (Language-Agnostic Href & Attributed Selectors):**
  - Luôn sử dụng URL href pattern thay vì text content:
    ```python
    # Click 2-Step Verification
    page.click('a[href*="signinoptions/twosv"]')
    
    # Click Authenticator
    page.click('a[href*="two-step-verification/authenticator"]')
    
    # Click Can't scan QR / Không thể quét mã
    page.click('a[href*="cannot-scan"], button:has-text("Can\'t scan"), button:has-text("Không thể quét")')
    ```

---

## 2. Google Re-Authentication Password Challenge Gate
- **Hiện tượng:** Khi click vào liên kết `signinoptions/twosv`, Google KHÔNG vào thẳng trang cấu hình 2SV mà chuyển hướng đến:
  `https://accounts.google.com/v3/signin/challenge/pwd?continue=...signinoptions%2Ftwosv`
- **Xử lý bắt buộc:**
  - Script tự động bật 2FA BẮT BUỘC phải đọc sẵn mật khẩu của tài khoản từ Excel (`D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` hoặc `gmail_clean_v2.xlsx`).
  - Khi phát hiện URL chứa `signin/challenge/pwd`:
    ```python
    if "challenge/pwd" in page.url:
        page.fill('input[type="password"]', password)
        page.click('button:has-text("Tiếp theo"), button:has-text("Next"), #passwordNext')
        page.wait_for_load_state("domcontentloaded")
    ```
  - Sau khi vượt qua password challenge, Google mới cho phép mở trang Authenticator setup.

---

## 3. GPM Proxy Fail-Safe Behavior (HTTP 407 & Connection Failures)
- **Cơ chế:** Khi proxy gán vào profile bị die, sai cổng hoặc sai user:pass (nhận HTTP 407 Proxy Authentication Required):
  - API `GET /api/v3/profiles/start/{id}` trả về `{"success": false, "message": "Proxy authentication failed"}`.
  - GPM **từ chối khởi động browser** (không tạo process Chrome, không mở CDP port).
  - Đây là cơ chế an toàn chuẩn nhằm chống rò rỉ IP máy chủ thật.
- **Kỷ luật:** CẤM cố gắng xóa cờ proxy để chạy bằng IP thật. Bắt buộc kiểm tra lại proxy IP/port/auth tương ứng trong file `PROXYgandienthoai.xlsx` và cập nhật lại vào `JsonData`.

---

## 4. Quản lý Tài nguyên & Concurrency Trên GPM Local API (19995)
- **Nguyên nhân crash 10-25 workers:** Khi bung đồng loạt 10 đến 25 instances Chromium Core 142 qua GPM Local API trên cùng một máy:
  - GPM Local API bị nghẽn port binding (`connect ECONNREFUSED 127.0.0.1:53xxx`).
  - Trình duyệt bị đóng bất ngờ (`Target page, context or browser has been closed`).
- **Mô hình vận hành tối ưu (Batching 3-4 Workers với Stagger Startup):**
  - Chia tổng số profiles cần xử lý thành các cụm (batches) gồm **3 đến 4 workers chạy song song**.
  - Áp dụng **stagger startup delay** (10-15s giữa các lần start profile) để tránh xung đột port và RAM spikes.
  - Sau khi gọi API start, **chờ tối thiểu 5-10s** cho Chrome khởi động hoàn tất trước khi gọi `connect_over_cdp` (kèm retry loop 5 lần).
  - Trong mỗi luồng, sau khi xong profile (dù thành công hay thất bại), BẮT BUỘC gọi `/api/v3/profiles/stop/{id}` và dọn dẹp tiến trình con ngay lập tức.

---

## 5. Preflight Check Excel & Kỷ Luật Viết Script Tự Động (Tránh Đứt Gãy Do LLM Turns)

### A. Preflight Check Trạng Thái 2FA Trong Excel
- **Bài học thực tế:** Trước khi nạp danh sách acc cần bật 2FA, BẮT BUỘC đọc và kiểm tra 2 file:
  - `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (cột `2FA Secret` / `Secret Key`).
  - `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` (cột `2fa`).
- Nếu tài khoản đã có Secret Key hợp lệ (chuỗi 32 ký tự Base32): **BỎ QUA NGAY 100%**.
- Việc không check trước dẫn đến chạy lại các acc đã có 2FA, gây xung đột mã xác thực và lãng phí tài nguyên.

### B. Kỷ Luật Viết Script Python Tự Động vs Cấm Lái Browser Từng Turn Bằng LLM
- **Cấm kỵ:** Tuyệt đối không giao subagent tự lái trình duyệt từng bước qua lệnh gọi tool LLM đơn lẻ (1 turn click 2SV, 1 turn nhập pass, 1 turn click Authenticator...). Với 9-25 acc, số turn LLM lên tới 70-90 turns, làm phình context window lên hàng trăm nghìn tokens, chạy mất 1.5 - 2 tiếng và chắc chắn đứt gãy giữa chừng khi LLM gateway timeout hoặc gặp lỗi mạng (`API call failed after 2 retries: Connection error`).
- **Giải pháp chuẩn (Script-First):**
  - Worker subagent được giao việc BẮT BUỘC viết một file script Python hoàn chỉnh (ví dụ: `scripts/run_2fa_9profiles.py`) đóng gói toàn bộ: vòng lặp qua các acc, xử lý challenge password, click Authenticator, bóc Secret Key, tính TOTP bằng `pyotp`, ghi kết quả vào Excel, và bọc trong `try ... finally` đóng profile.
  - Sau đó worker chỉ cần chạy script bằng 1 lệnh `python <script_path>` trong terminal và kiểm tra log kết quả.

### C. Cách Ly Nghiêm Ngặt Group 1 Farm S7 Khỏi Admin Pool MikroTik
- Group 1 trong GPM là tài sản vận hành Farm S7 của 80 máy (`test.taadaa.click:5101..5138` / Singbox `20001..20074`), đặt tên theo chuẩn `<Số Máy> - <Gmail> - <Port>`.
- TUYỆT ĐỐI CẤM tạo hay nạp profile MikroTik Admin (`mirotik1...:10001..10035`) vào Group 1.
- TUYỆT ĐỐI CẤM tạo duplicate profile cùng email giữa Farm S7 và Admin Pool (như lỗi Bobby 15 vs 10014). Mọi profile Admin phải nằm ở Group riêng hoặc Group 0 (Archive).

