# Mass Upload Recovery: Parenthesized Workbook Headers & Profile Milestone Popup (2026-10-17)

## 1. Parenthesized Workbook Headers (Tik*.xlsx -> account_source.py)
- **Triệu chứng:** Runner upload báo lỗi:
  `Workflow target error: Missing required fields: Folder Video`
  lặp lại qua 5 lần retry đọc workbook.
- **Root cause:** Các file Excel phân bổ Tik (Tik1..Tik8) sử dụng tiêu đề cột chi tiết có chú thích mở rộng trong ngoặc đơn:
  `Folder Video (Render Dich)` và `Video Goc (Nguon Cao)`.
  Trước đây `CANONICAL_HEADERS` trong `scripts/tiktok_workflow/account_source.py` chỉ nhận diện chuỗi thuần `folder video` và `video goc`. Mặc dù `normalize_header` chuẩn hóa Unicode NFKC và bỏ dấu, dấu ngoặc đơn vẫn được giữ lại (`"folder video (render dich)"`) khiến mapping thất bại.
- **Fix đã áp dụng:**
  Thêm các biến thể có ngoặc đơn vào `CANONICAL_HEADERS`:
  - `Folder Video`: `{"folder video", "video folder", "folder video (render dich)", "folder video render dich", "sttvideo"}`
  - `video gốc`: `{"video goc", "video source", "source video", "video goc (nguon cao)", "video goc nguon cao"}`
  Đồng thời chuẩn hóa EOL LF cho file `account_source.py` và sync sang `admin-farm`.

## 2. Popup Milestone "Tổng lượt thích" chặn Account Switcher
- **Triệu chứng:** Khi mở Profile để switch account, TikTok hiển thị popup chúc mừng thành tích:
  Tiêu đề: *"Tổng lượt thích"* / *"Tổng số lượt thích"*
  Nội dung: `"<account> đã nhận tổng cộng X lượt thích cho tất cả video"`
  Nút bấm: `[OK]` ở tọa độ `[506, 1389, 575, 1425]` (tâm `(540, 1407)` trên 1080x1920).
  Popup che khuất thanh header tên tài khoản khiến `prepare_switcher_anchor` (`adapter.py`) quét ra nhiều candidate hoặc không tìm thấy anchor duy nhất, dẫn đến:
  `[ACCOUNT_SWITCHER_FAILED] open_switcher failed: SWITCHER_NOT_CONFIRMED`
- **Fix đã áp dụng:**
  1. Trong `scripts/tiktok_workflow/adapter.py` (`prepare_switcher_anchor`):
     - Kiểm tra nếu `xml_text` chứa `"tổng lượt thích"` hoặc `"tổng số lượt thích"`.
     - Tìm và bấm nút đóng (`"OK"`, `"ok"`, `"Đóng"`, `"Close"`, `"Xong"`) qua text hoặc `content_desc`.
     - Nếu không tìm thấy node văn bản, tap fallback tọa độ vật lý `adapter.tap(540, 1400)`.
     - Chờ 1.0s và dump lại XML sạch trước khi tiếp tục dò anchor switcher.
     - Sắp xếp candidates theo tọa độ Y tăng dần (`candidates.sort(key=lambda c: c[2])`) và chọn `candidates[0]` (luôn là thanh header tên nick ở đỉnh).
  2. Trong `scripts/tiktok_workflow/state_machine.py` (`_dismiss_simple_close_popup`):
     - Thêm kiểm tra `content_desc=label` khi gọi `_tap_if_found`.
     - Bổ sung fallback `adapter.tap(540, 1400)` nếu chuỗi `"tổng lượt thích"` hoặc `"tổng số lượt thích"` vẫn còn sau khi thử hết nhãn nút.

## 3. Thoát màn hình LIVE Camera sau khi bấm đăng (`VERIFY_POST`)
- **Triệu chứng:** Sau khi bấm Đăng bài, TikTok đôi khi nhảy sang giao diện phát LIVE camera (`CAMERA / TẠO / LIVE`).
  Lệnh phím cứng `BACK` bị TikTok chặn ở màn hình này, dẫn đến:
  `[POST_VERIFY_LIVE_SURFACE_BLOCKED] LIVE vẫn còn hoặc recapture không hợp lệ sau tối đa 2 Back -> MANUAL_REVIEW`
- **Fix đã áp dụng:**
  Trong `_dismiss_live_surface` (`state_machine.py`), kết hợp tap trực tiếp nút `[X]` đóng camera ở góc trên bên trái `(60, 140)` cùng lệnh `adapter.back()` ở mỗi attempt.

## 4. 🛑 CẢNH BÁO: BỎ HOÀN TOÀN VICHANGER — CẤM BẬT LẠI WATCHER (USER CORRECTION 2026-10-17)
- **Triệu chứng nhầm lẫn:** Runner gặp lỗi UI kích hoạt `SOFT REBOOT RECOVERY`, sau reboot dừng ở:
  `Guarded reboot recovery failed: proxy watcher did not publish post-reboot readiness after reboot`
  Agent từng nhầm lẫn rằng task `GanProxyWatcherTray` bị tắt là lỗi và tự ý bật lại watcher.
- **BẢN CHẤT CỐT LÕI (USER INVARIANT):**
  - **Farm đã BỎ HOÀN TOÀN ViChanger từ tháng 9/2026:** Toàn bộ 80 máy Kibe chạy proxy ở **tầng Wi-Fi / Router MikroTik + Container Singbox** (`192.168.110.2:20001..20080`), gán qua `global http_proxy`. Máy KHÔNG cài/chạy app ViChanger, KHÔNG dùng card mạng `tun0`.
  - Task `GanProxyWatcherTray` **BẮT BUỘC ĐỂ TRẠNG THÁI DISABLED**. CẤM TUYỆT ĐỐI bật lại task này hay chạy bất kỳ tiến trình `gan_proxy_fleet.py watch` nào trên máy Kibe.
  - Lỗi `proxy watcher did not publish post-reboot readiness` là do code runner còn sót logic chờ file marker `.codex/device-readiness/<hash>.json` sau soft-reboot.
  - **Hành động đúng:** KHÔNG cố phục hồi ViChanger; thay vào đó giải quyết dứt điểm các lỗi UI (popup che, nút bấm không ăn) để quy trình đăng bài chạy thẳng mượt mà, không kích hoạt soft-reboot.

## 5. Downloader Admin kẹt 502 Bad Gateway do WAN loopback
- **Triệu chứng:** Log cào video `download_admin_p10.log` trên host Admin văng lỗi:
  `ProxyError: ('Unable to connect to proxy', OSError('Tunnel connection failed: 502 Bad Gateway'))`
- **Root cause:** File `proxy_pool_69.txt` trên host Admin dùng domain WAN `mirotik1.taadaa.click:10001..10035`. Máy Admin nằm trong LAN gọi vòng ra WAN bị router chặn.
- **Fix đã áp dụng:**
  Sửa toàn bộ `mirotik1.taadaa.click:` thành IP LAN MikroTik nội bộ `192.168.110.2:`.
  Kill các tiến trình `download_by_niche.py` đang chạy ngậm cấu hình cũ trong RAM để service tự restart và nạp dải proxy mới.
