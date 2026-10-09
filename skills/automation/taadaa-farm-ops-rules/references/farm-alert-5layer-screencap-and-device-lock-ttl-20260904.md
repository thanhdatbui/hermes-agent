# Farm Alert 5-Layer Screencap Fallback & Device Lock 2H Policy (2026-09-04)

## 1. Rule Lock cứng khi gặp lỗi máy (TTL 2h)
- **Hành vi bắt buộc:** Khi bất kỳ máy nào gặp lỗi dừng phiên (`manual-needed`, `blocked-vichanger-vpn`, `fail`, popup lạ, sai account, navigation target not found...), script hoặc agent BẮT BUỘC phải tạo lock cứng giữ hiện trường:
  - File: `~/.codex/device-locks/machine_<N>.lock.json`
  - Trường dữ liệu: `status: "blocked"`, `ttl: 7200` (2 giờ = 7200s), `reason: "<mô tả lỗi chi tiết>"`.
- **Mục đích:** Giữ nguyên màn hình lỗi trên thiết bị, ngăn chặn các chu kỳ cron / runner tiếp theo nhảy vào tương tác đè làm mất dấu vết.
- **Thời hạn tự nhả (TTL):** Tối đa 2 tiếng. Trong vòng 2 tiếng nếu user/agent chưa can thiệp, watchdog (`watch_device_locks.py` / `reap-dead-owner-locks`) mới được phép tự động nhả lock để giải phóng máy.

## 2. Cơ chế Alert Multi-layer Screencap Fallback (5 Tầng)
- **Vấn đề đã khắc phục:**
  - Lệnh `adb exec-out screencap -p` có thể bị SurfaceFlinger từ chối do bảo vệ framebuffer (`FB is protected: PERMISSION_DENIED` -> trả về 12 byte `0x00...`), hoặc transport ADB bị nghẽn dẫn đến timeout.
  - Code alert cũ gửi text thuần khi không lấy được ảnh, gây thiếu hiện trường.
- **Kiến trúc 5 tầng chuẩn (`automation_core.alerts`):**
  1. **Tầng 1 (Primary Live):** `adb exec-out screencap -p` (10s timeout).
  2. **Tầng 2 (ATX-Agent / UiAutomator2 Direct JSON-RPC):** Port forward `7912`/`9008`. Nếu uiautomator stub chưa chạy (trả về 502 Bad Gateway), gửi `POST /uiautomator` đánh thức tiến trình, sau đó gọi JSON-RPC `takeScreenshot` bypass SurfaceFlinger.
  3. **Tầng 3 (ADB Reconnect + ATX):** Khi ADB transport bị timeout/nghẽn, gọi `adb -s <serial> reconnect` (chỉ reset kết nối thiết bị đó) rồi retry ATX takeScreenshot.
  4. **Tầng 4 (Shell SDCard):** Chụp qua file đệm `/sdcard/__alert_screencap.png` rồi `cat` stream về máy tính.
  5. **Tầng 5 (Artifact Fallback):** Quét tìm file `screen.png` mới nhất trong thư mục artifact/run gần nhất của máy đó.
- **Banner Đỏ:** Luôn phủ Banner Đỏ trên đầu ảnh với thông tin `[MAY <N>] - HH:MM:SS DD/MM` trước khi dispatch lên Telegram.
