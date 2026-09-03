# Case UI-28 & Fail-Closed Safe Back / Strict 4-Package Governance (2026-08-31 / 2026-09-01)

## 1. Clean FOLLOW_FAILED Exit Contract (Case UI-28 / Máy 14 `hong.bo.anh83`)
- **Triệu chứng:** Tài khoản đạt follow rate-limit / shadow drop trong ngày (`budget_used >= limit`), Path B phát hiện nút vẫn là "Follow" (`outcome == "failed"`).
- **Bug cũ:** `run_mode2` và `run_mode1` gán nhầm cờ `res.failed = True` thay vì `False`. `cleanup_after_result` thấy `failed=True` nên bỏ qua bước đóng app (`close_all_recent_apps`) và trả exit code `1`. Tiến trình cha `multi_machine_feed_session.py` thấy exit code `1` nên kích hoạt Farm Alert Telegram Đỏ và giữ hiện trường máy thật không cần thiết.
- **Chuẩn hóa chuẩn:**
  - Khi gặp `outcome == "failed"`, gán:
    - `res.status = STATE_FOLLOW_FAILED`
    - `res.failed = False`
    - `res.follow_failed = True`
    - `failed = False`
  - Khởi động (`follow_engine.py`) và kết thúc phiên: Nếu `state.follow_failed == True`, thực hiện ladder `_cleanup_follow_failed` đóng app sạch về Home, trả `failed=False, follow_failed=True, exit 0`.
  - Nếu ladder cleanup thất bại hoàn toàn (`close_all_recent_apps -> close_all_apps -> home -> press_home`), tự động promote thành `status="CLEANUP_FAILED", failed=True, exit 1` để Farm Alert giữ hiện trường.

## 2. Fail-Closed Safe Back in Mode 2 Path B
- **Nguyên tắc an toàn điều hướng:**
  1. Chỉ bỏ qua `adapter.back()` khi và chỉ khi **chứng minh độc lập qua UI dump thực tế** rằng màn hình **chưa từng rời khỏi follower list** trong toàn bộ các lần dump (`left_follower_list=False, dump_ok=False`) VÀ **không có bất kỳ dump exception/timeout nào** (`not had_dump_exception`).
  2. Nếu có bất kỳ dump nào rời khỏi list, hoặc dump bị exception/timeout, hoặc rơi vào màn hình không xác định (`unproven profile`/popup/feed), `adapter.back()` **bắt buộc phải được thực thi** để đưa UI trở về, tránh làm kẹt app ở màn hình profile gây nhiễm state cho các lượt follow tiếp theo.

## 3. Strict 4-Package TikTok Whitelist
- Toàn bộ codebase (`mode1_search_follow.py`, `mode2_follow_followers.py`, `verify_follow.py`, `selectors.py`) và test suite chỉ chấp nhận đúng 4 package TikTok chính thức:
  1. `com.ss.android.ugc.trill`
  2. `com.zhiliaoapp.musically`
  3. `com.ss.android.ugc.aweme`
  4. `com.ss.android.ugc.aweme.lite`
- Cấm dùng prefix `startswith` lỏng lẻo hoặc các biến thể thử nghiệm như `com.zhiliaoapp.musically.go` để ngăn chặn fail-open sang bàn phím hoặc app hệ thống.

## 4. Fail-Closed Parsing Error Handling
- Mọi hàm trích xuất selector/node từ XML uiautomator (`_exact_search_result_from_xml`, `_unique_search_submit`) phải bọc `except (ET.ParseError, Exception): return None` thay vì chỉ bắt `ET.ParseError`, đảm bảo bất kỳ lỗi layout/node tree bất thường nào cũng trả về `None` fail-closed thay vì crash unhandled exception qua khỏi recovery ladder.
