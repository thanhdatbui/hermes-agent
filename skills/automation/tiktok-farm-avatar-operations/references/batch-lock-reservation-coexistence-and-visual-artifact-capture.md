# Batch Lock Reservation Coexistence & Canonical Visual Artifact Capture

## 1. Hiện Tượng Xung Đột Device Lock Dạng `queued_v2`
Khi chạy nạp avatar đơn lẻ qua `run_avatar_batch_3accs.py --tik <slot> --machine <M>`:
- Runner có thể báo `SKIPPED_LOCKED` (`device lock active`).
- Kiểm tra file lock tại `C:\Users\Kibe\.codex\device-locks\machine_<M>.lock.json`:
  ```json
  {
    "machine": "34",
    "serial": "...",
    "pid": 6332,
    "project": "tiktok-add-bao-mat-f2a",
    "command": "batch-live-2fa-reservation",
    "status": "queued_v2",
    "owner_active": true,
    "pinned": true
  }
  ```
- **Bản chất**: Tiến trình batch hệ thống (ví dụ `run_batch_live_2fa.py` hoặc batch feed/reg) giữ trước hàng đợi reservation cho toàn bộ danh sách máy mục tiêu.
- **Kỷ luật Farm Safety tuyệt đối**:
  - **CẤM cướp lock hay xóa file lock**: Tuyệt đối không xóa `.lock.json` khi PID sở hữu vẫn đang chạy (`owner_active: true`, PID alive trong `psutil`).
  - **Kiểm tra hiện trường PID**: Dùng `psutil.Process(pid).children()` để kiểm tra xem process có đang can thiệp trực tiếp trên serial máy `<M>` hay chỉ đang nằm trong hàng đợi chờ lượt.
  - **Xử lý chuẩn**: Đợi tiến trình batch hoàn thành xử lý hoặc nhả lock (`NO LOCK`), sau đó mới kích hoạt lại runner nạp avatar.

---

## 2. Truy Xuất Bằng Chứng Thị Giác Chuẩn Từ Runtime Artifacts (Gate 6)
Khi pipeline `run_avatar_batch_3accs.py` (hoặc `run_tiktok_upload_avatar.ps1`) chạy thành công:
- Runner tự động thực thi các bước: Push ảnh -> Vào Sửa hồ sơ -> Chọn ảnh -> Màn hình Crop -> Bấm Lưu -> Chờ CDN -> Force-stop TikTok đưa về Home.
- **Bẫy ngộ nhận**: Nếu sau khi runner xong mà Agent tự chạy `adb exec-out screencap` thì máy đã bị force-stop về Launcher Home hoặc màn hình tắt (Dozing), dẫn đến ảnh chụp không phản ánh được màn hình ứng dụng hoặc bị đen màn hình.
- **Thư mục chứa Artifacts chuẩn (Canonical Run Directory)**:
  - Đường dẫn: `D:\CodexRuntime\tiktok-video\runs\run_<serial>_<timestamp>\`
  - Các artifact bắt buộc kiểm tra:
    1. `avatar-save-surface-guard.png`: **Bằng chứng thị giác đắt giá nhất** — Chụp đúng khoảnh khắc khuôn mặt nhân vật nằm bên trong vòng tròn crop của TikTok kèm nút "Lưu" đỏ rực.
    2. `avatar-uploaded-confirmed.png`: Ảnh chụp màn hình Sửa hồ sơ sau khi bấm Lưu.
    3. `report.json`: Chứa `"avatar_status": "FORCED_REPLACED_VERIFIED"`, `"status": "AVATAR_SMOKE_SUCCESS"`.
- **Thao tác nghiệm thu Gate 6**:
  - Mở `avatar-save-surface-guard.png` qua `browser_navigate` + `browser_vision` để soi mắt kiểm chứng.
  - Kiểm tra OCR xác nhận đúng tên tài khoản (`yobi1965`).
  - Gửi `MEDIA:D:/CodexRuntime/tiktok-video/runs/run_<serial>_<timestamp>/avatar-save-surface-guard.png` kèm mô tả chi tiết nội dung đã thấy tận mắt cho người dùng.
