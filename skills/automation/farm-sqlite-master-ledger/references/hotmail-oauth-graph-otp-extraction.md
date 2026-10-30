# Hotmail/Outlook OAuth Graph API OTP Extraction

Chi tiết kỹ thuật và mã mẫu trích xuất mã OTP 6 số tự động từ kho 881 mailboxes trong `D:/Taadaa/data/farm_master.db`.

## 1. Bản chất kỹ thuật
- Khi đăng nhập web Outlook bằng password thông thường trên IP lạ / proxy, Microsoft sẽ chặn checkpoint yêu cầu xác minh qua email khôi phục (`ca*****@fviainboxes.com`).
- Toàn bộ mailboxes trong bảng `mailboxes` của Farm đã được ủy quyền sẵn `oauth_refresh_token`.
- Điểm cuối token: `https://login.live.com/oauth20_token.srf`
- Client ID mặc định của Outlook Web/Consumer app: `0000000040170455` (hoặc lấy từ cột `oauth_client_id` nếu có).

## 2. Mã nguồn chuẩn Python trích xuất OTP

```python
import sqlite3
import urllib.request
import urllib.parse
import json
import re

def fetch_otp_from_farm_mailbox(email, folder='inbox'):
    conn = sqlite3.connect('D:/Taadaa/data/farm_master.db')
    cur = conn.cursor()
    cur.execute('SELECT oauth_refresh_token, oauth_client_id FROM mailboxes WHERE email = ?', (email,))
    row = cur.fetchone()
    conn.close()
    
    if not row or not row[0]:
        raise ValueError(f"Mailbox {email} không có oauth_refresh_token trong farm_master.db")
        
    r_token, c_id = row
    client_id = c_id if c_id else '0000000040170455'
    
    # 1. Đổi refresh token lấy access token mới
    url_token = 'https://login.live.com/oauth20_token.srf'
    payload = {
        'client_id': client_id,
        'grant_type': 'refresh_token',
        'refresh_token': r_token
    }
    req = urllib.request.Request(
        url_token,
        data=urllib.parse.urlencode(payload).encode('utf-8'),
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
    access_token = resp['access_token']
    
    # 2. Truy vấn tin nhắn mới nhất qua Microsoft Graph
    # Lưu ý: Kiểm tra folder 'inbox', nếu không thấy cần fallback sang 'junkemail'
    for fld in [folder, 'junkemail'] if folder == 'inbox' else [folder]:
        url_mail = f'https://graph.microsoft.com/v1.0/me/mailFolders/{fld}/messages?$top=3'
        req_mail = urllib.request.Request(url_mail, headers={'Authorization': f'Bearer {access_token}'})
        try:
            res_mail = json.loads(urllib.request.urlopen(req_mail, timeout=10).read().decode('utf-8'))
            msgs = res_mail.get('value', [])
            for m in msgs:
                subject = m.get('subject', '')
                body = m.get('bodyPreview', '')
                codes = re.findall(r'\b\d{6}\b', body) or re.findall(r'\b\d{6}\b', subject)
                if codes:
                    return codes[0]
        except Exception:
            continue
            
    return None
```

## 3. Quy tắc vận hành
- **Tuyệt đối không dừng lại hỏi xin người dùng email cá nhân** khi đang có hơn 880 hòm thư sẵn sàng nhận OTP.
- **Tự động hóa hoàn toàn:** Khi dịch vụ (Meta, TikTok, OpenAI) gửi OTP, lập tức query Graph API đọc mail và submit tiếp tục luồng ngay.
