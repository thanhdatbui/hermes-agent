# GPMLogin v4.3.6: Chromium 142 Core Update, Modal Blocking & API Quirks

## 1. Lỗi "Yêu cầu cập trình duyệt [Chromium] [142]" & Modal Blocking
Khi GPM tự động cập nhật hoặc người dùng tải gói tài nguyên core Chromium 142:
- GPM API `POST /api/v3/profiles/start/{id}` trả về:
  `{"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}`
- **Nguyên nhân chính:** GPM bật popup modal "Big Update" (thông báo cập nhật fingerprint database 411, ra mắt GPMLogin Global) với nút đỏ "Đóng thông báo" ở giữa màn hình. Khi modal này đang hiển thị, UI và API nội bộ của GPM bị chặn, không khởi động được trình duyệt.
- **Khắc phục:** Bắt buộc bấm nút đỏ "Đóng thông báo" trên giao diện GPM (hoặc gửi event tắt popup) để đưa GPM về danh sách Profiles bình thường.

## 2. Lỗi chính tả tham số trong Binary GPMLogin.exe (`addination_args`)
- Trong binary `GPMLogin.exe` (v4.3.6), tham số nhận cờ bổ sung dòng lệnh của Chromium có typo:
  `addination_args` (có chữ 'n' thừa sau 'addi'), KHÔNG PHẢI `addition_args`.
- Khi cần truyền cờ qua API start:
  `GET /api/v3/profiles/start/{id}?addination_args=--remote-allow-origins=*`

## 3. Cấu trúc thư mục Chromium Core 142
- Gói tài nguyên Chromium 142 tải về tại:
  `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142`
- Các file DLL lõi (`chrome.dll`, `chrome_elf.dll`) nằm trong thư mục con phiên bản: `142.0.7444.163\`.
- Nếu chạy `chrome.exe` trực tiếp ngoài GPM, hệ điều hành cần nạp `chrome_elf.dll` qua cấu trúc version directory của Chromium. Khi GPM khởi chạy qua API với profile đã tải core xong, GPM tự quản lý đường dẫn driver `gpmdriver.exe`.

## 4. Playwright CDP Handshake trên Chromium 142
- Chromium 142 kiểm tra chặt chẽ WebSocket `Origin` header.
- Playwright kết nối CDP qua `pw.chromium.connect_over_cdp(f"http://{remote_debugging_address}")` sẽ gửi `Origin: http://127.0.0.1:...`.
- Nếu profile khởi động bình thường trên GPM, Playwright kết nối mượt mà vào port debug được cấp. Tuy nhiên, nếu GPM đang bị modal che hoặc core chưa tải xong, connection sẽ timeout 180s.

## 5. Cạm bẫy Crash Playwright `launch_persistent_context` Trên Core 142 (Exit Code 3221225477)
- **Hiện tượng:** Khi một script cố khởi chạy `chrome.exe` của core 142 trực tiếp qua Playwright:
  ```python
  ctx = p.chromium.launch_persistent_context(
      user_data_dir=prof_dir,
      executable_path=CHROME_EXE,
      ignore_default_args=["--disable-save-password-bubble"]
  )
  ```
  Chromium crash ngay khi bật với exit code `3221225477` kèm log:
  `--variations-state-file can not work with other field-trial related flags: --force-fieldtrials, --force-fieldtrial-params, --enable-features, --disable-features`
- **Nguyên nhân cốt lõi:** Bản build Chromium 142 của GPM nhúng sẵn cờ `--variations-state-file`. Trong khi đó, Playwright mặc định tự động tiêm `--enable-features=...`, `--disable-features=...` và `--disable-field-trial-config`. Sự xung đột giữa variations state và field-trial flags làm Chromium abort ngay lập tức.
- **Quy chuẩn khắc phục:**
  1. *Khởi chạy qua GPM Local API (Khuyên dùng):* Luôn gọi `GET /api/v3/profiles/start/{id}` lấy `remote_debugging_address`, sau đó kết nối qua `p.chromium.connect_over_cdp(f"http://{addr}")`. GPM tự quản lý proxy authentication và các flags an toàn.
  2. *Nếu bắt buộc dùng `launch_persistent_context`:* BẮT BUỘC đặt boolean `ignore_default_args=True` (thay vì list các cờ riêng lẻ) để Playwright loại bỏ hoàn toàn các cờ features/field-trial mặc định xung đột.

