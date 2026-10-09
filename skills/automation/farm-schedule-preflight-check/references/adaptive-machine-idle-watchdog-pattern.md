# Quy Chuẩn Canh Máy Rảnh Động Bằng Watchdog (Adaptive Machine Idle Watcher)

Thay vì đoán mốc giờ tĩnh (dễ gây xung đột do ca nuôi kéo dài hoặc uiautomator reload), áp dụng mẫu Watchdog động:

1. **Chu kỳ quét:** Mỗi 3-5 phút (qua Cronjob `schedule: '*/5 * * * *'`).
2. **Kiểm tra Lock Vật Lý:** Quét trực tiếp `~/.codex/device-locks/machine_<M>.lock.json` và `serial_<SERIAL>.lock.json`. Bắt buộc không có PID nào đang sống ở trạng thái `running` / `queued_v2`.
3. **Kiểm tra Ca Nuôi Kế Tiếp:** Cách slot nuôi tiếp theo tối thiểu 60 phút.
4. **Tự Động Kích Hoạt & Nghiệm Thu:**
   - Acquire device lock với `user_authorized=True`.
   - Thực thi luồng chuẩn (Login OTP, 2FA, Reconcile).
   - Kiểm tra UI Switcher + Chụp ảnh nghiệm thu (`MEDIA:...`).
   - Đưa máy về Home an toàn (`LauncherActivity`) và giải phóng lock.
   - Gửi Farm Alert thông báo kết quả.
