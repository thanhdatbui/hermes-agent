# GPMLogin Local REST API & Chrome CDP Registration / Verification Workflow

## Overview
Khi người dùng yêu cầu tự động hóa trên trình duyệt antidetect (GPMLogin) thông qua Local REST API (`127.0.0.1:19995`) và Chrome DevTools Protocol (CDP):

## 1. GPM Local REST API Discovery & Port Identification
- **Default Port:** `19995`.
- **Cấu hình dynamic port:** Đọc từ file `%LOCALAPPDATA%\Programs\GPMLogin\api_port.dat` (hoặc kiểm tra `active_log.txt`).
- **Endpoint kiểm tra profiles:**
  - `GET http://127.0.0.1:19995/api/v3/profiles?page=1&per_page=100`
  - `GET http://127.0.0.1:19995/api/v3/groups`
  - Tìm kiếm theo keyword: `GET http://127.0.0.1:19995/api/v3/profiles?search=<keyword>`

## 2. Vendor Contract & Typo Trap khi Start Profile
- **Vendor Typo:** GPMLogin Local REST API v3 C# backend (`GPMLogin.Models.dll`) nhận tham số dòng lệnh Chromium là `addination_args` (có thêm chữ "n"), KHÔNG nhận `addition_args`.
- **Start Profile Endpoint:**
  ```python
  url = f"http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}?win_scale=0.8&addination_args=--mute-audio&addition_args=--mute-audio"
  res = requests.get(url, timeout=30).json()
  remote_addr = res["data"]["remote_debugging_address"] # e.g. "127.0.0.1:65017"
  ```
- **Close Profile Endpoint:**
  - `GET http://127.0.0.1:19995/api/v3/profiles/close/{profile_id}`
  - Fallback: `GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}`

## 3. Web Automation qua Native WebSocket CDP
Không cần cài thư viện nặng (Playwright/Selenium) khi môi trường bị khóa gói (PEP 668):
- Lấy `webSocketDebuggerUrl` từ `http://<remote_addr>/json/list`.
- Gửi các lệnh RFC 6455 qua thư viện `websockets` (Python):
  ```python
  import asyncio, json, base64, urllib.request, websockets

  async def inspect_and_act(remote_addr):
      tabs = json.loads(urllib.request.urlopen(f"http://{remote_addr}/json/list").read().decode("utf-8"))
      page_tab = next(t for t in tabs if t.get("type") == "page")
      ws_url = page_tab["webSocketDebuggerUrl"]
      
      async with websockets.connect(ws_url, max_size=10*1024*1024) as ws:
          # Điều hướng
          await ws.send(json.dumps({"id": 1, "method": "Page.navigate", "params": {"url": "https://example.com"}}))
          await asyncio.sleep(5)
          
          # Chụp ảnh nghiệm thu (Gate 6)
          await ws.send(json.dumps({"id": 2, "method": "Page.captureScreenshot", "params": {"format": "png"}}))
          while True:
              resp = json.loads(await ws.recv())
              if resp.get("id") == 2:
                  data = base64.b64decode(resp["result"]["data"])
                  with open("screen.png", "wb") as f:
                      f.write(data)
                  break
  ```

## 4. Input Automation & Anti-Bot Hand-off Discipline
- **Input Field Attributes:** Khi điền form web phức tạp (như AWS Console Signup), các input thường dùng `id="emailAddress"`, `id="accountName"` thay vì selector thông thường. Bắt buộc kích hoạt cả 3 sự kiện: `focus()`, `input`, `change`, `blur()`.
- **Anti-Bot / CAPTCHA Gate:**
  - Khi bấm Verify xuất hiện reCAPTCHA/Arkose Labs/puzzle hoặc yêu cầu xác minh thẻ thanh toán (Credit/Debit Card): Agent KHÔNG ĐƯỢC chạy loop mù giải đố hay nhập thông tin thẻ nhạy cảm.
  - Phải chụp ảnh màn hình bằng chứng (Gate 6), mở profile trên màn hình desktop máy người dùng và bàn giao đúng điểm nghẽn để người dùng thao tác 1 chạm bằng tay.
- **Post-Reboot Recovery:**
  - Nếu hệ thống bị reboot giữa chừng, GPMLogin và các tiến trình Chrome con sẽ bị tắt hoàn toàn.
  - Kiểm tra cổng `19995` trước. Nếu GPMLogin chưa chạy, báo người dùng mở app GPMLogin trên Desktop trước khi gửi lệnh start profile.
