# Chi Tiết Kỹ Thuật: Flow Đổi Email TikTok & Xử Lý Sự Cố

## 1. Bản Đồ Giao Diện (UI Hierarchy Map) Của Mục Cài Đặt TikTok

```
[Profile Root]
  └── Header menu (icon 3 gạch: [1005, 150])
        └── Bottom Sheet: "Cài đặt và quyền riêng tư" (bounds [621, 1248])
              └── Menu List:
                    ├── "Tài khoản" (vị trí thay đổi tùy độ phân giải màn hình)
                    │     └── Account Detail Subpage:
                    │           ├── "Thông tin tài khoản" (Account information)
                    │           │     ├── "Số điện thoại"
                    │           │     ├── "Email" -> Mở Bottom Sheet "Thay đổi email"
                    │           │     └── "Ngày sinh"
                    │           ├── "Mật khẩu"
                    │           ├── "Khóa bảo mật"
                    │           └── [NGUY HIỂM - ĐÁY MÀN HÌNH]:
                    │                 "Hủy kích hoạt hoặc xóa tài khoản"
                    └── "Quyền riêng tư", "Bảo mật", ...
```

## 2. Vì Sao Tuyệt Đối Cấm Click Tọa Độ [540, 1810]?
1. Khi máy ở trang `Cài đặt và quyền riêng tư`, mục `Tài khoản` thường nằm ở `y ~ 300-600`.
2. Nếu lệnh `click [540, 1810]` được gửi khi app đã vô tình vào trang `Tài khoản`:
   - Tọa độ `y = 1810` chính là dòng `Hủy kích hoạt hoặc xóa tài khoản`.
   - App sẽ lập tức navigate vào màn hình `Xóa hoặc hủy kích hoạt?`.
3. Giải pháp chuẩn xác bằng Python:
   ```python
   def click_by_text(base_url, text_needle):
       nodes = dump_hierarchy(base_url)
       for n in nodes:
           t = (n.get('text') or n.get('desc') or '').strip()
           if text_needle.lower() in t.lower():
               cx = (n['bounds'][0] + n['bounds'][2]) // 2
               cy = (n['bounds'][1] + n['bounds'][3]) // 2
               atx_rpc(base_url, 'click', [cx, cy])
               return True
       return False
   ```

## 3. Quy Trình Bóc OTP Hotmail Tự Động Qua Microsoft Graph API
```python
def fetch_hotmail_otp(email, refresh_token, client_id, max_retries=15):
    token_url = 'https://login.live.com/oauth20_token.srf'
    post_data = urllib.parse.urlencode({
        'client_id': client_id,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }).encode('utf-8')
    req = urllib.request.Request(token_url, data=post_data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    res = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
    access_token = res['access_token']

    graph_url = 'https://graph.microsoft.com/v1.0/me/messages?$top=5'
    for _ in range(max_retries):
        req_msgs = urllib.request.Request(graph_url, headers={'Authorization': f'Bearer {access_token}'})
        msgs_res = json.loads(urllib.request.urlopen(req_msgs, timeout=10).read().decode('utf-8'))
        for msg in msgs_res.get('value', []):
            subj = msg.get('subject', '')
            sender = msg.get('from', {}).get('emailAddress', {}).get('address', '')
            if 'tiktok' in sender.lower() or 'tiktok' in subj.lower():
                codes = re.findall(r'\b(\d{6})\b', subj + ' ' + msg.get('bodyPreview', ''))
                if codes:
                    return codes[0]
        time.sleep(2)
    return None
```
