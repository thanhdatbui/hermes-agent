# Google Prompt S7 Preservation & Automated Verification Challenge Recovery

## 1. Nguyên Tắc Bất Di Bất Dịch: CẤM Đăng Xuất S7 Để Tắt Prompt (User Invariant 2026-09-05)

### Vấn Đề
Khi tài khoản Gmail đã đăng nhập vào thiết bị Android Samsung Galaxy S7 (Farm), Google Play Services tự động đặt S7 làm thiết bị tin cậy bậc 1 nhận **"Lời nhắc của Google" (Google Prompt)**.
Trên giao diện quản lý tài khoản (`myaccount.google.com/signinoptions/twosv`), dòng "Lời nhắc của Google" luôn hiển thị tên thiết bị S7. **Google KHÔNG có nút gạt Tắt riêng cho Lời nhắc nếu thiết bị Android vẫn còn đăng nhập.** Nút duy nhất để làm mất dòng này trên web là nút **"Đăng xuất"** trong `myaccount.google.com/device-activity`.

### Hậu Quả Nghiêm Trọng Nếu Bấm "Đăng Xuất"
- Thiết bị Galaxy S7 thực tế trên Farm sẽ lập tức bị văng phiên Google Account, hiện thông báo đỏ *"Đã xảy ra lỗi và bạn cần đăng nhập lại"* (Action required).
- Toàn bộ các luồng TikTok, CH Play, cập nhật ứng dụng và cron nuôi tài khoản trên máy S7 đó sẽ bị đình trệ hoặc fail.

### Quy Tắc Chuẩn:
- **TUYỆT ĐỐI CẤM vào `device-activity` bấm "Đăng xuất" thiết bị S7 của Farm.**
- **Tại sao cấp quyền OAuth (Antigravity/Developer) vẫn đòi mã S7 dù đã bật 2FA? Có nên gỡ thiết bị S7 không?**
  - *Cơ chế Google:* Luồng cấp quyền OAuth Google Cloud / Developer First-party (Antigravity) được Google xếp vào diện rủi ro cao (High-privilege / Sensitive Action Verification), bắt buộc kích hoạt xác minh qua Thiết bị tin cậy phần cứng bậc 1 (Hardware Trusted Device - Galaxy S7) qua Google Prompt (`challenge/dp`) hoặc Offline Security Code (`challenge/ootp`). Bằng chứng thực tế trên màn hình `challenge/selection`: Google HOÀN TOÀN ẨN tùy chọn nhập mã Authenticator TOTP và Email khôi phục, chỉ hiển thị đúng 2 phương thức: (1) Nhấn Có trên Galaxy S7, (2) Nhận mã bảo mật 10 số trên Galaxy S7.
  - *Hậu quả nếu gỡ S7:* S7 bị văng session ("Action required"), đứt gãy cron nuôi TikTok / CH Play; tài khoản mất mỏ neo phần cứng (Hardware Trust Anchor) và Google sẽ giáng trust score, chuyển sang bắt xác minh Số điện thoại (Phone SMS Checkpoint) $\rightarrow$ mất acc vĩnh viễn nếu không có SIM thật.
  - *Bản chất 1 lần:* Cấp quyền OAuth vào OmniRoute CHỈ LÀM 1 LẦN DUY NHẤT. Sau khi exchange thành công, OmniRoute lưu `refresh_token` vĩnh viễn và tự động xin `access_token` mới trong nền, KHÔNG BAO GIỜ hỏi lại máy S7 nữa. Vì vậy **BẮT BUỘC GIỮ NGUYÊN S7 TRÊN FARM**.
- **Giải pháp chuẩn:** Giữ nguyên trạng thái đăng nhập của S7 trên Farm. Thực hiện kích hoạt **2-Step Verification (2FA) qua Ứng dụng Google Authenticator (TOTP)** và lưu chuỗi 32 ký tự Secret Key vào Excel (`master_gmail_manager.xlsx` và `gmail_clean_v2.xlsx`).
- Khi đăng nhập trên PC/GPM ở các phiên sau: Dù Google có hiện màn hình nhắc S7 đầu tiên, script **chỉ cần bấm "Thử cách khác" (Try another way)** $\rightarrow$ Chọn **"Nhập mã từ ứng dụng xác thực"** $\rightarrow$ Điền mã 6 số (sinh từ `pyotp.TOTP(secret_key).now()`) để vào thẳng tài khoản mà không cần chạm vào máy S7.

---

## 2. Cơ Cấu 40 Proxy Farm Kibe (80 Máy = 40 Proxy × 2 Máy)

Toàn bộ 80 máy Farm Kibe được cấu hình cặp 1:2 theo file `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`:
- **32 Proxy Mobi 4G (`test.taadaa.click:5101..5138`):**
  - Cụm 1: `5101` → `5108` (Máy 1..8 ghép với Máy 39..46)
  - Cụm 2: `5111` → `5118` (Máy 9..16 ghép với Máy 47..54)
  - Cụm 3: `5121` → `5128` (Máy 17..24 ghép với Máy 55..62)
  - Cụm 4: `5131` → `5138` (Máy 25..32 ghép với Máy 63..70)
