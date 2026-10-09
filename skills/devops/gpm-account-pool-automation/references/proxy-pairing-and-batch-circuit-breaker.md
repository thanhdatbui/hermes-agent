# Farm 2-Tier Proxy Topology & Batch Login Circuit Breaker Discipline

## 1. Bản Chất Topology Proxy Của Farm 80 Máy Kibe (Chuẩn 40 Proxy x 2 Máy)
Toàn bộ 80 máy Farm Kibe được phân bổ vào đúng **40 proxy vật lý** (mỗi proxy map cố định 2 máy):
- **32 Cổng USB 4G Mobi (`test.taadaa.click`):** Gồm 4 dải 8 port (32 port thực tế):
  - Dải 1: `5101` → `5108` (8 proxy — Máy 1..8 ghép cặp với Máy 39..46)
  - Dải 2: `5111` → `5118` (8 proxy — Máy 9..16 ghép cặp với Máy 47..54)
  - Dải 3: `5121` → `5128` (8 proxy — Máy 17..24 ghép cặp với Máy 55..62)
  - Dải 4: `5131` → `5138` (8 proxy — Máy 25..32 ghép cặp với Máy 63..70)
- **7 Cổng MikroTik (`mirotik1.taadaa.click:10001` → `10007`):** 7 proxy — Dùng cho Máy 33 → 37, Máy 71 → 75, và Máy 77 → 80.
- **1 Cổng Khoalee (`khoalee.duckdns.org:16002`):** 1 proxy — Dùng cho Máy 38 và Máy 76.
👉 **Tổng cộng: 32 + 7 + 1 = ĐÚNG 40 PROXY VẬT LÝ.** Tầng 1 (Máy 01..32) ghép cặp với Tầng 2 (Máy 39..70).

---

## 2. Quy Tắc Gán Proxy & Tái Sử Dụng Port (BẮT BUỘC)

### A. Cấm Login Nhiều Con Cùng Port Trong 1 Batch
- **Hành vi sai lầm:** Cho 2-3 tài khoản dùng chung 1 IP proxy đăng nhập GPM liên tiếp trong cùng một thời điểm.
- **Cơ chế phát hiện của Google:** Trên Android thật, Google tin tưởng Android ID & persistent token. Nhưng trên GPM Browser (môi trường mới), việc nhiều tài khoản xuất hiện từ cùng 1 IP trong vài phút bị thuật toán đánh dấu là **hành vi spam tự động**.
- **Hậu quả:** Google lập tức kích hoạt **Checkpoint số điện thoại (`challenge/iap`)** hoặc chặn reCAPTCHA diện rộng.

### B. Quy Tắc Tái Sử Dụng Port Theo Ca (Giãn Cách Thời Gian)
- Mỗi port proxy trong một buổi **chỉ được phép nạp 1 tài khoản mới**.
- Nếu muốn nạp tài khoản cho máy Tầng 2 dùng chung port với máy Tầng 1 (VD: Máy 39 dùng lại port 5101 của Máy 01):
  - **Bắt buộc giãn cách theo ca (tối thiểu cách nhau 3-4 tiếng).**
  - Đảm bảo profile trước đã hoàn tất, đã tắt sạch Chrome và IP đã được xoay hoặc nghỉ.

---

## 3. Cấu Hình Tối Ưu Cho Batch Login (Max Workers = 3, Stagger 15s)
- **Số workers song song:** **`max_workers = 3`** (không chạy 5-10 workers gây nghẽn socket Local API port 19995 và lag CPU/RAM).
- **Stagger startup:** Trì hoãn 10 - 15 giây giữa các lần start profile để tránh đột biến tài nguyên.
- **Immediate Stop:** Khối `finally` BẮT BUỘC gọi `GET /api/v3/profiles/stop/{id}` và kill Chrome theo PID/port ngay sau khi xử lý xong từng tài khoản.

---

## 4. Circuit Breaker — Ngắt Khẩn Cấp & Phân Biệt PROXY_ERROR vs Google Account Failure (2026-09-05)
Khi chạy batch tự động nạp Gmail hoặc kích hoạt 2FA:
1. **Ngưỡng kích hoạt ngắt (Trip Threshold):**
   - Nếu gặp **$\ge 2$ đến 3 tài khoản liên tiếp** bị:
     - Checkpoint số điện thoại (`challenge/iap`).
     - Sai mật khẩu / Đổi mật khẩu (`DIE`).
     - Lỗi Google xác minh thất bại (`FAILED`).
