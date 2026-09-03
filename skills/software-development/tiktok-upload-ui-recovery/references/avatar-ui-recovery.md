# TikTok Avatar Flow & UI Fallback Recovery

## Quy trình Avatar-Only chuẩn
1. Khởi chạy chế độ Avatar-only: `--avatar-smoke --force-avatar-upload --force-avatar-machines <N>`
2. Tránh nhầm lẫn: Không chạy `--force-avatar-upload` đơn lẻ vì sẽ kéo theo quy trình đăng video.

## Quy tắc Tự động Upload Avatar khi Đăng Video Lần Đầu (Video #1)
1. **Auto-Trigger Policy**:
   - Khi tài khoản đăng video lần đầu tiên (`video_number == 1`), `_force_avatar_upload_allowed()` trong `state_machine.py` tự động trả về `True` để kích hoạt flow tải ảnh đại diện `avatar.jpg` lên profile.
   - Từ video số 2 trở đi (`video_number >= 2`): Tự động bỏ qua flow avatar (`skip`).
2. **State Machine Transition Architecture**:
   - Sau khi `UPDATE_WORKBOOK` hoàn tất trong flow đăng video, State Machine phải chuyển trạng thái sang `ENSURE_AVATAR` trước khi tới `DELETE_REMOTE_MEDIA` -> `POST_CACHE_CLEANUP`.
   - *Pitfall*: Nếu `TRANSITION_MAP[WorkflowState.UPDATE_WORKBOOK]` trỏ thẳng sang `DELETE_REMOTE_MEDIA`, toàn bộ nhánh `ENSURE_AVATAR` sẽ bị bỏ qua và avatar cho nick mới không bao giờ được up.

## Xử lý các màn hình chuyển tiếp (UI Fallback)
1. **Màn chọn ảnh từ Album**:
   - Sau khi chọn tile ảnh đại diện, UI TikTok hiển thị nút đỏ **"Tiếp (1)"** ở góc dưới bên phải.
   - Nếu ATX XML dump bị trễ/stale, script cần dùng visual fallback để xác định tọa độ nút Tiếp và tap chuyển tiếp.

2. **Màn Cắt ảnh (Crop surface)**:
   - Giao diện có 2 nút: **Hủy** (trái) và **Lưu** (phải, màu đỏ).
   - Nếu XML không bắt được text "Lưu", fallback nhận diện vùng nút đỏ phía dưới bên phải để tap Lưu.

3. **Hậu kiểm thành công (Tránh False-Fail)**:
   - Ngay sau khi bấm Lưu, TikTok tự động đóng màn Crop và quay về trang **"Sửa hồ sơ"** (Profile Edit) với ảnh đại diện mới.
   - Nhận diện trang Sửa hồ sơ + tên nick là bằng chứng hoàn tất (`SUCCESS`), không fail-closed vì màn Crop không còn tồn tại.

4. **Dọn dẹp kết thúc**:
   - `am force-stop com.ss.android.ugc.trill`
   - Đưa thiết bị về màn hình Home.