- **7 Proxy MikroTik (`mirotik1.taadaa.click:10001..10007`):**
  - `10001` (Máy 33, 72)
  - `10002` (Máy 34, 73)
  - `10003` (Máy 35, 74)
  - `10004` (Máy 36, 75)
  - `10005` (Máy 37, 77)
  - `10006` (Máy 71, 78)
  - `10007` (Máy 79, 80)
- **1 Proxy Khoalee (`khoalee.duckdns.org:16002`):** Máy 38 và Máy 76.
👉 **Tổng cộng: 32 + 7 + 1 = 40 Proxy vật lý.**

### Quy Tắc Gán Proxy & Tránh Checkpoint:
1. **Ép chuẩn 1:1:** Tài khoản của máy nào BẮT BUỘC phải gán đúng proxy của máy đó trong `PROXYgandienthoai.xlsx`. CẤM gán chéo proxy.
2. **Giới hạn 1 Gmail / 1 Proxy / 1 Phiên:** Trên cùng 1 proxy, không đăng nhập liên tiếp nhiều tài khoản trong cùng 1 batch để tránh bị Google kích hoạt phone SMS checkpoint (`challenge/iap`). Nếu nạp tài khoản cho máy thứ 2 dùng chung proxy, phải giãn cách ca ít nhất 3-4 tiếng.

---

## 3. Hai Cơ Chế Tự Động Vượt Thử Thách Xác Minh Google (Two-Tier Challenge Recovery)

Khi đăng nhập Google trên GPM Browser, Google có thể chuyển hướng sang các trang thử thách bảo mật:

### A. Cơ Chế 1: IMAP OTP Email Khôi Phục (`thanhdatbui1995@gmail.com`)
Áp dụng khi gặp màn hình `challenge/selection` (Chọn cách bạn muốn đăng nhập) có tuỳ chọn *"Nhận mã xác minh tại email khôi phục"*:
- Mailbox khôi phục mặc định: `thanhdatbui1995@gmail.com`.
- Thông tin IMAP: `imap.gmail.com`, SSL port 993, App Password lưu tại biến môi trường `OTP_MAIL_APP_PASSWORD` hoặc Windows Registry `HKCU\Environment\OTP_MAIL_APP_PASSWORD`.
- Script chuẩn: `D:\Taadaa\add mail khoi phuc\read_otp_mail.py` (hàm `fetch_latest_otp(host, user, password, mailbox, sender_hint, lookback_seconds, max_messages)`).
- **Quy trình:**
  1. Click vào lựa chọn email khôi phục trên DOM (`li:has-text("khôi phục"), div:has-text("recovery email")`).
  2. Google gửi mã 6 số về `thanhdatbui1995@gmail.com`.
  3. Script gọi IMAP poll hộp thư INBOX (timeout 60s, delay 5s).
  4. Trích xuất mã OTP 6 số từ subject hoặc body (`extract_otp_code`).
  5. Điền mã vào input (`input#idvPin`, `input[type="tel"]`, `input[type="text"]`) $\rightarrow$ Click Next $\rightarrow$ Vượt qua thành công.

### B. Cơ Chế 2: S7 Security Code 10 Số Qua ADB (BẮT BUỘC DEVICE LOCK)
Áp dụng khi gặp màn hình `challenge/ootp` (Offline One-Time Password) hoặc khi Google gửi prompt `challenge/dp` (bấm "Thử cách khác" $\rightarrow$ chọn "Mã bảo mật"):
- **BẮT BUỘC BỌC TRONG DEVICE LOCK:** Mọi thao tác ADB can thiệp S7 BẮT BUỘC dùng context manager:
  ```python
  from automation_core.device_lock import acquire_device_lock

  with acquire_device_lock(machine=str(machine_id), serial=serial, project="gpm-login", bypass_proxy_readiness=True, force_preempt=True):
      # Thao tác ADB tại đây...
  ```
  Trong khối `finally`, BẮT BUỘC gửi `keyevent 3` (HOME) trước khi nhả lock để trả máy về màn hình chính, chống xung đột với cron nuôi TikTok.
- ADB path: `C:\Program Files (x86)\xiaowei\tools\adb.exe`.
- ATX-Agent port: `17000 + machine_num` (forward từ `tcp:7912`).
- **Quy trình trích xuất mã 10 số:**
  1. Wake & unlock S7: `input keyevent 26` $\rightarrow$ `input keyevent 82` $\rightarrow$ `input swipe 500 1500 500 500`.
  2. Mở trực tiếp cài đặt Google: `am start -n com.google.android.gms/.app.settings.GoogleSettingsLink`.
  3. Lấy UI hierarchy qua ATX `http://127.0.0.1:{17000+m}/dump/hierarchy`.
  4. Nếu tài khoản trên màn hình chưa phải là tài khoản mục tiêu: tap vào banner tài khoản $\rightarrow$ tap chọn email mục tiêu.
  5. Tap vào banner tài khoản $\rightarrow$ tap **"Tài khoản Google"**.
  6. Cuộn màn hình tìm và tap **"Bảo mật và đăng nhập"** (hoặc "Bảo mật").
  7. Tap **"Mã bảo mật"** $\rightarrow$ S7 hiển thị 2 mã 10 số (hiệu lực 15 phút).
  8. Trích xuất mã regex `r"^\d{10}$"` (loại bỏ ký tự Unicode LTR `\u202d` và khoảng trắng).
  9. Nhấn phím HOME (`input keyevent 3`) để trả màn hình S7 về trạng thái ban đầu.
  10. Điền mã 10 số vào input của Google trên GPM Browser $\rightarrow$ Click Next $\rightarrow$ Đăng nhập thành công.

