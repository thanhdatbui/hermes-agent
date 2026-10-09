# Dynamic Per-Context Proxy & reCAPTCHA Handling over Chrome CDP

## Context & Problem
When accessing websites with strict firewalls, WAF, or regional ISP blocks (such as Vietnamese government portals `*.gov.vn`, `muasamcong.mpi.gov.vn`), direct connections or default headless browser instances may face:
- `ERR_CONNECTION_RESET` or SSL handshake timeout (`_ssl.c:999`) on certain ISP routes.
- WAF bot-challenge or Cloudflare blocking headless user agents.
- Need for proxy routing (e.g. Cloudflare WARP local proxy `socks5://127.0.0.1:40000` or commercial SOCKS5).

**Anti-Pattern:** Restarting the user's Chrome with `--proxy-server` kills all active tabs, disrupts logged-in sessions, and affects all open web apps.

## Solution: CDP `Target.createBrowserContext` with Dynamic Proxy
Chrome DevTools Protocol allows creating an isolated `BrowserContext` with its own dedicated proxy server on the fly, without modifying system proxy settings or restarting Chrome:

```python
import asyncio, sys, base64, urllib.parse, json
# Using zero-dep cdp_call from scripts/cdp_eval.py

async def open_proxied_tab(ws_browser_url, target_url, proxy="socks5://127.0.0.1:40000"):
    # 1. Create isolated context with proxy
    ctx_res = await cdp_call(ws_browser_url, 'Target.createBrowserContext', {
        'proxyServer': proxy
    })
    ctx_id = ctx_res['result']['browserContextId']

    # 2. Create tab inside the proxied context
    target_res = await cdp_call(ws_browser_url, 'Target.createTarget', {
        'url': target_url,
        'browserContextId': ctx_id
    })
    target_id = target_res['result']['targetId']
    ws_page = f"ws://127.0.0.1:9222/devtools/page/{target_id}"

    return ctx_id, target_id, ws_page
```

### Advantages:
1. Zero disruption to user's main Chrome window and existing tabs.
2. Completely isolates cookies and network traffic for the task.
3. Automatically leverages existing local proxies (WARP port 40000, 9Router, etc.).

---

## reCAPTCHA v2 Checkbox Handling via CDP

When a web form presents Google reCAPTCHA v2 checkbox:
1. Locate the anchor iframe:
   ```javascript
   const iframe = document.querySelector('iframe[title="reCAPTCHA"]');
   const rect = iframe.getBoundingClientRect();
   // Checkbox relative center is at (+28px, +37px)
   const clickX = rect.x + 28;
   const clickY = rect.y + 37;
   ```
2. Dispatch native mouse events via CDP `Input.dispatchMouseEvent`:
   ```python
   await cdp_call(ws_page, 'Input.dispatchMouseEvent', {
       'type': 'mousePressed',
       'x': clickX,
       'y': clickY,
       'button': 'left',
       'clickCount': 1
   })
   await cdp_call(ws_page, 'Input.dispatchMouseEvent', {
       'type': 'mouseReleased',
       'x': clickX,
       'y': clickY,
       'button': 'left',
       'clickCount': 1
   })
   ```
3. Verify resolution by reading `document.getElementById('g-recaptcha-response').value`:
   - Non-empty response string indicates reCAPTCHA was solved successfully without triggering image tile challenges.

---

## Attaching Playwright over CDP to Existing Chrome

When high-level automation is preferred:
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    # Access existing context & pages
    for ctx in browser.contexts:
        for page in ctx.pages:
            print(page.title(), page.url)
```
