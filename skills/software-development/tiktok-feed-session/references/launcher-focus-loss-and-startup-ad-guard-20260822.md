# Launcher Focus Loss vs Startup Ad False-Positive Recovery (2026-08-22)

## 1. Triệu chứng
- Phiên nuôi acc `multi-machine-feed-session` dừng với lý do: `feed not confirmed; swipe recovery (2 swipes) still stuck` và giữ hiện trường.
- Ảnh screencap cho thấy máy đang ở màn hình chính Android (Launcher / Home Screen) với hình nền Samsung Galaxy S7 (sóng xanh dương đậm).

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Mất focus / crash foreground:** TikTok bị trễ khởi động hoặc bị văng ra màn hình chính (`com.sec.android.app.launcher`).
2. **False-Positive Image Heuristic (`detect_startup_ad_splash`):** Thuật toán nhận diện ảnh dựa trên tỷ lệ màu sáng/tối/tương phản (`region_stats`) bị kích hoạt nhầm bởi các mảng màu trên hình nền Samsung và icon ứng dụng, dẫn đến kết luận sai là `manual-needed:startup-ad` (quảng cáo mở đầu TikTok).
3. **Chặn cơ chế Relaunch:** Do nhãn `startup-ad` bị xem là popup nhạy cảm/cần xử lý trong app, hệ thống không kích hoạt cơ chế hồi phục Launcher (`_is_launcher_focus_loss` -> `prepare_tiktok` / `monkey -p com.ss.android.ugc.trill`) mà rơi vào nhánh vuốt retry 2 lần trên Home screen rồi dừng phiên.

## 3. Quy tắc & Giải pháp chuẩn
1. **Kiểm tra Package Foreground trước khi quét ảnh:**
   - Trong `flows/calibrate_screens.py`, `detect_startup_ad_splash` **BẮT BUỘC** chỉ được gọi khi `focused_package` là TikTok (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`) hoặc `None`. Tuyệt đối không phân loại `startup-ad` khi máy đang ở Launcher / SystemUI.
2. **Mở rộng nhận diện Launcher Focus Loss:**
   - Trong `flows/feed_swipe_smoke.py`, hàm `_is_launcher_focus_loss` phải kiểm tra `focus_package != expected_package` và kích hoạt Relaunch ngay khi rơi vào `LAUNCHER_PACKAGES`, `com.android.systemui`, package chứa chuỗi `launcher` hoặc `focus_package` rỗng.
3. **Độ trễ sau launch:**
   - Đảm bảo delay đủ để TikTok trên máy yếu tải xong view trước khi dump UI XML.
