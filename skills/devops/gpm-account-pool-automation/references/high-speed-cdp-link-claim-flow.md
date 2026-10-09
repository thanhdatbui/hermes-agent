# High-Speed CDP Link Claiming Flow (Flash Offer / Mass Invite Activation)

## Bối cảnh & Vấn đề
- Khi nhận danh sách link ưu đãi (ví dụ Google One / AI Premium invite link `serviceactivation.google.com`) có thời gian sống ngắn hoặc bị giật hết trong vài phút (flash links).
- Sử dụng Selenium / giao diện đồ họa đầy đủ (GUI) của GPM khiến script chạy "ngọng", chậm (15-20s/profile do khởi động tiến trình, render UI, tải fingerprint phức tạp).
- Yêu cầu: Vừa giữ an toàn tài khoản (giữ trọn session/cookie/fingerprint của profile GPM thật), vừa đạt tốc độ xử lý cấp mili-giây (async CDP concurrency).

---

## Kiến trúc Tối ưu: GPM Local API + Async Playwright CDP

### 1. Cơ chế vận hành
1. **Khởi động Profile GPM siêu nhẹ**:
   - Gọi `GET /api/v3/profiles/start/{id}?win_scale=0.5` lấy `remote_debugging_address` (hoặc `wsUrl`).
   - Thời gian spawn: ~0.3 - 0.5s.
2. **Bắt tay trực tiếp qua Chrome DevTools Protocol (CDP)**:
   - Dùng `playwright.chromium.connect_over_cdp(f"http://{remote_debugging_address}")`.
   - Kết nối V8 Engine trực tiếp trong ~0.1 - 0.15s, bỏ qua hoàn toàn Selenium WebDriver.
3. **Điều hướng tinh gọn (`domcontentloaded`)**:
   - Dùng `wait_until="domcontentloaded"` thay vì `networkidle` để không bị nghẽn bởi tracking/media.
   - Inject click trực tiếp qua locator hoặc JS event khi button vừa xuất hiện.
4. **Đóng dọn dẹp profile an toàn**:
   - Gọi `GET /api/v3/profiles/close/{id}` giải phóng tài nguyên.

---

## Mẫu code chuẩn (Template)

```python
import asyncio
import aiohttp
from playwright.async_api import async_playwright

GPM_API = "http://127.0.0.1:19995/api/v3"

async def process_link(session, playwright, profile_id, link):
    # 1. Start profile
    start_url = f"{GPM_API}/profiles/start/{profile_id}?win_scale=0.5"
    async with session.get(start_url) as resp:
        res = await resp.json()
        remote_addr = res.get("data", {}).get("remote_debugging_address")
    
    if not remote_addr:
        return {"profile_id": profile_id, "status": "FAIL_START"}

    # 2. Connect CDP
    try:
        browser = await playwright.chromium.connect_over_cdp(f"http://{remote_addr}")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()

        # 3. Navigate & Click
        await page.goto(link, wait_until="domcontentloaded", timeout=12000)
        
        btn = page.locator('button:has-text("Tham gia"), button:has-text("Accept"), button:has-text("Bắt đầu")').first
        if await btn.is_visible(timeout=5000):
            await btn.click()
            status = "CLAIMED"
        else:
            status = "NO_BUTTON_OR_EXPIRED"
            
        await browser.close()
    except Exception as e:
        status = f"ERROR: {e}"
    finally:
        # 4. Close GPM profile
        async with session.get(f"{GPM_API}/profiles/close/{profile_id}"):
            pass

    return {"profile_id": profile_id, "status": status}
```

---

## Ưu thế so với các phương pháp khác
- **So với Selenium**: Nhanh gấp 5-10 lần, không bị nghẽn RAM do driver bridge.
- **So với Pure HTTP Request (cURL/aiohttp)**: Tránh được rủi ro Google checkpoint/revoke session do thiếu fingerprint/CSRF token phức tạp. Giữ 100% tính nguyên bản của session profile.
