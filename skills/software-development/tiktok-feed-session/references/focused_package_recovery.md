# Fallback & Re-poll cho lỗi 'focused package unavailable'

## 1. Hiện tượng & Root Cause
- Khi lướt feed TikTok trên Android (đặc biệt các máy farm như máy 15, 46), trong quá trình transition giữa các video hoặc khi thiết bị đang bận render, lệnh `dumpsys window` / `dumpsys activity` có thể trả về `focused_package = None` tạm thời.
- **ATX & Parsing Root Causes:**
  + `get_focused_activity()` trong `flows/observe.py` ưu tiên `capture_atx_session_ui` (port 7912). Nếu atx-agent tạm ngắt hoặc lag không trả về XML, code rơi vào fallback `dumpsys window`.
  + `parse_focused_activity()` dùng regex `FOCUS_RE`. Khi output của dumpsys xuất hiện dưới dạng token Window đặc biệt (ví dụ `mFocusedApp=AppWindowToken{...}` hoặc `mCurrentFocus=Window{...}` trên một số dòng Samsung/Android 9/10 khi mở Splash/Profile), `FOCUS_RE` có thể không khớp được và trả về `{"package": None, "activity": None}`.
- Tại `python_runner/core/safety.py`, hàm `safety_check()` và `safety_check_attempt()` khi thấy `focus_pkg is None` đã lập tức trả về `SafetyCheckResult(SAFETY_FAILED, "focused package unavailable", ...)`.
- Hệ quả: `feed_swipe_smoke.py` (tại `_row_from_attempt`) hoặc `calibrate_screens.py` coi đây là lỗi fatal làm ngắt toàn bộ phiên nuôi acc với `stop_reason = "focused package unavailable"`, mặc dù app TikTok vẫn đang mở và hiển thị bình thường.

## 2. Giải pháp kỹ thuật chuẩn (Graceful Fallback & Re-poll)
1. **Re-poll ngắn trước khi kết luận**:
   - Khi phát hiện `focus_pkg is None`, thực hiện re-poll 1–2 lần (mỗi lần delay 0.5s – 0.8s) qua `get_focused_activity(ctx)`.
   - Nếu ở lần thử lại lấy được package hợp lệ của TikTok (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`), phục hồi `focus_pkg = expected`.
2. **Fallback qua UI XML Hierarchy**:
   - Trong `safety_check_attempt`, cần truyền `raw_xml` hoặc trích xuất package từ file XML (`xml_path`) nếu có.
   - Nếu XML hierarchy chứa package TikTok hoặc các text đặc trưng của feed (e.g. `"Đề xuất"`, `"Bạn bè"`), phục hồi `focus_pkg = expected`.
3. **Graceful Handling tại Caller (`feed_swipe_smoke.py`)**:
   - Khi nhận `safety.reason == "focused package unavailable"` nhưng màn hình được phân loại vẫn là TikTok feed hợp lệ (`for_you`, `following`, `friends`, `home`), không coi là fatal abort mà ghi nhận cảnh báo và thử lại swipe tiếp theo hoặc trigger recovery focus thay vì dừng cả session.

## 3. Quy tắc tra cứu mã nguồn
- Tuyệt đối CẤM quét đĩa diện rộng bằng `find /d/Taadaa` vì sẽ gặp thư mục `.tmp-pytest-agent-loop` gây timeout 900s.
- Mã nguồn feed runner luôn nằm cố định tại: `D:\Taadaa\tiktok-luot nuoi acc\python_runner\`.
