# TikTok Post Profile Tile Loading Verification (96% Overlay Trap)

## Context
Khi đăng video TikTok trên thiết bị Android farm (Samsung S7), sau khi bấm nút Đăng và composer đóng lại, TikTok chuyển về màn hình Profile và tạo một tile video tạm thời (vị trí trên cùng bên trái của lưới video) có vòng tròn hiển thị tiến độ upload/transcoding (ví dụ: `96%`).

## Pitfall: Sớm coi là đã đăng thành công khi chỉ đếm số lượng tile
- `state_machine.py` trong `_verify_profile_post_increment()` kiểm tra số lượng ô video trên Profile theo công thức `current > baseline`.
- Khi TikTok render tile mới có loading overlay `96%`, node container đã tồn tại trong XML hierarchy (`clickable=true`, class `FrameLayout`).
- Nếu script đếm số tile mà không kiểm tra trạng thái loading, nó sẽ thấy `current > baseline` và kết luận `SUCCESS` ngay lập tức.
- Nếu sau đó workflow chuyển sang đổi tài khoản hoặc đóng app, tác vụ upload ngầm có nguy cơ bị đứt gánh, chuyển thành bản nháp (Draft) hoặc lỗi mạng.

## Quy tắc Verify Đúng Chuẩn
1. **In-Progress Gate**:
   - Quét tile đầu tiên (trên cùng bên trái) hoặc toàn bộ grid. Nếu node chứa text regex `\d+%`, hoặc là `android.widget.ProgressBar`, hoặc có loading overlay: BẮT BUỘC tiếp tục polling và chờ đợi.
2. **Clean Completion Gate**:
   - Khi hoàn tất, TikTok sẽ xóa overlay loading và hiển thị view count (thường là 0 view ban đầu) hoặc duration.
   - TUYỆT ĐỐI KHÔNG dùng mốc `100%` (TikTok không bao giờ hiện 100%).
   - TUYỆT ĐỐI KHÔNG dùng mốc `0 view` làm điều kiện tiên quyết (dễ nhầm lẫn với video cũ mới đăng hoặc video 0 view).
   - Điều kiện đủ: Toàn bộ grid không còn bất kỳ node nào chứa `%` hay `ProgressBar`, và tile đầu tiên đã ổn định thành video tile hoàn chỉnh.
3. **Timeout / Watchdog**:
   - Chờ tối đa 60–120s tùy proxy. Nếu quá thời gian vẫn kẹt `%` (rớt mạng/proxy), dừng lại chuyển `MANUAL_REVIEW`/`BLOCKED` kèm screenshot/XML, CẤM ghi đè `UPDATE_WORKBOOK`.
