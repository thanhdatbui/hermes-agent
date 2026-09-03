# Launcher Focus Loss Recovery Triage

## Bối cảnh & Hiện tượng
Trong flow `feed_swipe_smoke` và `multi_machine_feed_session`, khi phát hiện TikTok mất focus (`TikTok focus lost`) rơi về màn hình Launcher (ví dụ `com.sec.android.app.launcher`, `com.google.android.apps.nexuslauncher`...):
* **Nguyên nhân phổ biến**: Tràn RAM (Low Memory Killer / OOM) do lướt video liên tục, ANR hoặc xung đột dịch vụ nền Android.

## Quy trình Khôi phục 2 Tầng (`_recover_post_swipe_launcher_focus`)

### Tầng 1: Fast Relaunch (Khởi động lại App)
1. Kích hoạt `force_stop_and_relaunch_tiktok` (`am force-stop` -> `am start`).
2. Đợi `POST_SWIPE_LAUNCHER_RECOVERY_WAIT_SECONDS` (10s) để app nạp lại.
3. Polling kiểm tra `get_focused_activity` (3 lần x 2s delay) chống miss do Samsung S7 tải app chậm.
4. Recapture UI và xả popup nếu có (`drain_known_popups`) để xác nhận màn hình Feed For You (`_is_feed_confirmed`).
5. Nếu thành công -> chuyển trạng thái `VERIFIED_SUCCESS` và tiếp tục phiên lướt.

### Phạm vi bao phủ Recovery trong toàn bộ Flow
Cơ chế Launcher Recovery phải được bọc đồng bộ ở mọi khâu có nguy cơ văng app:
- Nhịp `before_swipe` (trước lượt vuốt đầu tiên: nếu mất focus về Launcher, bắt buộc kích hoạt `_recover_post_swipe_launcher_focus` trước khi vào `_swipe_recovery_on_stuck` để chống vuốt mù trên Launcher)
- Sau mỗi lượt swipe (`feed_swipe_smoke` main loop)
- Trong vòng lặp `loading_retry`
- Sau nhịp `_back_recheck`
- Trước và trong `_swipe_recovery_on_stuck` (nếu đang ở Launcher thì kích hoạt relaunch ngay thay vì vuốt mù trên Launcher)
- Trong bước đối soát hồ sơ `_verify_profile_after_session` (relaunch + retry `tap_navigation_target`)

## Bẫy Nhận Diện Sai Khi Văng Ra Launcher (False-Positive Traps)
1. **Va chạm Startup-Ad Image Classifier**:
   - Wallpaper/icon trên Launcher có thể làm `detect_startup_ad_splash` báo độ tin cậy cao (`manual-needed:startup-ad`).
   - BẮT BUỘC trong `_merge_xml_classification` phải kiểm tra `focused_package`: nếu là Launcher/SystemUI (`com.sec.android.app.launcher`, `systemui`...), cấm ghi đè phân loại ảnh thành `startup-ad` hay các marker in-app TikTok.
