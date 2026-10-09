# Bẫy Vòng Lặp "Thử Cách Khác" Trên `challenge/ootp` & Re-Auth Challenge Khi Kích Hoạt 2SV Authenticator

## 1. Bẫy Vòng Lặp Vô Tận "Thử Cách Khác" (Try Another Way Loop) Trên Trang Nhập Mã Bảo Mật 10 Số

### Triệu chứng:
- Script chọn thành công tuỳ chọn "Mã bảo mật" (Security code) từ `challenge/selection`.
- Trình duyệt điều hướng tới `https://accounts.google.com/v3/signin/challenge/ootp` (trang nhập 10 chữ số từ cài đặt thiết bị Samsung S7).
- Script không điền mã vào ô `code_inp` mà liên tục in log:
  ```
  Step N: URL = .../signin/challenge/ootp | Title = Xác minh danh tính của bạn...
  Google Prompt / Identity challenge detected. Looking for 'Try another way'...
  Step N+1: URL = .../signin/challenge/selection ...
  Selecting Security Code option...
  ```
- Quá trình lặp đi lặp lại 15 bước cho đến khi timeout, sau đó redirect về `google.com/account/about` và báo `FAILED`.

### Nguyên nhân cốt lõi:
1. Google đặt tiêu đề (Title & Heading) cho **TẤT CẢ** các trang challenge xác minh (`challenge/selection`, `challenge/ootp`, `challenge/pwd`) là:
   `"Xác minh danh tính của bạn Để giữ an toàn cho tài khoản của bạn, Google muốn đảm bảo rằng bạn chính là người đang cố đăng nhập."`
2. Nếu điều kiện phát hiện Google Prompt để bấm *"Thử cách khác"* (`Try another way`) chứa cụm từ `"xác minh danh tính"`:
   ```python
   # LỖI NGUY HIỂM:
   if "challenge/dp" in current_url or any(kw in body_text for kw in [..., "xác minh danh tính"]):
       try_another = page.locator('button:has-text("Thử cách khác"), a:has-text("Thử cách khác")')
       if try_another.is_visible():
           try_another.click() # Bấm quay ngược về selection!
           continue
   ```
3. Khi ở trang `challenge/ootp`, ở dưới chân trang luôn có một liên kết *"Thử cách khác"* (để người dùng đổi phương thức nếu không có điện thoại). Logic trên nhìn thấy chữ "xác minh danh tính" và nhìn thấy nút "Thử cách khác", lập tức click ngay khiến trang quay ngược lại menu chọn phương thức `challenge/selection`, tạo thành vòng lặp vô tận.

### Giải pháp khắc phục chuẩn:
1. **Loại bỏ hoàn toàn từ khóa `"xác minh danh tính"` khỏi điều kiện bấm "Thử cách khác"**:
   Chỉ bấm "Thử cách khác" khi URL thực sự chứa `"challenge/dp"` HOẶC body_text chứa các chuỗi đặc thù của Google Prompt điện thoại:
   `["kiểm tra điện thoại", "check your phone", "tap yes", "chạm vào có", "xác nhận trên điện thoại"]`.
2. **Đảo thứ tự kiểm tra: Quét ô nhập mã TRƯỚC khối "Thử cách khác"**:
   Khi trang đã render ô nhập mã bảo mật (`input[type="tel"]`, `input#security-code-input`, `input[name="code"]`) hoặc URL là `challenge/ootp`, ưu tiên lấy mã từ S7 và submit ngay, tuyệt đối không kiểm tra nút "Thử cách khác".

---

## 2. Re-Auth Challenge Khi Điều Hướng Đến Trang Thiết Lập 2FA Authenticator

### Triệu chứng:
- Tài khoản đã đăng nhập thành công vào trang chủ `myaccount.google.com`.
- Khi script mở URL `https://myaccount.google.com/two-step-verification/authenticator`, Google không hiện nút *"Thiết lập"* (*Set up*) mà redirect sang:
  `https://accounts.google.com/v3/signin/challenge/dp?continue=https://myaccount.google.com/two-step-verification/authenticator...`
- Script log:
  ```
  URL at 2SV Authenticator page: https://accounts.google.com/v3/signin/challenge/dp...
  No Setup button or Already Active indicator found.
  Login succeeded but 2FA failed: UNKNOWN_UI
  ```

### Nguyên nhân:
- Để truy cập vào các cài đặt bảo mật nhạy cảm (như 2SV Authenticator), Google yêu cầu xác thực lại danh tính (Re-authentication) bằng Google Prompt hoặc Password.
- Hàm `setup_google_authenticator_2fa` cũ chỉ xử lý `challenge/pwd` và `challenge/recaptcha`, không xử lý `challenge/dp`.

### Giải pháp:
Trong vòng lặp xử lý Re-auth của `setup_google_authenticator_2fa`:
1. Bổ sung kiểm tra `challenge/dp` với **bộ chọn rộng** (quét cả `div[role="button"]`, `span` thay vì chỉ `button`/`a`):
   ```python
   if "challenge/dp" in page.url.lower() or any(kw in body_txt for kw in ["kiểm tra điện thoại", "check your phone", "tap yes", "chạm vào có"]):
       logger.info("2SV Re-auth Google Prompt detected. Clicking Try another way...")
       try_another = page.locator('button:has-text("Thử cách khác"), button:has-text("Try another way"), a:has-text("Thử cách khác"), a:has-text("Try another way"), div[role="button"]:has-text("Thử cách khác"), div[role="button"]:has-text("Try another way"), span:has-text("Thử cách khác"), span:has-text("Try another way")')
       if try_another.count() > 0 and try_another.first.is_visible():
           try_another.first.click()
           time.sleep(3)
           continue
   ```
