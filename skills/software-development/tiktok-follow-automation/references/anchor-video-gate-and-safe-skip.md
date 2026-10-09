# Case UI-60: Anchor Video Gate, Cover Selectors & Safe-Skip Protocol

## 1. Hiện tượng & Triệu chứng
- Báo cáo Watchdog phiên nuôi TikTok xuất hiện hàng loạt máy dính "Lỗi script/xác minh" ở mục Follow chéo (ví dụ: 22 máy trong một phiên).
- Khi kiểm tra `follow_result.json`, phần lớn các máy bị gán nhãn:
  `MANUAL_REVIEW: anchor @<uid> không có video — back ra bỏ qua` với `exit_code: 1` và `failed: 1`.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Anchor Pool bốc phải nick yếu/thiếu video**:
   - `anchor_uids()` trước đây chỉ lọc theo `account_row_index <= 2` mà không kiểm tra `video_count`.
   - Các nick mới reg hoặc acc chưa kịp đăng đủ video (< 5 video) vẫn lọt vào danh sách Anchor của Mode 2.
2. **Selector Video Cover bị lệch trên TikTok UI 46.x (Samsung S7)**:
   - Logic cũ chỉ tìm các node có resource-id chứa chuỗi `"cover"`.
   - Trên TikTok 46.x thực tế trên thiết bị Samsung S7, grid video hiển thị các item frame với resource-id `id/exx`, `id/tv_play_count`, hoặc `aweme` chứ không còn chứa từ khóa `cover`. Dẫn tới dù anchor có video thật (21 video), script vẫn tưởng profile rỗng.
3. **Phân loại sai trạng thái Safe-Skip**:
   - Khi anchor không có video, runner thoát ra nhưng lại gán status mặc định là `MANUAL_REVIEW` và đánh dấu fail cả session thay vì coi đây là một safe-skip thông thường để chuyển sang anchor tiếp theo.
4. **Cạm bẫy ADB Screencap trên Windows MSYS**:
   - Dùng `adb shell screencap -p > file.png` trên MSYS/Git Bash sẽ bị chuyển đổi ký tự `\n` thành `\r\n` (CRLF), làm file PNG bị hỏng (corrupt header `cannot identify image file`).

## 3. Quy chuẩn khắc phục (Standard Fix)
1. **Lọc video_count cho Anchor**:
   - `anchor_uids` bắt buộc kiểm tra `row_video_counts.get(uid, 0) >= 5`. Chỉ cho phép nick có từ 5 video trở lên làm anchor. Fallback về row <= 2 nếu môi trường mock không có dữ liệu video count.
2. **Mở rộng selector nhận diện Video Covers**:
   - Khớp đa dạng selector: `any(k in str(n.get("resource_id", "")).lower() for k in ("cover", "tv_play_count", "exx", "aweme"))` với `bounds[1] >= 400`.
3. **Safe-skip outcome `no_video`**:
   - Khi anchor không có video: gán `engine._last_anchor_follow_outcome = "no_video"`.
   - Trong vòng lặp `run_mode2`, xếp `"no_video"` cùng nhóm với `("zero_following", "not_found")` để quay về feed an toàn và duyệt tiếp anchor tiếp theo.
   - Nếu cả 3 anchor đều bị bỏ qua an toàn, kết thúc session với trạng thái `SKIPPED` thay vì `MANUAL_REVIEW`.
4. **Chụp Screencap không corrupt**:
   - BẮT BUỘC dùng lệnh binary stream: `adb -s <serial> exec-out screencap -p > <path>.png`.
