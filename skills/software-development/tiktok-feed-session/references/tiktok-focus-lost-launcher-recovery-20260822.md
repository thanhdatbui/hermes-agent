# TikTok Focus Lost on Launcher Triage & Recovery

## 1. Triệu chứng & Báo động
- Farm Alert Telegram:
  - `🚨 [MÁY XX] DỪNG PHIÊN`
  - `• Script: multi-machine-feed-session`
  - `• Lý do: TikTok focus lost`
  - `• Trạng thái: 🟡 GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`
- Ảnh đính kèm: Thiết bị dừng ở Android Launcher (`com.sec.android.app.launcher`) với hình nền Samsung Galaxy S7.

## 2. Phân tích nguyên nhân gốc rễ
1. **OS Kill / OOM Crash:** Thiết bị Samsung Galaxy S7 (RAM 4GB, Android 8/Exynos) chạy feed hoặc chuyển đổi nhiều nick trong thời gian dài khiến bộ nhớ đệm tăng cao; hệ thống kích hoạt Low Memory Killer (LMK) đóng ngầm TikTok và văng về Launcher.
2. **Intent Launch Stalled/Dropped:** Sau khi chuyển nick hoặc preflight, lệnh launch qua `monkey` hoặc `am start` mất nhiều thời gian hơn budget timeout do tải CPU máy cao, dẫn đến `safety_check()` đọc `focused_package` đúng lúc package đang là Launcher (`com.sec.android.app.launcher` hoặc rỗng).
3. **Thiếu cơ chế retry relaunch ở các hook trung gian:** Cơ chế phục hồi launcher (`_recover_post_swipe_launcher_focus`) chỉ bọc quanh bước vuốt (post-swipe), trong khi các giai đoạn baseline, account switch, profile check nếu bị văng focus sẽ fail-closed ngay lập tức.

## 3. Quy trình chẩn đoán & Xử lý
1. **Kiểm tra hiện trường:** Xác nhận `focused_package` qua ATX hoặc ADB (`dumpsys window | grep -E "mCurrentFocus|mFocusedApp"`). Nếu là launcher và không có popup hệ thống chặn:
2. **Dọn dẹp bộ nhớ đệm phòng ngừa OOM crash:**
   - Khi thiết bị bị văng Launcher do RAM đầy/cache phình to, **BẮT BUỘC** clear cache qua widget *"Xóa bộ nhớ đệm"* của TikTok ở góc phải trên cùng màn Home (tọa độ chuẩn `810, 260` trên Samsung S7 1080x1920).
   - Chạy script chuẩn: `python D:/Taadaa/automation-core/scripts/clear-tiktok-cache.py --machine <M> --serial <SERIAL> --widget-pos 810,260`.
   - Tuyệt đối không dùng `pm clear` (gây mất phiên/văng tài khoản).
3. **Xử lý nhanh tại chỗ:**
   - Force-stop và mở lại app TikTok qua monkey / ATX.
   - Giải phóng máy và nhả lock theo đúng STOP GATE.
4. **Cải tiến logic code tự động (Code Fix):**
   - Đảm bảo `_is_launcher_focus_loss` được gọi trước khi kết luận `TikTok focus lost`.
   - Cung cấp delay buffer an toàn (`POST_SWIPE_LAUNCHER_RECOVERY_WAIT_SECONDS = 10.0s`, `after_launch_delay_seconds = 10.0s`) trên thiết bị Samsung Galaxy S7 để tránh drop intent launch khi tải cao.
   - Cho phép retry launch (tối đa 2 lần) với delay buffer thích hợp trước khi fail-closed.