### C. Cơ Chế 3: ADB Duyệt Trực Tiếp Google Prompt Trên S7 (BẮT BUỘC DEVICE LOCK)
Áp dụng khi gặp màn hình `challenge/dp` (Device Push Prompt):
- Khi Google hiển thị *"Kiểm tra Galaxy S7 của bạn"*:
  1. Bắt buộc bọc trong `acquire_device_lock(machine=str(mid), serial=serial, project="gpm-login", bypass_proxy_readiness=True, force_preempt=True)`.
  2. Đánh thức và mở khóa màn hình (`keyevent 26` $\rightarrow$ `keyevent 82`).
  3. Mở thanh thông báo (`cmd statusbar expand-notifications`).
  4. **Bẫy Thông báo Nhóm (Grouped Notifications):** Thông báo Dịch vụ Google Play thường bị gộp (`Tổng N thông báo`). Không click header mà phải tap vào thông báo con chứa `"Cho phép một ứng dụng truy cập dữ liệu của bạn trên Google?"`, `"Bạn đang cố đăng nhập?"` hoặc email mục tiêu, hoặc tap `"Mở rộng"`. Node chính xác trên Samsung S7 là `TextView: "Cho phép một ứng dụng truy cập dữ liệu của bạn trên Google?"` (click trực tiếp vào dòng này sẽ bung thẳng dialog phê duyệt).
  5. **Bẫy Khớp Số PIN (PIN Matching):** Nếu PC hiển thị mã PIN 2 chữ số (ví dụ `74`), màn hình S7 sẽ hiện 3 nút chọn số (không có nút "Có"). Ngay khi tap đúng nút số khớp `target_pin`, BẮT BUỘC ghi nhận duyệt thành công (`return True`) ngay, không chờ nút "Có".
  6. Nếu không có mã PIN (chỉ hỏi Yes/No): Tap nút `"Có, tôi là người thực hiện"` / `"Có"` / `"Yes"`.
  7. Trong khối `finally`: Luôn gửi phím HOME (`keyevent 3`) trước khi nhả lock.

---

## 4. Circuit Breaker Bắt Buộc Khi Chạy Batch (Ngắt Lỗi Liên Tiếp)

Để bảo toàn dàn tài khoản Farm và tránh spam khiến Google cấm IP:
- Luôn cài đặt bộ đếm thất bại liên tiếp (`consecutive_failures`).
- **Ngưỡng kích hoạt:** Nếu **3 tài khoản liên tiếp** bị thất bại (dính `challenge/iap` đòi SMS, proxy timeout, hoặc không vượt được thử thách) $\rightarrow$ **DỪNG NGAY LẬP TỨC (HALT BATCH)**.
- Khối `finally` đóng sạch toàn bộ profile qua API `/api/v3/profiles/stop/{id}` và kill tiến trình Chrome theo port CDP, sau đó gửi báo cáo khẩn cấp cho người dùng.

---

## 5. Tự Động Hóa Nạp Tài Khoản Vào OmniRoute & Gán Proxy 1:1

Sau khi hoàn tất lấy OAuth Code (Antigravity) từ GPM Browser:
1. **Exchange Code vào OmniRoute (`http://127.0.0.1:20129`):**
   ```python
   res_ex = requests.post(
       "http://127.0.0.1:20129/api/oauth/antigravity/exchange",
       json={"code": captured_code, "redirectUri": redirect_uri, "codeVerifier": code_verifier, "state": state},
       timeout=20
   ).json()
   conn_id = res_ex.get("connection", {}).get("id")
   ```
2. **Gán Proxy 1:1 (Scope: Account):**
   - Lấy danh sách proxy từ `GET /api/settings/proxies`, tìm `proxy_id` có port khớp với proxy của profile.
   - Gán proxy cố định cho connection:
     ```python
     requests.put(
         "http://127.0.0.1:20129/api/settings/proxies/assignments",
         json={"scope": "account", "scopeId": conn_id, "proxyId": proxy_id},
         timeout=5
     )
     ```
3. **Đồng Bộ Model:**
   ```python
   requests.post(f"http://127.0.0.1:20129/api/providers/{conn_id}/sync-models", timeout=10)
   ```
4. **Bảo Toàn IP Qua Sing-box:** Dải port farm Mobi (`5101-5138`) và MikroTik (`10001-10007`) tương ứng với Sing-box local port `20000 + (port - 5100)` hoặc `20000 + (port - 10000)`. Khi Playwright mở GPM, gán proxy tương ứng để đảm bảo IP nhất quán tuyệt đối.
