# Gỡ bỏ ViChanger VPN & Modal Lưu và Đăng Avatar TikTok (2026-09-02)

## 1. Gỡ bỏ ViChanger VPN trên Farm Phone
- **Bối cảnh:** Toàn bộ phone farm đã chuyển sang định tuyến proxy dân cư qua MikroTik / Singbox và Wi-Fi access point, không còn cài đặt hoặc bật ứng dụng ViChanger VPN trực tiếp trên thiết bị Android.
- **Bẫy cũ:** Hàm `_require_vpn` trong `account_reconcile.py` và `account_inventory.py` (repo `tiktok-log-in`) gọi `require_android_vpn(adb, required=required)` dẫn đến việc ném ngoại lệ `AccountInventoryError: machine N: VICHANGER_VPN_NOT_CONNECTED` làm dừng phiên vô cớ.
- **Giải pháp:**
  - Trong `account_reconcile.py`: `_require_vpn` bypass kiểm tra app VPN trên máy.
  - Trong `account_inventory.py`: Bỏ `require_android_vpn` fail-closed gate.
  - Các script tuyệt đối không ép buộc `tun0` hay Android VPN package khi farm chạy qua Wi-Fi proxy.

## 2. Modal Xác nhận "Lưu và đăng" Avatar TikTok mới
- **Bối cảnh:** Sau khi chọn ảnh từ thư viện và chuyển sang màn hình Cắt ảnh (Crop):
  1. Uncheck checkbox *"Đăng ảnh này lên Nhật ký"* tại `(84, 1590)`.
  2. Tap nút **Lưu** tại `(792, 1794)` (`id/tv_confirm`).
- **Hiện tượng trôi avatar:** Sau khi bấm nút Lưu ở bước trên, TikTok KHÔNG lưu ngay mà bật một Modal trượt từ dưới lên thông báo: *"✨ Tôi vừa tải lên một ảnh hồ sơ mới... Tài khoản của bạn được đặt ở chế độ công khai..."*
- **Thao tác bắt buộc:**
  - Phải tap tiếp vào nút đỏ **`Lưu và đăng`** nằm trên modal này ở tọa độ **`(540, 1764)`** (bounds `[96, 1698][984, 1830]`, resource-id `s_l`).
  - Sau khi tap nút này và sleep 3-4s, màn hình sẽ quay trở lại `Sửa hồ sơ` với avatar mới đã được cập nhật thật.

## 3. Kiểm tra Gmail Live Siêu Tốc qua checkmail.live (Chrome CDP)
- Khởi chạy Chrome với profile Hermes:
  `C:\Program Files\Google\Chrome\Application\chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\Users\Kibe\AppData\Local\hermes\browser_profile`
- Kết nối Playwright qua `http://127.0.0.1:9222`, nạp email vào `window.editor.setValue(...)`, kích hoạt `btn-check.click()` và đọc `window.liveResultEditor.getValue()`.
- Trả kết quả `[Live]` / `[die]` trong vòng 1s-2s mà không cần mở app trên thiết bị điện thoại.
