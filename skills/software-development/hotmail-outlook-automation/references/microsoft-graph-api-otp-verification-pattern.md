# Microsoft Graph API OTP Verification Pattern

Pattern trích xuất OTP tự động cho Hotmail/Outlook qua Microsoft Graph API (dùng cho đổi email TikTok, login verify, v.v.):

## 1. Refresh Token -> Access Token
Endpoint: `POST https://login.live.com/oauth20_token.srf`
```python
import requests

token_url = "https://login.live.com/oauth20_token.srf"
data = {
    "client_id": client_id,
    "grant_type": "refresh_token",
    "refresh_token": refresh_token
}
r = requests.post(token_url, data=data, timeout=10)
acc_token = r.json()["access_token"]
```

## 2. Polling Messages
Endpoint: `GET https://graph.microsoft.com/v1.0/me/messages?$top=10&$orderby=receivedDateTime desc`
Header: `Authorization: Bearer <access_token>`

```python
import re, time

def get_graph_otp(client_id, refresh_token, max_wait=90):
    t0 = time.time()
    while time.time() - t0 < max_wait:
        # Refresh access token & fetch messages
        ...
        for m in msgs:
            subject = m.get("subject", "")
            body = m.get("bodyPreview", "") + " " + m.get("body", {}).get("content", "")
            if any(k in (subject + body).lower() for k in ["tiktok", "mã", "verification", "code"]):
                codes = re.findall(r"\b(\d{6})\b", subject + " " + body)
                if codes:
                    return codes[0]
        time.sleep(5)
    return None
```

## 3. Python Runtime Pitfall
- Tránh chạy qua `D:/Taadaa/python-envs/automation/Scripts/python.exe` nếu bị stall/timeout I/O.
- Dùng Hermes venv python (`which python`) có sẵn `requests`, `openpyxl`, `pyotp`.