2. Nếu trang chuyển sang menu lựa chọn hoặc nhập mã:
   - Ưu tiên chọn Authenticator (nếu tài khoản đã có TOTP secret).
   - Hoặc chọn Mã bảo mật (Security Code từ S7 qua ADB `get_s7_security_code`).
   - Hoặc OTP Email khôi phục (`thanhdatbui1995@gmail.com`).
3. Sau khi Re-auth thành công, Google tự động chuyển tiếp về trang thiết lập Authenticator để trích xuất Secret Key.

---

## 4. Fallback "Thử Cách Khác" Khi S7 Không Lấy Được Mã Bảo Mật Trên `challenge/ootp`

### Triệu chứng:
Khi gặp `challenge/ootp` ở bước login hoặc re-auth, script gọi `get_s7_security_code(machine_id, serial, email)`. Nếu S7 bị lag adb, khóa màn hình hoặc không tìm thấy tài khoản trong danh sách Google Settings, hàm trả về `None`.
Nếu không có nhánh xử lý khi `s7_c is None`, ở vòng lặp tiếp theo Google vẫn ở URL `challenge/ootp`, script lại tiếp tục gọi `get_s7_security_code`. Mỗi lần gọi tốn ~25 giây (acquire lock, wake screen, dump UI nhiều lần). Sau 10-15 bước, tổng thời gian chờ lên tới 250-375 giây, gây cạn kiệt timeout của batch runner (lỗi timeout 600s của terminal) và chặn đứng tất cả tài khoản tiếp theo (như case Máy 61 chặn Máy 64).

### Giải pháp chuẩn:
1. Giới hạn số lần thử lấy S7 Security Code (tối đa 1-2 lần).
2. Nếu không lấy được mã (`s7_c is None`), **bắt buộc click ngay nút "Thử cách khác" (`Try another way`)** trên trang `challenge/ootp` để chuyển sang `challenge/selection`:
   ```python
   if "challenge/ootp" in current_url and account.get("serial"):
       logger.info(f"[M{machine_id:02d} | {email}] challenge/ootp detected! Getting S7 Security Code...")
       s7_c = get_s7_security_code(machine_id, account["serial"], email)
       if s7_c:
           logger.info(f"[M{machine_id:02d} | {email}] Submitting S7 code: {s7_c}...")
           code_inp.first.fill(s7_c)
           time.sleep(1)
           page.keyboard.press("Enter")
           time.sleep(5)
           continue
       else:
           logger.info(f"[M{machine_id:02d} | {email}] S7 security code not found. Clicking Try another way...")
           try_another = page.locator('button:has-text("Thử cách khác"), button:has-text("Try another way"), a:has-text("Thử cách khác"), a:has-text("Try another way"), div[role="button"]:has-text("Thử cách khác")')
           if try_another.count() > 0 and try_another.first.is_visible():
               try_another.first.click()
               time.sleep(3)
               continue
   ```
3. Sau khi chuyển sang `challenge/selection`, script chọn *"Nhận mã xác minh tại email khôi phục"* (`thanhdatbui1995@gmail.com`) và poll OTP qua IMAP, giải phóng hoàn toàn việc phụ thuộc vào thiết bị S7.

---

## 3. Pitfall: Lỗi UnicodeEncodeError Trong IMAP Search Của Python `imaplib`

### Triệu chứng:
Khi viết script poll OTP từ `thanhdatbui1995@gmail.com`:
```python
imap.search('utf-8', 'SUBJECT', 'xác minh')
# hoặc
imap.search(None, '(SUBJECT "xác minh")')
```
Python ném exception làm crash worker:
```
UnicodeEncodeError: 'ascii' codec can't encode character '\xe1' in position ...: ordinal not in range(128)
```

### Nguyên nhân:
Thư viện `imaplib` trong Python CPython chuẩn vẫn mã hóa các arguments của lệnh `SEARCH` bằng ASCII qua `_simple_command` trước khi gửi qua socket, không hỗ trợ string Unicode trực tiếp kể cả khi truyền charset UTF-8 nếu argument là str có chứa ký tự ngoài dải 128.

### Giải pháp khắc phục:
Chỉ tìm kiếm bằng các từ khóa/tiêu chí hoàn toàn ASCII:
```python
# 1. Tìm theo ngày (SINCE) và Sender thuần ASCII:
typ, data = imap.search(None, 'SINCE', since_date) # e.g. "05-Sep-2026"
# hoặc
typ, data = imap.search(None, '(FROM "accounts.google.com")')

# 2. Sau khi fetch email MIME, decode header và lọc regex trong bộ nhớ Python:
subj = str(email.header.make_header(email.header.decode_header(msg.get("Subject", ""))))
if "cảnh báo bảo mật" in subj.lower() or "security alert" in subj.lower():
    continue # bỏ qua email cảnh báo
match = re.search(r"(?<!\d)(\d{6})(?!\d)", subj + " " + body)
if match and match.group(1) != "000000":
    return match.group(1)
```
- Không bao giờ gửi chuỗi Unicode có dấu vào `imap.search()`. Mọi phép lọc tiếng Việt phải diễn ra ở Python level sau khi đã decode RFC2047 headers.
