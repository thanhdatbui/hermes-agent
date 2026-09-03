# TikTok Focus Loss, OOM RAM Inflation, and Worker Triage (2026-08-23)

## 1. Bản chất lỗi Focus Lost vs Dọn Cache định kỳ
- **Cache dọn ban đêm (ROM/Storage):** Script `cron_clear_tiktok_cache.py` chạy lúc 04:00 AM kích hoạt widget "Xóa bộ nhớ đệm" (810, 260) để dọn file rác/cache lưu trữ trên bộ nhớ trong (ROM).
- **RAM phình trong phiên (Runtime RAM):** Khi lướt feed, TikTok stream và render video liên tục trực tiếp trên RAM. Thiết bị Samsung Galaxy S7 (RAM 4GB, thực tế trống ~1.2–1.5GB cho user app) dễ bị đầy RAM sau 10–15 phút lướt.
- **Hệ quả:** Trình quản lý bộ nhớ Android (Low Memory Killer - LMK) kill tiến trình TikTok ngầm và đẩy máy về Launcher (`com.sec.android.app.launcher`). Dọn cache ban đêm không ngăn được việc đầy RAM khi stream video mới trong phiên.

## 2. Phân biệt tải Concurrency (PC Worker vs Device S7)
- **Tăng worker trên PC (`max_workers`):** Tăng tải CPU máy tính chủ, gây nghẽn hàng đợi ADB socket (`adb command timed out`) và trễ phản hồi RPC của ATX.
- **Thiết bị S7 tự văng app:** 100% do tài nguyên phần cứng nội tại của box S7 (OOM RAM / LMK / CPU throttling khi nóng máy), không phải do worker PC "đè nặng" lên RAM điện thoại.

## 3. Kiến trúc phục hồi Launcher Focus (Relaunch vs Fail-Closed)
- **Pha lướt Feed (`feed_swipe_smoke.py`):** Đã có cơ chế `_recover_post_swipe_launcher_focus` tự động force-stop và relaunch TikTok 1 lần qua monkey/am start nếu vuốt xong phát hiện văng về Launcher.
- **Pha Preflight & Navigation (`calibrate_screens.py` / `verify_profile`):** Áp dụng nguyên tắc `fail-closed` (`verify_tiktok_focus_after_navigation`). Nếu văng ra SystemUI/Launcher khi đang chuyển tab hoặc đọc hồ sơ, script dừng ngay và kích hoạt `GIỮ HIỆN TRƯỜNG` để tránh đọc nhầm XML hoặc thao tác sai nick.
- **Hướng mở rộng nếu cần:** Relaunch có kiểm soát (tối đa 1 lần, delay 5–8s chờ render) phải đặt ở tầng caller cấp cao (preflight/profile flow), không được nhét vào hàm tiện ích cấp thấp `tap_navigation_target`.
