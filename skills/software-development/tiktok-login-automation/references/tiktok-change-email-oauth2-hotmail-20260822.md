# TikTok Change Linked Email via Hotmail OAuth2 Token (2026-08-22)

## Context & Problem
Khi tài khoản TikTok đang đăng nhập trên máy có Gmail liên kết bị chết (Google Play Services báo "Yêu cầu đăng nhập", sync fail, hoặc bị quét "Xác nhận bạn không phải là rô-bốt"):
- Không thể nhận OTP gửi về Gmail cũ để đổi mật khẩu.
- Cần thay thế Gmail cũ bằng một tài khoản Hotmail mới có sẵn Token OAuth2 từ kho `gmail_clean_v2.xlsx` / `hotmail_input.txt`.

## TikTok Security Characteristics
1. **Không đòi hỏi mật khẩu TikTok hoặc OTP của email cũ** khi đổi email trên thiết bị tin cậy (đang đăng nhập sẵn):
   - Vào `Hồ sơ` -> Menu (`3 gạch`) -> `Cài đặt và quyền riêng tư` -> `Tài khoản` -> `Thông tin tài khoản` -> `Email` -> `Thay đổi email`.
   - Nhập email Hotmail mới -> Bấm `Tiếp tục`.
   - TikTok chỉ gửi mã xác nhận 6 số về **chính email Hotmail mới**.
2. **Quy tắc giảm rủi ro bảo mật (24h Cooldown Rule)**:
   - Sau khi đổi email thành công, hệ thống Risk Engine của TikTok giám sát tài khoản nhạy cảm trong vòng 24 giờ.
   - **CẤM** đổi mật khẩu TikTok ngay trong cùng phiên đổi email. Phải để tài khoản ngâm tối thiểu 24h rồi mới thực hiện đổi mật khẩu bằng OTP Hotmail.

## Automated OAuth2 Token Exchange & OTP Fetching
Hotmail Loại 2 từ `boxtaikhoan.com` (gói ID 60 - 393đ) có cấu trúc:
`mail|pass|refresh_token|client_id`

### Token Exchange Request
```python
import urllib.request, urllib.parse, json, imaplib, email, re

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
            for mid in reversed(msgs[0].split()[-5:]):
                r, d = imap.fetch(mid, "(RFC822)")
                msg = email.message_from_bytes(d[0][1])
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() in ("text/plain", "text/html"):
                            body += str(part.get_payload(decode=True))
                else:
                    body = str(msg.get_payload(decode=True))
                
                match = re.search(r"\b(\d{6})\b", body)
                if match and ("tiktok" in body.lower() or "mã" in body.lower() or "verification" in body.lower()):
                    imap.close()
                    imap.logout()
                    return match.group(1)
            imap.close()
            imap.logout()
        except Exception:
            pass
        time.sleep(3)
    return ""
```

## ATX-Agent XML-First Navigation (Port 7912)
1. **Tuyệt đối CẤM hardcode tọa độ**:
   - Dùng `dumpWindowHierarchy` qua ATX-Agent để lấy bounds động của `text="Nhập email"`, `text="Tiếp tục"`, `resource-id="qtf"` (ô nhập OTP), `text="Không, cảm ơn"` (popup khảo sát sau đổi email).
2. **Post-Change Verification**:
   - Xác nhận trong XML màn hình `Thông tin tài khoản` chứa text dạng `j***i@hotmail.com` hoặc popup `Đã thêm email`.
3. **Excel Workbook Synchronization**:
   - Cập nhật `taikhoan_dat_v2_updated .xlsx`: cột `GMAIL` = Hotmail mới, cột `PASS MAIL` = Pass Hotmail.
   - Thêm vào `gmail_clean_v2.xlsx`: Machine, Hotmail, Pass, Ngày tạo, Token OAuth2 (cột 9), Client ID (cột 10).
   - Xóa tài khoản khỏi `hotmail_input.txt`.

Script triển khai đầy đủ: `D:\Taadaa\tiktok-log-in\scripts\change_tiktok_email_flow.py`.
