# Case 74 (03/09/2026): Nút "Follow lại" Bị Bỏ Qua Do Bounds Left và Thanh Bình Luận Tĩnh Nhận Nhầm Popup (Máy 74)

## 1. Hiện Tượng & Triệu Chứng
- Máy 74 dừng phiên `multi-machine-feed-session` với tài khoản `muyduyen4589`.
- Lý do dừng: `startup ad/splash marker detected` hoặc `manual-needed:popup` khi đang ở màn hình chi tiết video (`DetailActivity`).
- Màn hình hiển thị video có nút CTA *"Follow lại"* (`bounds="[36,1625][840,1757]"`), nút Back (`:id/bq7` / `Quay lại`), và thanh nhập bình luận tĩnh ở đáy (`"Thêm bình luận..."`, `bounds="[72,1806][1032,1895]"`).

## 2. Nguyên Nhân Gốc (Root Cause)
1. **Lọc Bounds Quá Chặt trong `dismiss_follow_friends_suggestion_popup`**:
   - Code `flows/benign_popup.py` có điều kiện `bounds[0] >= 50` nhằm loại bỏ các icon mép màn hình.
   - Nút *"Follow lại"* dạng banner/card có mép trái ở $x_0 = 36 < 50$, dẫn đến bị bỏ qua và không được tap.
   - Khi không có nút đóng `X`, flow thiếu nhánh quay lại (`:id/bq7` / `Quay lại` / phím `BACK`) để thoát về Feed.
2. **Nhận Nhầm Thanh Bình Luận Tĩnh trong `detect_comment_input_overlay`**:
   - Node `EditText` (`:id/eg4`) của thanh comment ở đáy có `focused="true"` mặc định trong UI hierarchy Android.
   - Heuristic phát hiện comment input overlay kích hoạt mà không kiểm tra bàn phím ảo (`keyboard_detected`) hoặc comment drawer (`has_comment_drawer`), khiến màn hình video bị phân loại thành `manual-needed:popup` thay vì `for-you`.
3. **Cơ Chế Swipe Recovery Bị Chặn**:
   - Do màn hình bị phân loại nhầm thành popup/startup-ad, luồng chuyển sang tìm nút Skip thay vì chạy `_swipe_recovery_on_stuck`.

## 3. Cách Xử Lý Đã Triển Khai
1. **`python_runner/flows/benign_popup.py`**:
   - Đổi điều kiện biên trái nút Follow lại thành `bounds[0] >= 0` để nhận diện toàn bộ nút trên màn hình.
   - Thêm luồng thoát sau khi tap: nếu `followed_count > 0` và không có nút `X`, tự động tìm nút Back (`:id/bq7` / `Quay lại`) hoặc gửi phím `BACK` để quay về Feed.
2. **`python_runner/flows/benign_popup_registry.py`**:
   - Sửa `detect_comment_input_overlay`: chỉ phân loại là overlay nhập bình luận khi có bàn phím ảo hiển thị (`keyboard_detected`) hoặc mở drawer danh sách bình luận (`has_comment_drawer`).
3. **`python_runner/flows/feed_swipe_smoke.py`**:
   - Bổ sung kiểm tra `DetailActivity` / Back button trong `_swipe_recovery_on_stuck` để tự động bấm Back thoát về Feed chính khi gặp lỗi.
