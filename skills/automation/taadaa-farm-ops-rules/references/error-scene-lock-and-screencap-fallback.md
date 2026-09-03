# Error Scene Lock Policy & SurfaceFlinger Protected Screen Fallback

## 1. Mandatory Device Hard Lock on Error (TTL 2 Hours / 7200s)

- **Rule:** Khi bất kỳ thiết bị/máy Android nào gặp lỗi trong quá trình chạy tự động (feed-session, login, reg, follow, v.v.) và rơi vào trạng thái `manual-needed` hoặc `fail`, hệ thống PHẢI tạo lock cứng `status: "blocked"` tại `~/.codex/device-locks/machine_<n>.lock.json` và `serial_<s>.lock.json`.
- **Mục đích:** Giữ nguyên vẹn hiện trường lỗi trên màn hình thiết bị, ngăn ngừa các chu kỳ cron tiếp theo hoặc các batch chạy tay khác can thiệp đè lên làm mất bằng chứng.
- **TTL Cooldown:** TTL tối đa **2 tiếng (7200 giây)**. Trong vòng 2 tiếng, nếu người dùng chưa can thiệp, lock reaper (`reap-dead-owner-locks`) mới được phép dọn dẹp để giải phóng máy.

## 2. Alert Without Screenshot Fallback (SurfaceFlinger PERMISSION_DENIED)

- **Hiện tượng:** Telegram nhận được alert text `🚨 [MÁY XX] DỪNG PHIÊN` nhưng không có ảnh screenshot Banner Đỏ đính kèm.
- **Nguyên nhân cốt lõi:**
  1. `send_farm_machine_alert` gọi lệnh `adb exec-out screencap -p` để chụp màn hình thiết bị.
  2. Khi ứng dụng đang hiển thị màn hình có cờ bảo mật `FLAG_SECURE` hoặc SurfaceFlinger DRM buffer được bảo vệ (thường gặp trên Samsung Knox), lệnh screencap trả về `W/SurfaceFlinger: FB is protected: PERMISSION_DENIED` và stdout chỉ chứa 12 bytes null (`0x00...`).
  3. Khi ảnh chụp trả về dưới 1000 bytes, `send_farm_machine_alert` fail-safe kích hoạt gửi tin nhắn text thuần để không làm mất thông báo lỗi.
- **Quy trình điều tra & khôi phục hiện trường:**
  - Không khởi động lại máy hay tắt app để tránh mất hiện trường.
  - Sử dụng dump UI XML qua ATX agent (`http://127.0.0.1:7912/dump/hierarchy`) hoặc `uiautomator dump` để đọc cấu trúc các phần tử UI text, resource-id, content-desc nhằm xác định màn hình và tài khoản đang dừng.
