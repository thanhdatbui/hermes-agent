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
- **Post-Reboot / Headless Launch Pitfall (`Yêu cầu cập trình duyệt [Chromium] [142]`):**
  - **Symptom:** Khởi chạy `GPMLogin.exe` ngầm (headless / `subprocess.Popen`) hoặc sau khi máy reboot, gọi API `/api/v3/profiles/start/{id}` trả về:
    `{"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}`
  - **Root Cause:**
    1. Trình duyệt lõi (`gpm_browser_chromium_core_142\chrome.exe` và `chrome.dll` ~264MB) vẫn nguyên vẹn 100% trên đĩa.
    2. Tuy nhiên, nếu GPMLogin được bật mà **chưa hoàn tất phiên GUI khởi tạo** (chưa có cửa sổ chính đầy đủ `GPM-Login v4.3.6-stable` kích hoạt đồng bộ manifest/fingerprint với server GPM), hoặc bị chạy song song 2 tiến trình mồ côi (headless PID background vs GUI PID), backend C# của GPM sẽ tự động khóa Local API v3 và trả về lỗi giả yêu cầu cập nhật.
    3. Ngoài ra, GPM chặn hoàn toàn việc downgrade: nếu profile đã ở version 142 thì không thể hạ xuống 137 hay 139 qua API (`Do not downgrade from version 137`).
  - **Remediation:**
    1. Kiểm tra tiến trình: `Get-Process GPMLogin | Select-Object Id, MainWindowTitle, MainWindowHandle`. Nếu có tiến trình không có MainWindowTitle (chạy cụt ngầm), phải kill tiến trình mồ côi đó trước.
    2. Đảm bảo cửa sổ `GPM-Login v4.3.6-stable` được hiển thị trên desktop để app kết nối cloud session thành công.
    3. Nếu app vẫn kẹt cờ tài nguyên: Người dùng cần click một lần vào nút "Cập nhật lại GPM" (hoặc bấm mở 1 profile bất kỳ trực tiếp trên giao diện GPM) để app kích hoạt đồng bộ manifest/core 142 từ server về máy, sau đó Local API v3 sẽ tự động nhả khóa `success: true`.