2. **Quy tắc phân tách PROXY_ERROR (Không tăng Consecutive Failures):**
   - **Hiện tượng:** Khi GPM trả về `{'success': False, 'data': None, 'message': 'Không thể kết nối tới proxy'}`, đây là lỗi mạng/timeout cục bộ của proxy riêng máy đó, **không phải lỗi checkpoint hay die của tài khoản Google**.
   - **Kỷ luật xử lý:** Ghi nhận `status = "PROXY_ERROR"`, xóa profile tạm, nhưng **KHÔNG tăng biến đếm `consecutive_failures`**. Chỉ tăng đếm khi gặp lỗi trực tiếp từ Google (`CHECKPOINT`, `DIE`, `FAILED`). Điều này ngăn việc một proxy rớt mạng làm ngắt oan cả batch tài khoản khỏe phía sau.
3. **Hành động bắt buộc khi Circuit Breaker nổ (Fail-Fast):**
   - **DỪNG NGAY TOÀN BỘ TIẾN TRÌNH**, hủy bỏ các task còn lại trong hàng đợi.
   - Gọi stop cho toàn bộ profile đang chạy dở và dọn sạch tiến trình Chrome theo port.
   - **Báo cáo sự cố ngay lập tức cho user** kèm ảnh chụp màn hình hiện trường và nguyên nhân cụ thể.
   - **CẤM TUYỆT ĐỐI** tiếp tục chạy retry mù, vì sẽ làm hỏng hàng loạt tài khoản trong pool.

---

## 5. Phân Loại Thử Thách Đăng Nhập (Challenge Signatures) & Bộ Chọn Chuẩn (2026-09-05)
Trong quá trình đăng nhập tự động trên GPM, Google có thể trả về các URL challenge đặc thù:
- **`challenge/recaptcha`:** reCAPTCHA Enterprise. Giải tự động 100% bằng Audio Challenge (`pydub` + `speech_recognition` qua Google STT).
- **`challenge/pwd`:** Re-authenticate mật khẩu trước khi vào cài đặt 2SV / Authenticator. Điền mật khẩu từ Master Excel.
- **Speedbump / GDS Landing (Video selfie, Passkey, Onboarding):**
  - Google hiện các màn hình "Bảo vệ quyền truy cập vào tài khoản bằng video selfie" (`gds.google.com` hoặc `speedbump`).
  - Nút "Để sau" (Later), "Bỏ qua", "Huỷ", "Không phải bây giờ" thường được render dưới dạng thẻ `<a>` (`<a class="WpHeLc ...">Để sau</a>`) hoặc bọc trong thẻ `<span>`, **KHÔNG PHẢI thẻ `<button>`**.
  - **Bắt buộc mở rộng `dismiss_selectors` & `agree_selectors`**:
    ```python
    dismiss_selectors = [
        'a:has-text("Để sau")', 'button:has-text("Để sau")', 'span:has-text("Để sau")',
        'a:has-text("Không phải bây giờ")', 'button:has-text("Không phải bây giờ")', 'span:has-text("Không phải bây giờ")',
        'a:has-text("Not now")', 'button:has-text("Not now")', 'span:has-text("Not now")',
        'a:has-text("Bỏ qua")', 'button:has-text("Bỏ qua")', 'span:has-text("Bỏ qua")',
        'a:has-text("Skip")', 'button:has-text("Skip")', 'span:has-text("Skip")',
        'a:has-text("Hủy")', 'button:has-text("Hủy")', 'span:has-text("Hủy")',
        'a:has-text("Huỷ")', 'button:has-text("Huỷ")', 'span:has-text("Huỷ")',
        'a:has-text("Lúc khác")', 'button:has-text("Lúc khác")', 'span:has-text("Lúc khác")'
    ]
    ```
- **`challenge/selection` (Menu chọn hình thức xác minh):**
  - Tránh dùng selector div broad (`div:has-text("mã bảo mật")` / `div:has-text("thiết bị")`) vì sẽ click trúng div cha bọc ngoài khiến trang không chuyển trạng thái.
  - **Selector chuẩn bắt đúng thẻ `li` hoặc `data-challengetype`:**
    ```python
    rec_opt = page.locator('li:has-text("email khôi phục"), li:has-text("recovery email"), div[data-challengetype="12"]')
    sec_opt = page.locator('li:has-text("mã bảo mật"), li:has-text("security code"), div[data-challengetype="8"]')
    ```
