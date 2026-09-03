# Chẩn đoán lỗi Swipe Recovery Pass trên App thứ 3 cướp Focus (2026-08-24)

## Hiện tượng & Sự cố thực tế (Máy 46 - 24/08)
- **Script:** `multi-machine-feed-session` / `feed_swipe_smoke.py`.
- **Thông báo Farm Alert:** `🚨 [MÁY 46] DỪNG PHIÊN - Lý do: swipe recovery passed stuck screen`.
- **Hiện trạng máy:** Đang hiển thị ứng dụng Danh bạ / Điện thoại (`GẦN ĐÂY` / `DANH BẠ`, `Không có cuộc gọi và tin nhắn gần đây`), không phải ứng dụng TikTok. Trạng thái giữ hiện trường: `🟡 GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`.

## Phân tích Call Chain & Root Cause
1. **App ngoài cướp Focus hoặc điều hướng nhầm:**
   - Trong quá trình chạy hoặc mở popup, ứng dụng hệ thống (như Contacts/Dialer `com.samsung.android.dialer` / `com.samsung.android.contacts` hoặc Outlook) chiếm foreground.
2. **Cơ chế Swipe Recovery kích hoạt:**
   - Flow nhận thấy màn hình trước đó rơi vào trạng thái `failed` / `manual-needed`.
   - Hàm `_swipe_recovery_on_stuck(ctx, row, artifact_prefix, step)` được gọi để vuốt 2 lần cứu kẹt.
3. **Lỗ hổng đánh giá Recovery khi thiếu kiểm tra Focus Package:**
   - Sau khi vuốt và chụp lại màn hình qua `capture_calibration_attempt()`, `detected` từ classifier trả về màn hình không có marker nhạy cảm (không phải `login`, `verification`, `captcha`, `manual_challenge`).
   - `_swipe_recovery_on_stuck()` chỉ kiểm tra `detected and detected not in SENSITIVE_SCREENS` mà **không kiểm tra `focus_package == expected_package`**.
   - Do đó, hàm này gán nhầm `row["status"] = ExitStatus.SUCCESS.value`, `row["safety_status"] = "ok"`, `row["safety_reason"] = "swipe recovery passed stuck screen"`.
4. **Dừng phiên tại Guard tiếp theo:**
   - Khi row tiếp tục đi vào `ManualReasonGuard` hoặc các bước kiểm tra an toàn / điều hướng tiếp theo, hệ thống phát hiện TikTok đã mất focus hoàn toàn và kích hoạt dừng phiên an toàn, giữ nguyên hiện trường với lý do ghi nhận từ row trước: `swipe recovery passed stuck screen`.

## Quy tắc Invariant & Khắc phục
1. **Kiểm tra Focus Package trong Swipe Recovery:**
   - Mọi cơ chế `_swipe_recovery_on_stuck` bắt buộc phải xác nhận `focused_package == expected_package` (hoặc `_is_launcher_focus_loss` = False) trước khi kết luận đã recover thành công.
   - Nếu `focused_package != expected_package`, không được coi là đã qua màn hình kẹt về Feed TikTok.
2. **Phân biệt lỗi Feed kẹt với App ngoài đè màn hình:**
   - Khi alert dừng phiên báo `swipe recovery passed stuck screen` nhưng ảnh chụp là app ngoài (Danh bạ, Cuộc gọi, Cài đặt, Outlook), nguyên nhân gốc là **Third-party Focus Loss**, không phải video feed bị kẹt.
