# Navigation Launcher Focus Auto-Relaunch & OOM Resilience (2026-08-23)

## 1. Triệu chứng & Bối cảnh
- Alert: `🚨 [MÁY XX] DỪNG PHIÊN` / `Lý do: TikTok focus lost`
- Ảnh hiện trường: Thiết bị dừng ở Android Launcher (`com.sec.android.app.launcher`) với hình nền Samsung Galaxy S7.
- Bối cảnh: Samsung S7 (4GB RAM) khi lướt feed tải video liên tục khiến RAM bị đẩy lên cao, Low Memory Killer (LMK) của Android tự kill tiến trình TikTok và văng về Launcher. Dọn cache ban đêm chỉ giải phóng ROM/bộ nhớ rác, không ngăn được RAM tăng trong phiên.

## 2. Quy tắc Reboot vs Force-Stop
- **KHÔNG reboot thiết bị trước mỗi phiên:**
  - Khởi động lại S7 mất 60–90 giây, làm nghẽn hàng đợi ADB với farm 160 máy.
  - Reboot làm sập và phải khởi động lại `atx-agent` / uiautomator, VPN/ViChanger, dễ dính lỗi `ViChanger GET_IP failed` hoặc rớt kết nối ADB.
  - `am force-stop` giải phóng 100% RAM của app ngay lập tức trong 0.1s, không cần reboot phần cứng.

## 3. Kiến trúc Auto-Relaunch trong Navigation & Preflight
- Trước đây: `_recover_post_swipe_launcher_focus` chỉ bọc quanh bước post-swipe. Khi bấm điều hướng (chuyển tab Hồ sơ / Đề xuất), nếu văng Launcher thì `tap_navigation_target` hoặc `_maybe_recover_navigation_from_add_phone` fail-closed ngay.
- Giải pháp chuẩn:
  - Trong `_maybe_recover_navigation_from_add_phone` (`python_runner/flows/feed_swipe_smoke.py`), khi `captured` khớp `_is_launcher_focus_loss`:
    1. Gọi `force_stop_and_relaunch_tiktok` với `after_launch_delay_seconds = 10.0s`.
    2. Chờ 2s để UI ổn định.
    3. Trả về `retry_navigation()` để thực hiện lại cú tap điều hướng vào tab mong muốn.
  - Tránh dừng phiên oan uổng khi TikTok chỉ bị văng nhẹ hoặc trễ tải intent.
