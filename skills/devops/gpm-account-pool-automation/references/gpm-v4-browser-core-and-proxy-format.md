# GPMLogin v4.3.6+ Browser Core & UI Invariants

## 1. Lỗi "Yêu cầu cập trình duyệt [Chromium] [142]"
### Hiện tượng
- API `GET /api/v3/profiles/start/{id}` trả về:
  `{"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}`
- Dù kiểm tra thư mục `gpm_browser/gpm_browser_chromium_core_142` đã có binary `chrome.exe` và `142.0.7444.163`.

### Nguyên nhân gốc rễ
1. **Server GPM nâng fingerprint / build mới (ví dụ Fingerprint 411):** Khi server ra bản patch mới, file `version` trong thư mục core (vd `1.0`) không còn khớp với yêu cầu của backend GPM.
2. **Khóa hạ cấp (Downgrade lock):** Profile đã ở version 142 không thể hạ xuống 137 hay bản cũ hơn qua API/UI nếu chưa cập nhật core 142 mới nhất.
3. **Cách cập nhật chuẩn:**
   - Trên giao diện GPM, bấm trực tiếp nút **`Mở`** trên một profile v142.
   - Khi popup báo lỗi hiện ra, bấm nút **"Cập nhật"** hoặc **"Tải về"** để app kéo bản build mới về.

---

## 2. Cột Proxy trên UI GPM hiện `http:0`
### Hiện tượng
- Trên giao diện bảng profile của GPMLogin v4, cột Proxy hiển thị `http:0` màu đỏ dù profile đã được gán proxy.

### Nguyên nhân
- Script automation tạo/update profile truyền proxy có format chứa chú thích hoặc tiền tố URL, ví dụ:
  `http://192.168.110.2:20061 (test.taadaa.click:5127)`
- Parser UI của GPMLogin v4 chỉ nhận chuỗi proxy thô dạng:
  `host:port:user:pass` hoặc `host:port` hoặc `http://host:port`.
- Mọi ký tự lạ như dấu mở/đóng ngoặc đơn `(...)` sẽ khiến UI parse lỗi thành host `http` và port `0`.

### Khắc phục
- Chuẩn hóa chuỗi proxy trước khi gửi API `create_profile` / `update_profile`:
  Dùng regex loại bỏ toàn bộ phần chú thích:
  ```python
  clean_proxy = re.sub(r"\s*\(.*?\)", "", raw_proxy).strip()
  if clean_proxy.startswith("http://"):
      clean_proxy = clean_proxy[7:]
  ```

---

## 3. UIPI / Windows Privilege Isolation (Standard vs Elevated)
### Hiện tượng
- Khi Hermes Agent chạy dưới quyền Standard User (qua Telegram Gateway tự khởi động cùng Windows), các lệnh `computer_use` (InjectSyntheticPointerInput, SendKeys) vào cửa sổ GPMLogin bị lỗi:
  `Access is denied. (0x80070005)`

### Giải pháp
- Không dùng simulated mouse/keyboard trực tiếp vào cửa sổ Elevated.
- Ưu tiên dùng Win32 API `PostMessageW` (gửi `WM_KEYDOWN`/`WM_KEYUP` như phím `VK_ESCAPE`) hoặc đóng/khởi động lại GPMLogin dưới quyền của current user session.
- Đối với các thao tác cấu hình, gọi trực tiếp REST API port 19995 (`/api/v3/profiles/update/{id}`) hoặc cập nhật SQLite database `profile_data.db` thay vì click UI.
