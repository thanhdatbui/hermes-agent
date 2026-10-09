# Benchmark & Concurrency Pattern: GPMLogin Local API v3 + Playwright CDP

Tài liệu này ghi lại mẫu chuẩn để benchmark tốc độ duyệt link, cào dữ liệu hoặc kích hoạt (claim link) trên quy mô hàng loạt profile GPMLogin qua Playwright CDP.

## 1. Cơ chế kết nối và quản lý vòng đời (Lifecycle Discipline)

- **Port Local API GPMLogin v3:** `http://127.0.0.1:19995`.
- **Khởi động profile:** `GET http://127.0.0.1:19995/api/v3/profiles/start/{id}`
  - Response JSON:
    ```json
    {
      "success": true,
      "data": {
        "profile_id": "...",
        "browser_location": "...",
        "remote_debugging_address": "127.0.0.1:63153",
        "driver_path": "...",
        "process_id": 67108
      },
      "message": "OK"
    }
    ```
- **Playwright CDP Connection:**
  ```python
  from playwright.async_api import async_playwright

  async with async_playwright() as p:
    browser = await p.chromium.connect_over_cdp(f"http://{cdp_addr}")
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
    # Xử lý logic...
    await browser.close()
```
- **Đóng profile (BẮT BUỘC):** `GET http://127.0.0.1:19995/api/v3/profiles/stop/{id}`
  - Luôn bọc trong khối `finally` để giải phóng RAM, cổng debug và DeviceLock kể cả khi task gặp Exception/Timeout.

## 2. Benchmark Concurrency & Semaphore

Chạy đồng thời quá nhiều Chrome profile cùng lúc (ví dụ >10) trên máy cá nhân dễ gây spike CPU/RAM hoặc nghẽn băng thông proxy mobile (test.taadaa.click).
Khuyến nghị dùng `asyncio.Semaphore(3..5)` để giới hạn số profile mở cùng một thời điểm:

```python
import asyncio
import json
import time
import urllib.request
from playwright.async_api import async_playwright


async def run_worker(profile_id, link, semaphore, playwright_instance):
  async with semaphore:
    t0 = time.time()
    # 1. Start GPM
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(
        None,
        lambda: json.loads(
            urllib.request.urlopen(
                f"http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}"
            )
            .read()
            .decode()
        ),
    )
    cdp_addr = res["data"]["remote_debugging_address"]

    browser = None
    try:
      browser = await playwright_instance.chromium.connect_over_cdp(
          f"http://{cdp_addr}"
      )
      page = browser.contexts[0].pages[0]
      await page.goto(link, wait_until="domcontentloaded", timeout=30000)
      title = await page.title()
      return {"profile_id": profile_id, "duration": time.time() - t0, "title": title}
    finally:
      if browser:
        await browser.close()
      await loop.run_in_executor(
          None,
          lambda: urllib.request.urlopen(
              f"http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}"
          ),
      )
```

## 3. Pitfalls & Tránh cạm bẫy

1. **Sai path API:** Endpoint mở profile là `/api/v3/profiles/start/{id}`, KHÔNG PHẢI `/api/v3/profiles/start?profile_id={id}` (dạng query param sẽ trả về `PROFILE_NOT_FOUND`).
2. **Kiểm tra phiên bản Playwright:** Trong Python, package `playwright` không expose `playwright.__version__` ở root module (`AttributeError: module 'playwright' has no attribute '__version__'`). Để kiểm tra phiên bản từ code, dùng `import importlib.metadata; importlib.metadata.version('playwright')`.
3. **Hairpin NAT:** Nếu profile dùng proxy domain nội bộ trỏ về chính IP ngoài của router, preflight của GPM có thể báo lỗi proxy. Đối với proxy 4G ngoài (`test.taadaa.click`) thì kết nối bình thường.
4. **Session Google Redirect:** Mở link dịch vụ Google (`serviceactivation.google.com`) trên profile chưa có cookie/session hoặc hết hạn sẽ redirect ngay sang `accounts.google.com/v3/signin/identifier?flowName=GlifWebSignIn`. Cần kiểm tra URL redirect hoặc `page.title()` để phân loại trạng thái phiên.
