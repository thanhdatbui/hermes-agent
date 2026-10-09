# Quy Định Timeout 15 Phút & Force-stop Về Home Toàn Diện (Chốt 20/08/2026)

## 1. Bối Cảnh & Mục Tiêu
- Để máy ngâm ở màn hình lỗi quá lâu khiến thiết bị sáng màn hình liên tục, dễ bị TikTok gắn cờ bot/checkpoint và gây chai pin/nóng máy.
- Cần cơ chế dọn dẹp an toàn có giới hạn thời gian (15 phút) cho mọi luồng chạy trên farm (Feed, Follow, Upload, Reg, Login).

## 2. Quy Tắc Hoạt Động Cụ Thể

### A. Luồng Follow & Upload Hook
- Timeout cứng 900s (15 phút) qua `subprocess.TimeoutExpired` (Commit `c022fac`).
- Xử lý khi timeout:
  1. Kill subprocess python đang chạy.
  2. `am force-stop com.ss.android.ugc.trill`
  3. `input keyevent 3` (KEYCODE_HOME)
  4. Đặt cooldown riêng cho nick đó trong ngày.

### B. Luồng Lướt Feed Session (Nuôi Acc)
- Khi gặp màn hình kẹt / popup lạ / fail:
  - Ban đầu: Giữ nguyên hiện trường (`preserve_blocker_screen = True`) để AI Auto-Recovery vào phân tích ảnh/XML và vá code.
  - Sau 15 phút (900s): Nếu sau khi AI xử lý xong (worker feed không chạy tiếp) hoặc chưa có ai can thiệp -> BẮT BUỘC watchdog/cleanup timer tự động:
    1. `am force-stop com.ss.android.ugc.trill`
    2. `input keyevent 3` (KEYCODE_HOME)
    3. Đưa máy về Home an toàn, tránh ngâm sáng màn hình.

### C. Kết Thúc Toàn Diện Sau Các Hook (Teardown Invariant - Chốt 12/09/2026 Case 153)
- **Bối cảnh lỗi thực tế**: `feed_session_smoke` dọn về HOME nhưng các hook sau đó (`_run_follow_hook`, `_run_upload_hook`) mở lại TikTok/Gallery qua subprocess và khi kết thúc không đóng app, khiến màn hình bị ngâm ở feed/profile/gallery như bot.
- **Quy tắc bất biến**:
  1. Trong `_run_child` của `multi_machine_feed_session.py`, khối `finally:` TRƯỚC KHI nhả lease thiết bị bắt buộc phải gọi `_force_stop_tiktok_and_home(child_ctx, serial=account.serial)`.
  2. Bất kể phiên hoàn tất thành công, bị skip do đã upload, hay gặp lỗi ở bất kỳ hook nào: 100% thiết bị phải được `am force-stop` và gửi `input keyevent 3` về HOME launcher.
  3. Tuyệt đối không để máy treo ở video feed hay gallery sau khi ca chạy đã kết thúc.
