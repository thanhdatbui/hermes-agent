# Chuẩn Tạo & Khởi Chạy Profile GPM (GPMLogin Local API v3)

## 1. Nguyên tắc cốt lõi: CẤM MỞ PLAYWRIGHT TRỰC TIẾP TRÊN PC
- **Bẫy "Tại sao lại mở gpm = playwright gì đó"**:
  - Không tự viết script Playwright launch persistent context thủ công trên PC với proxy để vào Google / ChatGPT.
  - Các trang này sử dụng Cloudflare Turnstile và Bot Detection ngặt nghèo; mở Playwright độc lập không có vân tay hoàn chỉnh của GPM sẽ bị chặn ngay ở màn hình login.
- **Kiến trúc chuẩn của Farm**:
  - Toàn bộ profile trình duyệt được quản lý qua **GPMLogin Local API v3** tại `http://127.0.0.1:19995/api/v3`.
  - Module quản lý chuẩn: `D:/Taadaa/GPM auto/src/gpm_client.py` (`GPMClient`).

## 2. Quy trình chuẩn 3 bước

### Bước 1: Tạo Profile qua Local API
```python
import sys
sys.path.insert(0, r"D:/Taadaa/GPM auto/src")
from gpm_client import GPMClient

client = GPMClient(base_url="http://127.0.0.1:19995/api/v3")
# raw_proxy format: host:port:user:pass
res = client.create_profile(
    name="42 - thaonhatzodf747@gmail.com - 5104",
    raw_proxy="test.taadaa.click:5104:mobi4:TaadaaMobi#2026!",
    group_id=10,  # Group Google_Live_Ready
    browser_type="Chrome"
)
profile_id = res["data"]["id"]
```

### Bước 2: Start Profile lấy cổng CDP
```python
start_res = client.start_profile(profile_id)
# Trả về remote_debugging_address, ví dụ: 127.0.0.1:51391
remote_addr = start_res["data"]["remote_debugging_address"]
```

### Bước 3: Playwright chỉ kết nối qua CDP
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # Kết nối trực tiếp vào phiên GPM Chrome core 142 đã có sẵn fingerprint sạch
    browser = p.chromium.connect_over_cdp(f"http://{remote_addr}")
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://chatgpt.com/auth/login")
    # Tự động hóa các thao tác web...
    browser.close()

# Cuối cùng luôn gọi stop profile dọn dẹp
client.stop_profile(profile_id)
```
