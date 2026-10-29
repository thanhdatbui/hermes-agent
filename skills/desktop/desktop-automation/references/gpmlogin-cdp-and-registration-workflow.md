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

## 2. KỶ LUẬT TỐI CAO: REUSE PROFILE & PROXY INVARIANT (CHỐNG LỘ IP HOST)
- **Profile Reuse First (CẤM tạo profile rác):**
  * Khi có task cần trình duyệt để đăng nhập, nhận OTP, xác minh hoặc cày web, **BẮT BUỘC** tìm kiếm và tái sử dụng profile có sẵn trong hệ thống GPMLogin (`search=...`).
  * **CẤM TUYỆT ĐỐI** tự ý gọi `POST /api/v3/profiles/create` để đẻ profile mới không có trong danh mục quản lý của farm, gây rác database GPM và làm loãng pool tài khoản.
- **Proxy Invariant (BẤT BIẾN PROXY RIÊNG):**
  * Mọi tài khoản trong farm (Gmail, Hotmail, TikTok, AWS, ChatGPT...) **BẮT BUỘC** phải chạy qua Proxy riêng được gán (dải proxy di động Mobi/Mirotik).
  * **CẤM TUYỆT ĐỐI** mở profile trình duyệt chạy bằng IP trực tiếp của máy host (Kibe) để test, đăng ký hay truy cập dịch vụ bên ngoài. Lộ IP gốc của host sẽ kích hoạt cơ chế liên đới cấm hàng loạt tài khoản trên cùng dải IP.
  * **Hậu kiểm IP thực tế trước khi thao tác:** Bắt buộc mở 1 tab kiểm tra IP qua `https://api.ipify.org?format=json` để đảm bảo IP hiển thị đúng dải proxy của profile trước khi điều hướng tới trang đích.

## 3. Vendor Contract & Typo Trap khi Start Profile
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
- **Delete Profile Endpoint:**
  - `POST http://127.0.0.1:19995/api/v3/profiles/delete/{profile_id}` kèm body `{"mode": 2}` (mode 1: app, mode 2: app + folder).

## 4. Web Automation qua Native WebSocket CDP
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

## 5. Input Automation (React Native Setter) & Anti-Bot Hand-off Discipline
- **Input Field Attributes trên SPA (React / Vue / AWSUI):**
  - Thuộc tính `value` của input nếu chỉ gán trực tiếp `input.value = '...'` sẽ **KHÔNG** kích hoạt state của React/AWSUI, dẫn đến lỗi validation (`An email address is required`).
  - **Bắt buộc** dùng `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value)` kết hợp dispatch đủ 3 sự kiện: `input`, `change`, `blur`:
    ```javascript
    function setNativeValue(element, value) {
        const valueSetter = Object.getOwnPropertyDescriptor(element, 'value').set;
        const prototype = Object.getPrototypeOf(element);
        const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
        if (prototypeValueSetter && valueSetter !== prototypeValueSetter) {
            prototypeValueSetter.call(element, value);
        } else {
            valueSetter.call(element, value);
        }
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
        element.dispatchEvent(new Event('blur', { bubbles: true }));
    }
    ```
- **Anti-Bot / CAPTCHA Gate:**
  - Khi bấm Verify xuất hiện iframe bảo mật (`threat-mitigation.aws.amazon.com`, Arkose Labs, reCAPTCHA puzzle) hoặc yêu cầu xác minh thẻ thanh toán (Credit/Debit Card): Agent **KHÔNG ĐƯỢC** chạy loop mù giải đố hay nhập thông tin thẻ nhạy cảm.
  - Phải chụp ảnh màn hình bằng chứng (Gate 6), mở profile trên màn hình desktop máy người dùng và bàn giao đúng điểm nghẽn để người dùng thao tác 1 chạm bằng tay.

## 6. Post-Reboot / Headless Launch Pitfall (`Yêu cầu cập trình duyệt [Chromium] [142]`)
- **Symptom:** Khởi chạy `GPMLogin.exe` ngầm (headless / `subprocess.Popen`) hoặc sau khi máy reboot, gọi API `/api/v3/profiles/start/{id}` trả về:
  `{"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}`
- **Root Cause:**
  1. Trình duyệt lõi (`gpm_browser_chromium_core_142\chrome.exe` và `chrome.dll` ~264MB) vẫn nguyên vẹn 100% trên đĩa.
  2. Tuy nhiên, nếu GPMLogin được bật mà **chưa hoàn tất phiên GUI khởi tạo** (chưa có cửa sổ chính đầy đủ `GPM-Login v4.3.6-stable` kích hoạt đồng bộ manifest/fingerprint với server GPM), hoặc bị chạy song song 2 tiến trình mồ côi (headless PID background vs GUI PID), backend C# của GPM sẽ tự động khóa Local API v3 và trả về lỗi giả yêu cầu cập nhật.
  3. Ngoài ra, GPM chặn hoàn toàn việc downgrade: nếu profile đã ở version 142 thì không thể hạ xuống 137 hay 139 qua API (`Do not downgrade from version 137`).
- **Remediation:**
  1. Kiểm tra tiến trình: `Get-Process GPMLogin | Select-Object Id, MainWindowTitle, MainWindowHandle`. Nếu có tiến trình không có MainWindowTitle (chạy cụt ngầm), phải kill tiến trình mồ côi đó trước.
  2. Đảm bảo cửa sổ `GPM-Login v4.3.6-stable` được hiển thị trên desktop để app kết nối cloud session thành công.
  3. File `version` trong thư mục `gpm_browser_chromium_core_142` phải phản ánh đúng version của server (chuẩn hiện tại là `1.0` sau khi user update).
