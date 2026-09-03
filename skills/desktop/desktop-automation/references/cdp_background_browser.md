# Chrome DevTools Protocol (CDP) Background Automation

Driving an existing or logged-in Chrome profile in the background without stealing user focus or moving the OS cursor.

## Launching Chrome with CDP
Always launch detached from the agent shell (never block foreground):
```powershell
Start-Process -FilePath "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList @(
    "--remote-debugging-port=9222",
    "--user-data-dir=`"C:\Users\Kibe\AppData\Local\hermes\chrome_profiles\my_profile`""
)
```

## Connecting & Driving via Python CDP (Zero Focus Steal)
```python
import json
import asyncio
import websockets
import urllib.request

# 1. Discover targets
with urllib.request.urlopen("http://127.0.0.1:9222/json/list") as resp:
    pages = json.loads(resp.read().decode())

target = next((p for p in pages if "shopee.vn" in p.get("url", "")), pages[0])
ws_url = target["webSocketDebuggerUrl"]

# 2. Evaluate DOM / Actions
async def cdp_eval(ws_url, expr):
    async with websockets.connect(ws_url) as ws:
        msg = {
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {"expression": expr, "returnByValue": True, "awaitPromise": True}
        }
        await ws.send(json.dumps(msg))
        while True:
            res = json.loads(await ws.recv())
            if res.get("id") == 1:
                return res.get("result", {}).get("result", {}).get("value")

# Navigate
async def navigate(ws_url, url):
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Page.navigate", "params": {"url": url}}))
```
