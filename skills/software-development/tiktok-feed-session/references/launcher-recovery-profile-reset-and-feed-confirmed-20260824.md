# Launcher Focus Recovery: Mid-Session Profile Reset & Feed Confirmation Contract (2026-08-24)

## 1. Hiện tượng & Incident (Máy 29 - 2026-08-24)
- **Cảnh báo Telegram:** `[MÁY 29] DỪNG PHIÊN • Script: multi-machine-feed-session • Tài khoản: chauuyen0207 • Lý do: profile verification mismatch: profile account mismatch • Trạng thái: GIỮ HIỆN TRƯỜNG`.
- **Hiện trường UI XML & Screenshot:** Màn hình Profile hiển thị tài khoản `@linhtrinh446` (Khánh Linh - Slot 1) trong khi tài khoản được giao chạy theo workbook là `chauuyen0207` (Slot 2).

## 2. Phân tích nguyên nhân gốc rễ (Root Cause)

### A. Bằng chứng Preflight Switch thành công vs Hiện tượng Session Rollback sau Force-Stop
1. **Giai đoạn Preflight (06:04 - 06:05):**
   - Ban đầu mở Profile: ghi nhận `@linhtrinh446` (Slot 1).
   - Mở Switcher: chọn `chauuyen0207` (Slot 2).
   - Xác nhận chuyển đổi (`profile_preflight_verify_1_identity_guard`): UI XML và ảnh chụp màn hình ghi nhận **đã chuyển sang `@chauuyen0207` thành công 100%** (0 follower, 3 following, 1 video 98 view).
2. **Giai đoạn lướt Feed (06:05 - 06:15):**
   - Thực hiện trơn tru các lượt swipe 1 đến 7 trên phiên của `chauuyen0207`.
3. **Mất focus và Cold Restart (06:16):**
   - Tại lượt swipe 8, máy bị rơi focus sang `com.android.systemui`.
   - Cơ chế `_recover_post_swipe_launcher_focus` thực thi `am force-stop` và launch lại qua `monkey -p com.ss.android.ugc.trill`.
4. **Cơ chế Rollback tài khoản của TikTok khi bị kill đột ngột:**
   - Trên TikTok Android, khi chuyển tài khoản qua giao diện in-app, state session/token đồng bộ xuống database cục bộ (SQLite/SharedPreferences). Nếu app bị kill đột ngột bằng `am force-stop` trước khi hoàn tất vòng đồng bộ disk hoặc khi `monkey` gửi intent mặc định của Launcher, TikTok sẽ khởi động lại với tài khoản mặc định/chính (Slot 1 - `@linhtrinh446`).
   - Sau đó tại Swipe 9, app mở thẳng vào tab Hồ sơ của `@linhtrinh446`, dẫn đến bước `verify_profile` cuối phiên phát hiện `@linhtrinh446` $\neq$ `chauuyen0207` và kích hoạt dừng an toàn `profile verification mismatch`.

### B. Bug đối số `_is_feed_confirmed` trong Launcher Recovery
1. Trong `_recover_post_swipe_launcher_focus` (`feed_swipe_smoke.py:5981`):
   ```python
   recovered = recaptured.get("status") in {ExitStatus.SUCCESS.value, ExitStatus.DEGRADED.value} and _is_feed_confirmed(
       recaptured,
       expected=expected,
   )
   ```
2. `recaptured` là dictionary cấp `row` do `_capture_step` trả về (chứa `detected`, `status`, `attempts=[...]`), trong khi `_is_feed_confirmed()` mong đợi một `attempt` dictionary (chứa `detected_screen`, `image_selected_top_tab`, `home_selected`, `for_you_selected`).
3. `detected_screen_from_attempt(recaptured)` trả về `None`, dẫn đến `_is_feed_confirmed(recaptured)` luôn đánh giá `False`, ghi log sai `result="failed", error="feed not confirmed after launcher recovery"` dù recapture thực tế đã trở lại feed `for-you` thành công.

## 3. Quy tắc & Giải pháp chuẩn

1. **Khôi phục Profile sau Mid-Session Relaunch:**
   - Trong `_recover_post_swipe_launcher_focus` hoặc bất kỳ handler nào thực hiện `force_stop_and_relaunch_tiktok` giữa phiên:
   - Nếu tài khoản phiên chạy không phải slot 1 mặc định (đã qua `verify_and_switch_profile` thành công ở preflight), bắt buộc phải re-invoke lại `verify_and_switch_profile()` (hoặc kiểm tra/switch lại nick) trước khi tiếp tục các lượt swipe kế tiếp.
2. **Chuẩn hóa đối số `_is_feed_confirmed`:**
   - Khi gọi `_is_feed_confirmed` từ một `row` capture, truyền `recaptured["attempts"][-1]` (hoặc kiểm tra cả row-level `detected` và attempt-level markers) để tránh false-negative recovery status.