- **`challenge/ootp` (Offline One-Time Password 10 số từ S7):**
  - Google yêu cầu nhập mã bảo mật 10 số tạo ngoại tuyến trên điện thoại Android (Settings $\rightarrow$ Google $\rightarrow$ Manage Google Account $\rightarrow$ Security $\rightarrow$ Security Code).
  - Ô nhập mã trên `challenge/ootp` có thể là `input[type="text"]` hoặc `input#security-code-input`, không chỉ riêng `input[type="tel"]`.
  - Khi phát hiện `"challenge/ootp" in current_url`, bắt buộc ưu tiên gọi `get_s7_security_code()` từ thiết bị S7, không chạy polling OTP email IMAP.
- **`challenge/dp` (Device Prompt):** Google đẩy thông báo "Kiểm tra điện thoại của bạn / Chạm vào Có". Nếu S7 không tương tác kịp -> bấm "Thử cách khác" (Try another way) để chuyển sang `challenge/selection`.
- **`challenge/iap` (Phone SMS Checkpoint):** Google bắt nhập số điện thoại nhận SMS. Bắt buộc fail-closed ngay lập tức, xóa profile tạm và kích hoạt đếm Circuit Breaker.

---

## 6. Quy Trình Đối Soát Tự Động 40 Proxy Farm Kibe & Phát Hiện Proxy Chưa Đăng Nhập Trong Ngày (Daily Untouched Proxy Audit — 2026-09-05)

### Bối Cảnh & Nhu Cầu
Mỗi ngày khi vận hành Farm Kibe (80 máy điện thoại tương ứng 40 proxy vật lý), cần xác định chính xác:
1. Những proxy/port nào trong ngày hôm nay đã có profile GPM Group 1 cập nhật/đăng nhập.
2. Chính xác những proxy/port nào chưa từng được nạp/đăng nhập hôm nay.
3. Tài khoản Gmail tương ứng trong kho là gì, trạng thái 2FA/mật khẩu ra sao để kích hoạt batch nạp tiếp.

### Thuật Toán & Kịch Bản Đối Soát Tự Động (O(1) Scan):
1. **Nguồn Dữ Liệu 40 Proxy (Source of Truth):**
   - File `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (Sheet `Proxy`):
     - 32 cổng Mobi 4G: `5101`..`5108`, `5111`..`5118`, `5121`..`5128`, `5131`..`5138` (Máy 1..32 & Máy 39..70).
     - 7 cổng MikroTik: `10001`..`10007` (Máy 33..37 & Máy 71..75, 77..80).
     - 1 cổng Khoalee: `khoalee.duckdns.org:16002` (Máy 38 & Máy 76).
2. **Truy Vấn Profile Đã Login Hôm Nay Trong GPM SQLite:**
   ```python
   conn = sqlite3.connect(r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db")
   cur = conn.cursor()
   cur.execute("SELECT Name, JsonData, CreatedAt, UpdatedAt FROM Profiles WHERE GroupId=1")
   # Lọc port từ JsonData['raw_proxy'] hoặc suffix '- <PORT>'
   # Kiểm tra today (YYYY-MM-DD) nằm trong CreatedAt hoặc UpdatedAt
   ```
3. **Phát Hiện Untouched Ports & Lọc Tài Khoản An Toàn:**
   - `untouched_ports = all_40_ports - logged_in_today_ports`.
   - Tra cứu số máy và tài khoản trong `master_gmail_manager.xlsx` (Sheet `Kibe_Farm_S7`) và `gmail_clean_v2.xlsx`.
   - **BỘ LỌC AN TOÀN BẮT BUỘC (User Invariant):**
     - BỎ QUA 100% tài khoản có recovery email là `khoaleemagic@gmail.com` (CẤM tạo profile, CẤM đăng nhập).
     - Bỏ qua các port/máy chỉ dùng Hotmail (ví dụ Máy 79, 80 trên port `10007` chỉ có Hotmail, không có Gmail cổ).
     - Ưu tiên tài khoản đã có sẵn 2FA Secret Key (ví dụ Máy 36) hoặc có thể nhận OTP recovery email qua IMAP `thanhdatbui1995@gmail.com` (ví dụ Máy 35).

