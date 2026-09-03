# Recovery: Máy dừng phiên do rơi về Home screen (feed not confirmed; swipe recovery still stuck)

*Ghi nhận: 2026-08-22 (Máy 23 `thaidiem19` / `ce0117113acfd47e0c`)*

## 1. Hiện tượng & Root Cause
- **Báo cáo alert từ farm bot**:
  ```
  🚨 [MÁY 23] DỪNG PHIÊN
  • Script: multi-machine-feed-session
  • Tài khoản: thaidiem19
  • Lý do: feed not confirmed; swipe recovery (2 swipes) still stuck
  • Trạng thái: GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ
  ```
- **Nguyên nhân**:
  - Khi bắt đầu hoặc trong quá trình chạy phiên, TikTok bị mất focus / trễ khởi động rơi về màn hình chính Android (Launcher Home screen).
  - Bộ phân loại ảnh (`detect_startup_ad_splash`) phân tích hình ảnh Launcher và nhận diện nhầm các biểu tượng ứng dụng / độ tương phản của hình nền là `startup-ad`.
  - Cơ chế swipe recovery (`_swipe_recovery_on_stuck`) cố thực hiện 2 lần vuốt trên màn hình chính nhưng không thể vào được TikTok feed -> báo lỗi `feed not confirmed; swipe recovery (2 swipes) still stuck` và giữ hiện trường.

## 2. Quy trình xử lý phục hồi live
1. **Kiểm tra trạng thái ATX & ADB**:
   - Sử dụng `capture_atx_session_ui` (automation-core) để kiểm tra socket ATX agent trên máy. Nếu ATX kẹt, gọi `reset_atx_agent(adb)`.
2. **Khởi động lại ứng dụng TikTok**:
   ```bash
   adb -s <serial> shell "monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1"
   ```
3. **Đợi UI ổn định & Verify qua ATX XML**:
   - Chờ 3 giây để TikTok splash hoàn tất và load feed.
   - Capture ATX XML (`capture_atx_session_ui` / `classify_tiktok_screen`): đảm bảo `detected_screen` xác nhận là `for-you` hoặc `home`.
4. **Chụp screencap & Báo cáo**:
   - Chụp ảnh màn hình mới nhất và gửi kèm `MEDIA:<path>` cho user.
   - Kiểm tra thư mục device locks (`~/.codex/device-locks/`) để đảm bảo không còn file lock kẹt của máy.