2. **Va chạm Search Landing Page**:
   - Thanh tìm kiếm của Launcher (`com.sec.android.app.launcher:id/app_search_edit_text`, text "Tìm trên điện thoại") rất dễ kích hoạt nhầm detector `search_landing_overlay` và `detect_search_landing_page`.
   - BẮT BUỘC bổ sung danh sách loại trừ Launcher (`com.sec.android.app.launcher`, `app_search_edit_text`, `Tìm trên điện thoại`) và chỉ match khi package là TikTok (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`).
3. **Swipe Recovery trên Launcher**:
   - Trong `_swipe_recovery_on_stuck`, nếu thiết bị đang ở Launcher, lệnh `input swipe` hoàn toàn vô nghĩa và sẽ làm cạn kiệt số lần retry rồi báo kẹt.
   - BẮT BUỘC kiểm tra `_is_launcher_focus_loss` trong `_swipe_recovery_on_stuck` để gọi `force_stop_and_relaunch_tiktok` trước/sau khi vuốt.

## Quy tắc Dọn Cache & Bộ Nhớ Đệm Farm (Tuyệt đối an toàn)
- **CẤM tuyệt đối**: Không chạy `pm clear` hay xóa dữ liệu thô qua ADB, sẽ làm văng toàn bộ phiên đăng nhập của tài khoản TikTok trên thiết bị.
- **Cách dọn cache chuẩn**: Sử dụng script UI widget `D:\Taadaa\automation-core\scripts\clear-tiktok-cache.py` (tương tác tự động với widget "Xóa bộ nhớ đệm" trên màn hình Home) để đưa cache về 0,0MB an toàn.

## Nguyên Tắc Bất Biến Chống Thao Tác Mù (Anti-Minefield Invariants)
1. **Kiểm tra Focus Chặt Chẽ Trước Khi Vuốt (Fail-Closed)**:
   - Trong `_swipe_recovery_on_stuck`, trước khi gửi bất kỳ lệnh `input swipe` nào, BẮT BUỘC kiểm tra `current_focus_pkg in tiktok_pkgs`. Nếu focus bị rỗng, unverified, hoặc rơi vào package ngoài (kể cả system dialogs), lập tức hủy (`return None` / fail-closed), tuyệt đối cấm fall-through để vuốt mù.
2. **Tái Kiểm Tra Focus Sau Khi Xả Popup (Post-Drain Verification)**:
   - Khi gọi `drain_known_popups` trong quy trình phục hồi Launcher, `drain_known_popups` thực hiện các thao tác UI và có thể làm đổi focus.
   - Chỉ đánh dấu `recovered = True` khi kết quả trả về vừa xác nhận Feed (`_is_feed_confirmed`), vừa thỏa mãn `status in {SUCCESS, DEGRADED}`, đồng thời kiểm tra lại `get_focused_activity` trực tiếp trên máy xác nhận app foreground vẫn là TikTok.
3. **Lọc Thông Báo Google Play Trên Status Bar Không Làm Mất Marker Nhạy Cảm**:
   - Khi lọc notification "Yêu cầu đăng nhập" của Google Play trên status bar trong `_is_sensitive`, chỉ loại bỏ các node XML thuộc `com.android.systemui` / `com.google.android.gms` nằm trong dải status bar ($y \le 100$) và áp dụng regex xóa cụm từ trên OCR.
   - Tuyệt đối KHÔNG xóa blanket toàn bộ các node ở đầu màn hình ($y \le 100$) vì sẽ làm mất các marker tiêu đề / cảnh báo đăng nhập thật sự của chính app TikTok.

### Tầng 2: Guarded Reboot & Chờ Gán VPN (Khởi động lại Thiết bị)
Nếu Tầng 1 thất bại (app crash lại ngay, treo splash, hoặc không focus được TikTok):
1. **Kiểm tra cờ an toàn**: Kiểm tra `getattr(ctx.adb, "_launcher_reboot_attempted", False) is True` để đảm bảo mỗi thiết bị chỉ reboot tối đa đúng 1 lần trong phiên.
2. **Kích hoạt Guarded Reboot**: Gọi `reboot_and_restore` từ `automation_core`:
   - Gửi lệnh reboot qua ADB và đợi thiết bị hoàn tất boot (`sys.boot_completed`).
   - Mở khóa màn hình qua `wait_until_unlocked`.
3. **Bắt buộc chờ gán & xác thực VPN**:
   - Sử dụng callback `wait_for_proxy_ready` kết hợp verifier `require_vichanger_connected`.
   - Đảm bảo 100% proxy-watcher đã kết nối lại VPN an toàn trước khi mở TikTok (ngăn chặn tuyệt đối rò rỉ Direct IP).
4. **Mở lại TikTok & Recapture Feed**:
   - Relaunch app TikTok với delay ổn định 10s.
   - Recapture UI và xác nhận màn hình Feed For You (`_is_feed_confirmed`).
   - Nếu đạt -> `VERIFIED_SUCCESS` và tiếp tục phiên lướt; nếu vẫn không đạt -> `FINAL_BLOCKED`.

## Cơ chế Fail-Closed khi Thất bại
Nếu cả 2 tầng recovery đều không khôi phục được màn hình Feed:
- Đánh dấu `FINAL_BLOCKED`.
- Chụp ảnh màn hình hiện trường gắn Banner Đỏ cảnh báo.
- Tạo lock giữ nguyên hiện trường thiết bị (TTL 2h) và dừng phiên để bảo vệ tài khoản.

## Pitfalls & Lưu ý Kỹ thuật khi Phát triển / Test
1. **Mock Truthiness Pitfall khi kiểm tra cờ device lock/reboot**:
   - Trên đối tượng `unittest.mock.Mock` (như `ctx.adb`), truy cập thuộc tính `getattr(ctx.adb, "_launcher_reboot_attempted", False)` sẽ trả về một child `Mock` (luôn `bool(Mock()) == True`), khiến nhánh `if not reboot_attempted:` bị bỏ qua sai lệch trong unit test.
   - **Cách fix chuẩn**: Luôn kiểm tra strictly `getattr(ctx.adb, "_launcher_reboot_attempted", False) is True` để phân biệt chính xác giá trị boolean `True` thật sự so với child Mock.
2. **Đường dẫn ADB khi chạy script ngoài PATH**:
   - Khi chạy trên Windows host farm, executable adb thường nằm tại `C:\Program Files (x86)\xiaowei\tools\adb.exe`. Khi gọi các helper từ `vpn_preflight` / `automation_core`, bắt buộc truyền đúng `adb_path` từ config thay vì giả định binary `adb` có sẵn trong global PATH.
