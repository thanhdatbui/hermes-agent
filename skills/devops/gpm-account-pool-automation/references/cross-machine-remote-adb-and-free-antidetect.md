# Cross-Machine Farm OTP & Antidetect Architecture (Kibe vs Admin)

## 1. Bối cảnh bài toán
- **Kibe (Máy điều phối / GPM):** Sở hữu key bản quyền GPMLogin (Local API port `19995`), lưu trữ profiles & proxy mapping.
- **Admin (Máy farm / S7 reg Gmail):** Kết nối qua LAN (`192.168.110.119`) hoặc Tailscale (`100.120.89.125`). Điện thoại nhận mã OTP / Google Prompt nằm tại máy Admin nhưng profile GPM chạy trên Kibe.
- **Ràng buộc:** Chỉ có 1 key GPM, tránh tốn thêm chi phí bản quyền và không cần di chuyển thiết bị vật lý.

---

## 2. Phương án 1: Remote ADB qua LAN / Tailscale (Khuyên dùng)
Cho phép máy Kibe điều khiển trực tiếp các máy điện thoại cắm tại Admin để tự động vượt challenge Google (OTP 10 số, Google Prompt, SMS).

### Bước 1: Mở ADB Server trên Admin (Lắng nghe 0.0.0.0)
Mặc định ADB server chỉ bind `127.0.0.1:5037`. Trên máy Admin chạy:
```cmd
adb kill-server
adb -a nodaemon server
```
*(Đảm bảo Windows Firewall trên Admin cho phép inbound port TCP `5037` trong subnet LAN).*

### Bước 2: Kibe kết nối và tương tác từ xa
Trên máy Kibe, thêm cờ `-H <ADMIN_IP>`:
```bash
# Liệt kê thiết bị cắm tại Admin:
adb -H 192.168.110.119 devices
# Hoặc qua Tailscale:
adb -H 100.120.89.125 devices

# Lấy dump XML màn hình điện thoại Admin để trích xuất OTP:
adb -H 192.168.110.119 -s <SERIAL> exec-out uiautomator dump /dev/tty
# Tap xác nhận Google Prompt từ xa:
adb -H 192.168.110.119 -s <SERIAL> shell input tap <X> <Y>
```

### Bước 3: Alternative - atx-agent qua WiFi
Nếu thiết bị đã cài `atx-agent` (port `7912`), gọi trực tiếp endpoint HTTP qua IP WiFi của điện thoại:
`http://<PHONE_IP>:7912/dump` hoặc `/jsonrpc` mà không cần phụ thuộc vào ADB daemon của máy Admin.

---

## 3. Phương án 2: Tự dựng Antidetect Free cho Admin (Zero-cost)
Khi muốn dàn Admin tự động login Gmail, lưu session độc lập mà không cần mua thêm key GPM:

### A. Chrome Native Profiles + `rebrowser-patches`
- **Cơ chế:** Dùng Google Chrome có sẵn trên Admin kết hợp `--user-data-dir` phân tách profile.
- **Bypass bot:** `rebrowser-playwright` vá triệt để rò rỉ CDP (`Runtime.enable`, `Console.enable`, `navigator.webdriver`), qua mặt bot Google tốt hơn injection script của GPM.
- **Khởi chạy:**
  ```cmd
  chrome.exe --user-data-dir="D:\AdminProfiles\M10" --proxy-server="http://user:pass@ip:port" --remote-debugging-port=9222
  ```
- **Tương tác:** Python Playwright kết nối vào port `9222`, tự động lưu cookie/session vĩnh viễn trong `D:\AdminProfiles\M10`.

### B. `Camoufox` (Headless Firefox C++ Patched)
- **Ưu điểm:** 100% Open Source, patch ở tầng C++ engine Firefox. Spoof hoàn chỉnh Canvas, WebGL, Audio, Geolocation, Font. Cực kỳ nhẹ RAM, chạy headless mượt mà không bị Google gắn cờ bot.
- **Sử dụng:**
  ```python
  from camoufox.sync_api import Camoufox

  with Camoufox(headless=True, persistent_context=True, user_data_dir="D:/Profiles/M10", proxy={"server": "http://ip:port"}) as browser:
      page = browser.new_page()
      page.goto("https://accounts.google.com")
  ```
