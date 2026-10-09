# Remote Chrome DevTools Automation via ADB Forward

Khi cần thao tác, click, submit form hoặc kiểm tra web trên Chrome đang mở trên thiết bị Android qua ADB (đặc biệt khi uiautomator dump không lấy được chi tiết webview DOM hoặc trang web chạy dynamic content):

## 1. Kiểm tra Chrome DevTools Unix Socket trên thiết bị
```bash
$ADB -s <SERIAL> shell "grep -a chrome /proc/net/unix"
# Kết quả thường thấy: @chrome_devtools_remote
```

## 2. Port forward qua ADB
```bash
$ADB -s <SERIAL> forward tcp:<LOCAL_PORT> localabstract:chrome_devtools_remote
# Ví dụ: tcp:9223
```

## 3. Liệt kê các tab đang mở
```bash
curl -s http://127.0.0.1:<LOCAL_PORT>/json/list
```
JSON trả về danh sách các tab kèm:
- `title`
- `url`
- `webSocketDebuggerUrl`: ví dụ `ws://127.0.0.1:9223/devtools/page/<ID>`

## 4. Tương tác với DOM qua WebSocket / CDP Runtime.evaluate
Sử dụng script Python với thư viện `websockets` để query DOM và trigger click / submit trực tiếp vào JavaScript context:

```python
import asyncio, json, websockets

async def click_element(ws_url):
    async with websockets.connect(ws_url) as ws:
        expr = """
        (() => {
            const btn = document.querySelector('button[type="submit"]');
            if (btn) {
                btn.click();
                return 'Clicked submit button';
            }
            const form = document.querySelector('form');
            if (form) {
                form.submit();
                return 'Submitted form directly';
            }
            return 'Button not found';
        })()
        """
        msg = {'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': expr, 'returnByValue': True}}
        await ws.send(json.dumps(msg))
        res = await ws.recv()
        print('Result:', res)

asyncio.run(click_element('ws://127.0.0.1:9223/devtools/page/<ID>'))
```

## 5. Dọn dẹp port forward sau khi hoàn thành
```bash
$ADB -s <SERIAL> forward --remove tcp:<LOCAL_PORT>
```
