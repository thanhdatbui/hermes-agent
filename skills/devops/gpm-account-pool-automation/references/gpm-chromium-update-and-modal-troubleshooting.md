# GPMLogin Chromium Version Mismatch & Modal Dialog Blockers

## 1. Triệu chứng & Mã lỗi API
Khi gọi `GET /api/v3/profiles/start/<profile_id>`, GPMLogin trả về:
```json
{"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}
```
(hoặc `[Chromium] [127]`, `[Chromium] [139]`) mặc dù thư mục binary tương ứng đã tồn tại trong `gpm_browser/gpm_browser_chromium_core_<ver>`.

## 2. Các nguyên nhân gốc rễ (Root Causes)

### A. Core Browser Sub-version / Patch mismatch
- **Cơ chế**: Thư mục `gpm_browser_chromium_core_<ver>` có chứa file text `version` (ví dụ `1.0`). Khi GPMLogin server phát hành bản vá Fingerprint database mới (ví dụ Fingerprint 411 trên v4.3.6), nó yêu cầu core browser package phải có `version >= 1.1`.
- **Dấu hiệu nhận biết**:
  - `gpm_browser_chromium_core_142/version` là `1.0`.
  - `gpm_browser_firefox_core_145/version` đã là `1.1`.
- **Cách khắc phục**:
  - Truy cập UI GPMLogin -> **Cài đặt (bánh răng)** -> tab **Trình duyệt (Browser)** -> bấm **Cập nhật/Tải về** cho core tương ứng để đồng bộ package mới từ server GPM.
  - Sau khi tải xong, GPM sẽ nâng `version` lên và API `/api/v3/profiles/start/` mở khóa.

### B. Modal Dialog / Popup "Big Update" chặn Engine API
- **Cơ chế**: Khi GPMLogin có popup modal (ví dụ dialog "Big Update" giới thiệu tính năng, đổi fingerprint 411), engine UI của GPM có thể khóa luồng khởi tạo browser và quăng mã lỗi giả `Yêu cầu cập trình duyệt` để ép người dùng chú ý tới UI.
- **Dấu hiệu nhận biết**:
  - Chụp màn hình GPMLogin thấy cửa sổ bị phủ mờ (dimmed) bởi popup modal ở chính giữa.
  - File `do_not_show_what_news` lưu version đã đọc, nhưng các bản cập nhật đặc biệt vẫn có thể bung modal một lần lúc khởi động.
- **Cách khắc phục**:
  - Click nút đỏ **"Đóng thông báo"** trên màn hình GPMLogin.

## 3. Lưu ý về Quyền thực thi (UIPI / UAC) trên Windows
- GPMLogin thường chạy dưới quyền Administrator (Elevated).
- Các lệnh điều khiển GUI nền (như `computer_use`, Win32 `InjectSyntheticPointerInput`, `SendKeys`) nếu chạy từ tiến trình quyền Standard User sẽ bị Windows chặn theo cơ chế **UIPI (User Interface Privilege Isolation)** với lỗi:
  `InjectSyntheticPointerInput: Access is denied (0x80070005)`
- Để automation can thiệp được vào UI của GPMLogin, gateway/runner bắt buộc phải cùng mức đặc quyền (Elevated/Admin).

## 4. Chromium Core Structure & DLL Loader Crash (0xc0000135)
- **Triệu chứng**: GPM báo khởi động profile thành công (trả về PID Chrome và remote_debugging_address), nhưng sau 1-2 giây tiến trình Chrome tự biến mất (exit code `3221225781` / `0xc0000135` - `STATUS_DLL_NOT_FOUND`).
- **Nguyên nhân**: Khi GPM tải gói core Chromium mới (ví dụ `gpm_browser_chromium_core_142`), gói giải nén chỉ đặt `chrome_elf.dll` và `chrome.dll` trong thư mục con phiên bản (ví dụ `142.0.7444.163/`). Khi `chrome.exe` ở thư mục gốc khởi chạy, Windows Dynamic Linker không tìm thấy `chrome_elf.dll` ở root và crash ngay trước khi mở port CDP.
- **Cách khắc phục**:
  Copy `chrome_elf.dll` từ thư mục con phiên bản ra thư mục gốc của core:
  ```bash
  cp "gpm_browser_chromium_core_<ver>/<sub_ver>/chrome_elf.dll" "gpm_browser_chromium_core_<ver>/chrome_elf.dll"
  ```

## 5. Playwright CDP Timeout & WebSocket 403 Forbidden (`--remote-allow-origins`)
- **Triệu chứng**: GPM profile khởi động thành công, port remote debugging đang lắng nghe (`/json/version` trả về 200 OK), nhưng Playwright `browser = p.chromium.connect_over_cdp(f"http://{addr}")` bị treo cứng và ném `TimeoutError: BrowserType.connect_over_cdp: Timeout exceeded`.
- **Nguyên nhân gốc rễ**: Chromium v111+ kích hoạt cơ chế bảo mật WebSocket origin validation. Playwright khi kết nối luôn gửi header `Origin: http://127.0.0.1:<port>`. Nếu Chrome không có cờ `--remote-allow-origins=*`, Chrome sẽ từ chối bắt tay WebSocket với lỗi ngầm:
  `HTTP 403 Forbidden: Rejected an incoming WebSocket connection from the http://127.0.0.1:<port> origin.`
- **Cách khắc phục**:
  Khi gọi API start profile của GPM, bắt buộc truyền cờ `addition_args`:
  ```python
  res = requests.get(f"http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}", params={
      "win_scale": "0.8",
      "addition_args": "--remote-allow-origins=*"
  }).json()
  ```

