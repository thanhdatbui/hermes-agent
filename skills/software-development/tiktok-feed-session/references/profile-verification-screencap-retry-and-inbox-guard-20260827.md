# Profile Verification Screencap Retry & Inbox Selection Invariant (2026-08-27)

## Bối cảnh sự cố
Trong phiên chạy `multi-machine-feed-session`, các máy (như Máy 30, Máy 59) bị dừng phiên với lỗi:
`profile verification capture-artifact-incomplete: profile verification navigation retry artifact incomplete`
hoặc `profile verification capture artifact incomplete`.

## Root Cause Analysis
1. **Screencap 12 zero bytes (`\x00`*12):**
   - Trên thiết bị Android (Samsung S7 box farm), khi màn hình đang ngủ (asleep) hoặc chuyển đổi buffer SurfaceFlinger, lệnh `exec-out screencap -p` có thể trả về đúng 12 byte null.
   - Hàm `_persist_profile_capture_artifacts` trước đây chỉ gọi `screencap -p` 1 lần duy nhất, không retry, không đánh thức màn hình. Khi gặp 12 byte này, nó raise `RuntimeError("screencap output is not a PNG")`, ghi nhận `capture_artifact_status = "incomplete"`.
   - Gate `_profile_capture_artifact_is_complete` kiểm tra thấy thiếu file ảnh PNG hợp lệ nên fail-closed, khóa máy giữ hiện trường.
2. **False Trigger Inbox Navigation Retry:**
   - Điều kiện cũ `initial_normalized & message_markers` quét toàn bộ text trong UI XML. Vì thanh điều hướng bottom navigation bar của TikTok luôn chứa chữ "Hộp thư", điều kiện này luôn `True`, làm script luôn kích hoạt nhánh re-tap navigation sang Profile kể cả khi đang ở Profile hoặc Feed.

## Quy tắc Invariant & Cách khắc phục
1. **Screencap Bounded Retry + Screen Wake:**
   - Trong `_persist_profile_capture_artifacts`, bắt buộc thử tối đa 3 lần cho `screencap -p` với độ trễ 0.5s giữa các lần.
   - Nếu dữ liệu trả về rỗng / < 64 bytes hoặc không có PNG magic bytes (`\x89PNG\r\n\x1a\n`), kiểm tra `dumpsys power` và gửi `input keyevent 224` (wake up) trước khi thử lại.
   - Chỉ khi đủ cả 3 lần thất bại mới đánh dấu `capture_artifact_status = "incomplete"`.
2. **Xác định màn hình Inbox chính xác bằng Tab Selection:**
   - Thay vì quét text toàn màn hình, sử dụng `_is_inbox_tab_selected_from_xml`: chỉ re-tap khi tab "Hộp thư" / "Inbox" thực sự mang thuộc tính `selected="true"`.
3. **Độ trễ chuyển cảnh UI:**
   - Sau khi dismiss overlay Camera hoặc re-tap Profile, luôn có khoảng nghỉ `time.sleep(1.5)` trước khi chụp XML để đảm bảo UI đã render xong các node username và display name.
