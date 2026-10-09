# Extension VPN Headless Injection & Direct Connection Workflow in GPM

## Bối cảnh
Khi cần IP US/quốc tế sạch để đăng ký hoặc truy cập các dịch vụ AI nước ngoài (như Meta Muse AI, Perplexity, Claude, ChatGPT...) mà:
1. Không có sẵn proxy US dạng `ip:port:user:pass`.
2. Chrome Web Store dialog bấm "Thêm vào Chrome" bị OS/browser native prompt chặn (không thể click qua CDP/Playwright DOM thông thường).

## Kỹ thuật tải CRX và giải nén nạp Extension vào GPM

### 1. Tải CRX trực tiếp từ Google Update API
Không cần mở UI Chrome Web Store, lấy Extension ID (ví dụ Touch VPN là `bihmplhobchoageeokmgbdihknkjbknd`):
```python
import urllib.request

ext_id = 'bihmplhobchoageeokmgbdihknkjbknd'
crx_url = f'https://clients2.google.com/service/update2/crx?response=redirect&prodversion=120.0&acceptformat=crx2,crx3&x=id%3D{ext_id}%26uc'
urllib.request.urlretrieve(crx_url, 'extension.crx')
```

### 2. Giải nén CRX (Unpack Header CRX3/CRX2 sang ZIP)
File `.crx` có header binary (Cr24), unpack header để lấy định dạng `.zip`:
```python
import struct, zipfile

with open('extension.crx', 'rb') as f:
    data = f.read()

# Header CRX3: Magic b'Cr24' (4 bytes), Version (4 bytes), Header length (4 bytes)
header_len = struct.unpack('<I', data[8:12])[0]
zip_data = data[12 + header_len:]

with open('extension.zip', 'wb') as f:
    f.write(zip_data)

with zipfile.ZipFile('extension.zip', 'r') as zip_ref:
    zip_ref.extractall('C:/path/to/extracted_ext')
```

### 3. Nạp Extension vào Chrome GPM bằng `--load-extension`
GPM khởi chạy Chrome bằng script core riêng. Khi profile GPM được tạo, khởi chạy Chrome với tham số:
```bash
--load-extension="C:/path/to/extracted_ext,C:/path/to/gpm_clipboard_ext"
```

### 4. Điều khiển Extension UI & Kết nối VPN tự động qua CDP
Extension popup/panel thực chất là trang HTML chạy trong extension origin:
* Mở trang panel: `chrome-extension://<ext_id>/panel/index.html` (hoặc `popup.html` tùy manifest).
* Chọn location (ví dụ United States) và trigger kết nối trực tiếp trong background context:
```python
# Gọi hàm nội tại của extension hoặc click nút Connect trên panel page
page.goto('chrome-extension://bihmplhobchoageeokmgbdihknkjbknd/panel/index.html')
# Chọn server
page.click('#location-select')
page.click('[data-location="us-new-york"]')
# Trigger connect
page.evaluate('window.app.startConnection()')  # hoặc page.click('#connect-button')
```

### 5. Kiểm tra kết nối (Verification Gate)
* Truy cập `https://ipinfo.io/json` để kiểm tra IP và Geolocation (`country: "US"`).
* Chụp ảnh snapshot verification trước khi truy cập dịch vụ mục tiêu.
