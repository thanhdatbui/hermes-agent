# Case UI-53: TikTok 46.x Profile Action Button "Nhắn tin" / "Message" & Icon Tick Friend Classification

## 1. Hiện trường sự cố & Triệu chứng
- **Farm Alert:** `[MÁY 51] MANUAL_REVIEW: trạng thái nút không xác định sau vuốt xác nhận` (hoặc các máy S7/S8 chạy TikTok 46.x).
- **Màn hình profile sau khi tap Follow:**
  - Nút chính chuyển thành hình pill lớn với chữ **"Nhắn tin"** (hoặc **"Message"**).
  - Nút phụ ở giữa là icon **người có dấu tích** (biểu thị quan hệ bạn bè / đang follow, không có text).
  - Nút phụ bên phải là icon tam giác xổ xuống **▼**.
  - Hoàn toàn KHÔNG hiển thị text "Đã follow", "Following", hay "Bạn bè" theo cách hiển thị cũ.

## 2. Root Cause
- Trong `follow_runner/flows/verify_follow.py`:
  - Sau khi tap Follow, hàm `_confirm_not_released` thực hiện kéo `pull_to_refresh_profile` để kiểm tra tài khoản có bị shadow drop / rate-limit âm thầm nhả follow hay không.
  - Sau khi vuốt tải lại trang, hàm `classify_button(xml)` quét uiautomator XML để phân loại nút action.
  - Trước đây, `_is_profile_action_node` chỉ nhận diện các resource ID suffix cũ (`id/fds`, `id/ff8`, `id/fij`, `id/fi6`, `id/flo`). Nếu nút "Nhắn tin" không mang các id này hoặc id thay đổi, nó bị loại khỏi danh sách `action_nodes`.
  - Đồng thời trong `classify_button`, code chỉ tìm tập text trong `FOLLOWED_TEXT` (`"đã follow"`, `"đang theo dõi"`, `"following"`, `"bạn bè"`, `"friends"`). Khi chỉ có nút "Nhắn tin" mà không có chữ "Đã follow", `classify_button` trả về `"unknown"`.
  - Sau khi vuốt reload vẫn phân loại `"unknown"`, flow fail-closed kích hoạt:
    `MANUAL_REVIEW: trạng thái nút không xác định sau vuốt xác nhận`.

## 3. Giải pháp chuẩn (Case Fix)
1. **Mở rộng `_is_profile_action_node`:**
   - Thêm bộ marker tin nhắn: `message_markers = {"nhắn tin", "message", "gửi tin nhắn", "send message"}`.
   - Chấp nhận các node có text hoặc content-desc chứa marker này nằm ở vùng header action (`bounds[1] < 1200`), thuộc package TikTok hợp lệ và loại trừ stat counters (`_STAT_COUNTER_IDS`).
2. **Quy tắc phân loại trong `classify_button`:**
   - Nhận diện `has_message` từ `message_markers`. Nếu có `has_message`, đánh dấu `has_followed = True`.
   - Thêm quy tắc short-circuit rõ ràng: Nếu profile có nút "Nhắn tin" / "Message" và hoàn toàn KHÔNG còn nút "Follow" / "Follow lại" / "Theo dõi" (`recognized_messages and not recognized_not_followed`), lập tức phân loại là `"followed"`.

## 4. Anti-Derailment Rule: Không nhầm lẫn hiện trường Incident với màn hình trôi do Cron chạy sau
- **Bài học xương máu:** Khi nhận Farm Alert từ tối hôm trước nhưng xử lý vào sáng hôm sau, thiết bị có thể đã bị cron sáng chạy đè hoặc rơi vào màn hình khác (ví dụ kẹt Tìm kiếm có bàn phím ảo hoặc màn hình 2FA).
- **Kỷ luật:** BẮT BUỘC bám chặt vào log của run sự cố (`D:/Taadaa/runtime/kibe/live/.../machines/machine_<N>/<run_id>/follow_result.json`) và thông báo alert gốc để định vị đúng hàm/dòng code phát sinh lỗi.
- Tuyệt đối KHÔNG chụp màn hình hiện tại rồi tự suy diễn một root cause hoàn toàn mới không liên quan đến thông báo lỗi gốc của người dùng.
