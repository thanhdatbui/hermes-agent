# Case 93: Startup Splash & Loading Recovery Under MainActivity Focus

## Bối cảnh & Hiện tượng
Khi TikTok khởi động (cold-start) trên các dòng máy Android/Samsung, ứng dụng hiển thị màn hình Splash / Logo TikTok trên nền đen. Trong thời điểm này:
- WindowManager của Android có thể chuyển trạng thái focus sang `MainActivity` (`com.ss.android.ugc.trill.main.MainActivity` / `com.ss.android.ugc.aweme.main.MainActivity`) trước khi giao diện Feed hoặc video đầu tiên được render xong.
- UI Dump (XML) trong thời gian render này rất thưa (sparse) hoặc rỗng, không chứa các marker của Home/For You/Profile/Friends. Trình phân loại XML trả về `unknown`.
- Ảnh chụp màn hình (PNG) của màn splash/logo có dung lượng 100KB–800KB (lớn hơn ngưỡng `80_000` bytes).

## Anti-Pattern cần tránh
1. **Size-gating cứng nhắc trên `detected == unknown`:** Dùng điều kiện `0 < screenshot_size < 80_000` để chặn luồng retry của `unknown` khiến mọi lần khởi động chậm trên `MainActivity` bị fail-closed ngay ở attempt 1 với alert `unknown TikTok state`.
2. **Chỉ exempt `SplashActivity`:** Giả định splash screen chỉ xuất hiện khi `focused_activity` chứa `"splash"`. Thực tế `MainActivity` nhận focus từ rất sớm trong khi màn hình vẫn đang kẹt splash.
3. **Quên `tiktok_pkgs` definition trong slow capture retry:** Dẫn đến `NameError` crash khi capture deadline bị vượt quá.
4. **Cờ `popup_type` chặn launcher recovery sau dismiss:** Giữ cờ `packageinstaller_permission` khiến `_is_launcher_focus_loss` bị vô hiệu hóa sau khi đã tap từ chối quyền.

## Pattern chuẩn (Best Practice)
1. **Bounded Retry cho toàn bộ `_has_tiktok_startup_focus`:** Khi package TikTok có focus và activity thuộc nhóm khởi động (`splash`, `main`, `aweme`, `tiktok`), nếu `detected == unknown` thì luôn trả về `True` trong `_is_startup_loading_retry_row` để cho phép vòng lặp startup retry tiếp tục:
   - Chờ `BASELINE_STARTUP_RETRY_DELAY_SECONDS = 3.0` mỗi attempt.
   - Sau `LOADING_RESTART_THRESHOLD = 5` attempts kẹt liên tiếp, tự động gọi `force_stop_and_relaunch_tiktok` để giải cứu app.
   - Giới hạn tối đa `BASELINE_STARTUP_RETRY_ATTEMPTS = 20` attempts để fail-closed an toàn nếu app bị hỏng hoàn toàn.
2. **Kiểm tra `not row.get("popup_dismissed")` trong `_is_launcher_focus_loss`:** Đảm bảo sau khi dialog quyền Android bị từ chối và TikTok tự thoát về launcher, runner tự động kích hoạt relaunch về TikTok.
