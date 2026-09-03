# TikTok Change Linked Email Flow (Thay đổi email liên kết TikTok)

## 1. Cơ chế hoạt động (Behavior & Security Rules)
Khi đổi email liên kết của tài khoản TikTok trên thiết bị tin cậy (đang đăng nhập sẵn trong app):
1. **Không đòi hỏi mật khẩu tài khoản TikTok hiện tại.**
2. **Không đòi OTP của email cũ (kể cả khi email cũ là Gmail đã bị khóa/die/captcha).**
3. **Chỉ yêu cầu xác thực email mới:** TikTok gửi mã OTP gồm 6 chữ số trực tiếp về hòm thư mới được nhập.
4. Sau khi nhập đúng 6 chữ số OTP từ hòm thư mới, TikTok tự động chuyển email liên kết chính sang email mới.

## 2. Các bước điều hướng UI (UI Navigation)
1. **Mở TikTok** -> Chuyển sang tab **Hồ sơ** (`com.ss.android.ugc.trill:id/o76` / góc dưới bên phải).
2. **Mở Menu 3 gạch ngang** (góc trên bên phải, `bounds=[936,84][1080,228]`).
3. **Chọn `Cài đặt và quyền riêng tư`** (nằm dưới cùng menu, hoặc `bounds=[204,1176][1038,1320]`).
4. **Chọn `Tài khoản`** -> **Chọn `Thông tin tài khoản`**.
5. **Chọn mục `Email`** -> Xuất hiện popup dialog xác nhận.
6. **Chọn nút `Thay đổi email`** -> Mở màn hình `Nhập email`.
7. Nhập địa chỉ Hotmail/Outlook mới và bấm nút **`Tiếp tục`** (`com.ss.android.ugc.trill:id/ffe`).
8. TikTok chuyển sang màn hình **`Xác minh email` (Nhập mã gồm 6 chữ số)**.

## 3. Lấy OTP Hotmail tự động qua Microsoft XOAUTH2 IMAP
Hotmail/Outlook Loại 2 có sẵn `refresh_token` và `client_id`:
```python
import urllib.request, urllib.parse, json, imaplib, email, re, time

def get_hotmail_otp(email_addr: str, refresh_token: str, client_id: str, timeout: int = 60) -> str:
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "https://outlook.office.com/IMAP.AccessAsUser.All https://outlook.office.com/POP.AccessAsUser.All offline_access"
    }).encode()
    
    req = urllib.request.Request(token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    res = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
    access_token = res["access_token"]
    
    def generate_auth_string(user, token):
        return f"user={user}\x01auth=Bearer {token}\x01\x01"

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            imap = imaplib.IMAP4_SSL("outlook.office365.com", 993)
            imap.authenticate("XOAUTH2", lambda x: generate_auth_string(email_addr, access_token).encode())
            imap.select("INBOX")
            status, msgs = imap.search(None, "ALL")
            msg_ids = msgs[0].split()
            for mid in reversed(msg_ids[-5:]):
                r, d = imap.fetch(mid, "(RFC822)")
                msg = email.message_from_bytes(d[0][1])
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() in ("text/plain", "text/html"):
                            body += str(part.get_payload(decode=True))
                else:
                    body = str(msg.get_payload(decode=True))
                
                # Bắt mã OTP 6 số từ TikTok
                match = re.search(r"\b(\d{6})\b", body)
                if match and ("tiktok" in body.lower() or "verification" in body.lower() or "mã" in body.lower()):
                    otp = match.group(1)
                    imap.close()
                    imap.logout()
                    return otp
            imap.close()
            imap.logout()
        except Exception:
            pass
        time.sleep(3)
    return ""
```

## 4. Điền OTP & Xử lý hậu kiểm
1. Gửi OTP bằng `adb shell input text <otp>`.
2. Khi hiện popup gợi ý cập nhật *"Bạn muốn nhận nội dung thịnh hành...?"*: bấm **`Không, cảm ơn`** (`com.ss.android.ugc.trill:id/dec`).
3. Verify lại màn hình `Thông tin tài khoản`: nhãn email đã chuyển sang định dạng masked của email mới (`j***i@hotmail.com`).
4. **Cập nhật Excel & Kho:**
   - Cập nhật cột `GMAIL` và `PASS MAIL` trong `taikhoan_dat_v2_updated .xlsx`.
   - Lưu thông tin tài khoản Hotmail mới vào `gmail_clean_v2.xlsx`.
