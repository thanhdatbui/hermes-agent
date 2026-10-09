# Case 112: Hạ Cấp An Toàn (Degraded) Khi Feed Confirmed Nhưng UI XML Gặp ATX_SESSION_UNAVAILABLE

## Bối cảnh & Hiện tượng (2026-09-05, Máy 41)
- Thiết bị: Máy 41 (`ce031823f9b1903c01`, Nick `pegsofuh038`).
- Triệu chứng: Dừng phiên feed session với thông báo:
  `feed marker confirmed but XML unavailable: ATX_SESSION_UNAVAILABLE`
- Hiện trường máy thật: TikTok đang ở màn hình feed Đề xuất (For You), video và các nút tương tác hiển thị bình thường.

## Nguyên nhân cốt lõi
1. Khi toàn bộ farm chuyển sang 100% ATX session dump (`automation_core.persistent_ui.capture_atx_session_ui`), nếu stub ATX gặp glitch sau retry và reset, `core/ui_capture.py` ném ngoại lệ `UIDumpError("ATX_SESSION_UNAVAILABLE")`.
2. Hằng số `FEED_CONFIRMED_XML_DEGRADED_ERRORS` trong `python_runner/flows/feed_swipe_smoke.py` chỉ định nghĩa các mã lỗi uiautomator shell cũ:
   ```python
   FEED_CONFIRMED_XML_DEGRADED_ERRORS = {
       "uiautomator_idle_state_error",
       "uiautomator_null_root_node",
       "ui_dump_command_failed",
       "ui_dump_failed",
       "ui_dump_file_missing",
   }
   ```
3. Trong hàm `_row_from_attempt`, khi `_is_feed_confirmed(attempt)` xác nhận feed qua screenshot marker (`for-you`, `home`, feed controls), script kiểm tra `xml_error in FEED_CONFIRMED_XML_DEGRADED_ERRORS`. Do thiếu `"ATX_SESSION_UNAVAILABLE"` và `"atx_session_unavailable"`, điều kiện này trả về `False` -> flow rơi xuống nhánh `failed` thay vì `ExitStatus.DEGRADED.value` (`"feed confirmed by screenshot marker but XML unavailable: ATX_SESSION_UNAVAILABLE"`).

## Giải pháp chuẩn hóa
1. Bổ sung `atx_session_unavailable` và `ATX_SESSION_UNAVAILABLE` vào `FEED_CONFIRMED_XML_DEGRADED_ERRORS`.
2. Chuẩn hóa kiểm tra case-insensitive (`xml_error.lower() in FEED_CONFIRMED_XML_DEGRADED_ERRORS`) tại tất cả các điểm đối chiếu trong flow (`_capture_retry_needed`, `_row_from_attempt`, `_recover_known_feed_tab_drift`, `_run_after_swipes_home_guard`).
3. Viết unit test xác thực `test_feed_confirmed_atx_session_unavailable_degrades_instead_of_failing` trong `test_feed_session_smoke.py`.
