# Khắc phục Giới hạn Lượt gọi Công cụ (Tool Budget Exhaustion) trong GPM CDP Testing

## Bối cảnh & Vấn đề
Khi thực hiện test đăng nhập Google hoặc các Gate kiểm tra trên profile GPMLogin (`gpm-account-pool-automation`), agent dễ bị cạn lượt gọi công cụ (`maximum number of tool-calling iterations reached`) nếu thăm dò lần lượt qua nhiều lệnh đơn lẻ:
1. `search_files` tìm script
2. `read_file` đọc logic đăng nhập
3. `terminal` curl/requests kiểm tra profile GPM
4. `terminal` viết script test
5. `terminal` thực thi test và chụp screenshot

## Mẫu giải pháp 1-Shot Runner (One-Shot Execution Pattern)
Thay vì chia nhỏ các bước khảo sát qua nhiều turn/tool calls, gom logic thực thi trực tiếp vào 1 script Python độc lập và gọi chạy ngay:

```python
import os, sys, time, requests
from playwright.sync_api import sync_playwright

GPM_BASE = "http://127.0.0.1:19995/api/v3"

def run_gate_check(profile_id: str, email: str, password: str, report_png: str):
    # 1. Start profile
    res = requests.get(f"{GPM_BASE}/profiles/start/{profile_id}").json()
    if not res.get("success"):
        raise RuntimeError(f"GPM start failed: {res}")
    
    cdp_addr = res["data"]["remote_debugging_address"]
    
    # 2. Connect CDP & execute
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://{cdp_addr}")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        
        # Test navigation & gate check
        page.goto("https://accounts.google.com", timeout=30000)
        # Login flow logic ...
        time.sleep(3)
        page.screenshot(path=report_png)
        
    # 3. Stop profile cleanly
    requests.get(f"{GPM_BASE}/profiles/stop/{profile_id}")
```

## Checklist thực hiện
- [ ] Truy vấn ID profile trực tiếp từ `http://127.0.0.1:19995/api/v3/profiles` trong cùng 1 lần gọi nếu chưa biết ID.
- [ ] Chạy thẳng script runner một bước duy nhất thay vì đọc tuần tự từng hàm phụ trợ trong repo.
- [ ] Luôn đảm bảo chụp screenshot nghiệm thu GATE lưu vào `reports/` trước khi tắt profile.
