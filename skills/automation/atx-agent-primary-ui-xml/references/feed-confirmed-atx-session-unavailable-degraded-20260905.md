# Feed Confirmed ATX Session Unavailable Degraded Handling (Case 110, 2026-09-05)

## Hiện tượng lỗi (Máy 41, ce031823f9b1903c01, nick pegsofuh038)
- Alert: `[FARM ALERT: MÁY 41] DỪNG PHIÊN`
- Triệu chứng: `feed marker confirmed but XML unavailable: ATX_SESSION_UNAVAILABLE`
- Hiện trường: TikTok đang mở Trang chủ (Tab Đề xuất / For You), video và UI feed (like/comment/share/bottom bar) hiển thị rõ ràng trên màn hình.

## Nguyên nhân cốt lõi
1. Khi farm chuyển dịch 100% sang `atx_session` UI capture (port 7912), nếu socket JSON-RPC bị nghẽn hoặc UiAutomator service bận do video TikTok đang phát liên tục trên Samsung S7, `core/ui_capture.py` ném `UIDumpError("ATX_SESSION_UNAVAILABLE", "ATX session UI capture failed after retry and reset")`.
2. Trong `flows/feed_swipe_smoke.py`, hàm `_row_from_attempt` dùng `_is_feed_confirmed(attempt)` để xác minh màn hình qua screenshot markers (top navigation tab, bottom navigation tab, feed controls).
3. Khi screenshot khẳng định đang ở Feed (`_is_feed_confirmed` là True), flow kiểm tra:
   ```python
   if xml_error in FEED_CONFIRMED_XML_DEGRADED_ERRORS:
       return build_step(..., status=ExitStatus.DEGRADED.value, ...)
   if xml_available:
       return build_step(..., status=ExitStatus.SUCCESS.value, ...)
   return build_step(..., status="failed", reason=f"feed marker confirmed but XML unavailable: {xml_error}", ...)
   ```
4. Tập `FEED_CONFIRMED_XML_DEGRADED_ERRORS` trước đây chỉ chứa các mã lỗi uiautomator cũ:
   `{"uiautomator_idle_state_error", "uiautomator_null_root_node", "ui_dump_command_failed", "ui_dump_failed", "ui_dump_file_missing"}`.
5. Khi `xml_error` là `"ATX_SESSION_UNAVAILABLE"`, do không nằm trong `FEED_CONFIRMED_XML_DEGRADED_ERRORS`, flow dừng phiên sai lệch với status `"failed"` thay vì chuyển sang trạng thái chấp nhận được là `ExitStatus.DEGRADED`.

## Giải pháp chuẩn hóa
1. Thêm `"ATX_SESSION_UNAVAILABLE"` và `"atx_session_unavailable"` vào `FEED_CONFIRMED_XML_DEGRADED_ERRORS`.
2. Bổ sung kiểm tra case-insensitive (`xml_error.lower() in {e.lower() for e in FEED_CONFIRMED_XML_DEGRADED_ERRORS}`) tại các vị trí đánh giá XML error trong `feed_swipe_smoke.py`:
   - `_is_degraded_xml_drift`
   - `_row_from_attempt` (feed confirmed check)
   - `_recover_known_feed_tab_drift`
   - `_is_profile_guard_degraded_xml_drift`
   - `_is_profile_guard_drift_due_to_degraded_xml`
   - `home_navigation` status check
3. Viết focused unit test `test_feed_confirmed_atx_session_unavailable_degrades_instead_of_failing` trong `python_runner/tests/test_feed_session_smoke.py` xác nhận row status là `ExitStatus.DEGRADED.value`.
