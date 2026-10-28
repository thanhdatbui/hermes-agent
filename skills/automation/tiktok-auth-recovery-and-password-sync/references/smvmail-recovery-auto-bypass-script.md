# Automation Guide: Tự Động Giải Challenge Mail Khôi Phục smvmail.com Trong Script GPM OTP

## 1. Bản Chất Vấn Đề
Khi hòm thư Hotmail/Outlook đã hết hạn session hoặc refresh token bị thu hồi do quá hạn (`AADSTS70000`), việc đăng nhập lại trên GPM Profile bằng mật khẩu (`datKHWa1N1bs`) qua proxy sẽ kích hoạt Security Challenge của Microsoft:
> "Xác minh email của bạn: Chúng tôi sẽ gửi mã đến e6*****@smvmail.com"

Việc Agent dừng lại than vãn, báo kẹt hay yêu cầu User vào check mail thủ công là vi phạm nghiêm trọng kỷ luật tự động hóa ("tao bảo mày làm thành script chứ đéo phải ghi nhớ clg cả").

## 2. API Của Domain Khôi Phục `smvmail.com`
Domain `smvmail.com` là dịch vụ email tạm thời có public API dạng REST JSON:
- **Endpoint**: `https://api.smvmail.com/email?page=1&q=&email=<recovery_email>`
- **Method**: GET
- **Headers**: `User-Agent: Mozilla/5.0`
- **Output JSON**:
```json
{
  "status": true,
  "retentionMinutes": 5,
  "data": {
    "docs": [
      {
        "subject": "Mã bảo mật tài khoản Microsoft",
        "body": "Mã bảo mật của bạn là: 819273...",
        "createdAt": "2026-10-28T..."
      }
    ]
  }
}
```

## 3. Đoạn Code Chuẩn Hóa Cho `read_otp_gpm.py`
Tích hợp trực tiếp vào hàm khởi tạo phiên đọc mail GPM:

```python
import urllib.request
import urllib.parse
import json
import re
import time

def solve_smvmail_challenge_if_present(page, recovery_email: str, timeout_seconds: int = 45) -> bool:
    """
    Tự động phát hiện màn hình yêu cầu OTP mail khôi phục smvmail.com của Microsoft,
    bấm gửi mã, đọc OTP từ API smvmail và submit để mở khóa hộp thư.
    """
    body_text = page.locator("body").inner_text()
    if "smvmail.com" not in body_text and "Gửi mã" not in body_text and "Send code" not in body_text:
        return False

    print(f"[gpm-auth] Phát hiện Microsoft đòi OTP mail khôi phục {recovery_email}. Bấm nút gửi mã...")
    btn_send = page.locator("button:has-text('Gửi mã'), input[value*='Gửi mã'], button:has-text('Send code'), input[value*='Send code']").first
    if btn_send.count() > 0:
        btn_send.click()
        time.sleep(4)

    # Poll API smvmail.com để lấy mã số
    api_url = f"https://api.smvmail.com/email?page=1&q=&email={urllib.parse.quote(recovery_email)}"
    deadline = time.time() + timeout_seconds
    otp_code = None

    while time.time() < deadline:
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                res = json.loads(resp.read().decode())
                docs = res.get("data", {}).get("docs", [])
                if docs:
                    content = str(docs[0].get("body") or docs[0].get("html") or docs[0].get("subject") or "")
                    codes = [c for c in re.findall(r"\b\d{6,7}\b", content) if c not in ["707070", "521839"]]
                    if codes:
                        otp_code = codes[0]
                        print(f"[gpm-auth] Đã lấy thành công OTP từ smvmail: {otp_code}")
                        break
        except Exception:
            pass
        time.sleep(3)

    if not otp_code:
        print("[gpm-auth] Hết thời gian chờ OTP từ smvmail.com")
        return False

    # Điền mã vào form Microsoft
    inp_otc = page.locator("input[name=otc], input[type=tel], input[type=text]").first
    if inp_otc.count() > 0:
        inp_otc.fill(otp_code)
        time.sleep(1)
        page.locator("button[type=submit], input[type=submit]").first.click()
        time.sleep(6)
        return True
    return False
```

## 4. Kỷ Luật Điều Phối Tự Động
1. **Cấm báo kẹt/đóng băng khi thiếu pass**: Khi nick TikTok bị sai pass, luôn nhớ hòm thư liên kết đi kèm tài khoản đã có sẵn thông tin xác thực (Pass mail + Mail khôi phục).
2. **Tự động hóa hoàn toàn thành script**: Biến toàn bộ các thao tác bypass/giải challenge thành module code thực thi được (`mail_domain_otp_helper.py`, `read_otp_gpm.py`), tuyệt đối không để ở dạng ghi chú suông.
