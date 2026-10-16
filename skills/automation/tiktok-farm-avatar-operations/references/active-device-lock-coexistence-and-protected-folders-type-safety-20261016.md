# Active Device Lock Coexistence, Sub-caption Edge Trap & Protected Folders Type Safety (16/10/2026)

## 1. Bối Cảnh Thực Tế & Hiện Trường Sự Cố
- **Tình huống**: Operator gửi ảnh Profile TikTok nick `Hoàng Kim Hùng` (`@carlosfwagne2`) trên Máy 59 (Tik 3, F_out=467, F_src=219) yêu cầu *"Đổi ava"*.
- **Xung đột tài nguyên**: Khi kiểm tra máy 59 qua `with_device_lock.py`, phát hiện thiết bị đang có active device lock từ tiến trình `tiktok-add-bao-mat-f2a` (`run_batch_live_2fa.py`, PID 28120).
- **Yêu cầu kỷ luật**: Không được ngắt ngang, cấm force-kill hay reboot máy để cướp lock; đồng thời không được nằm im đóng băng để operator phải giục.

---

## 2. Quy Trình Chuyển Giao & Phối Hợp Mượt Mà Với Active Device Lock (Coexistence Protocol)
1. **Tiền trạm không chạm thiết bị**:
   - Trong lúc máy đang bận ca nuôi hoặc ca bảo mật 2FA, Coordinator tiến hành toàn bộ các khâu xử lý media offline:
     * Quét `representative_frames` hoặc video gốc/render để tìm ứng viên khuôn mặt.
     * Cắt vuông $512 \times 512$ theo Center-based Crop và tạo ảnh preview viền tròn xanh.
     * Giám định thị giác qua `ag_cli.py ask` và `browser_vision` để loại trừ frame dính chữ, dính logo hoặc lẹm cằm/đỉnh tóc.
     * Gửi 2 phương án đạt chuẩn cho Operator lựa chọn.
2. **Dàn trận dữ liệu & Marker vật lý**:
   - Ngay khi chốt phương án:
     * Sao chép ảnh vào cả 3 đầu kho: `D:/TIKTOK-videonuoinick/<F_out>/avatar.jpg`, `D:/video goc/<F_src>/avatar.jpg`, `D:/video goc/<F_out>/avatar.jpg`.
     * Tạo marker vật lý `.manual_avatar_locked` tại cả 3 thư mục trên.
     * Đăng ký metadata vào `D:/Taadaa/data/manual_avatar_protected_folders.json`.
     * Ghi nhận `PENDING` vào `avatar_replace_queue` (SQLite) và `Tik<N>.xlsx`.
3. **Theo dõi nhả lock & Kích hoạt nạp ngay lập tức**:
   - Giám sát tiến trình đang giữ lock: `psutil.pid_exists(pid)`.
   - Ngay khi PID kết thúc và device lock được giải phóng $\to$ lập tức kích hoạt canonical runner đơn máy:
     ```bash
     python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <N> --machine <M>
     ```
     (Chạy qua `terminal(background=True, notify_on_complete=True, timeout=360)` để event-driven đánh thức).
4. **Nghiệm thu thị giác Gate 6 độc lập**:
   - Đọc `report.json` xác nhận `avatar_status: "FORCED_REPLACED_VERIFIED"`.
   - Soi mắt qua `browser_vision` trên `avatar-save-surface-guard.png` (màn Cắt) và `avatar-uploaded-confirmed.png` (màn Sửa hồ sơ).
   - Cập nhật SQLite sang `DONE` và Excel sang `OK`.

---

## 3. Bẫy Mẩu Chữ Phụ Đề Lởm Chởm Trong Vòng Tròn (Sub-caption Edge Trap)
- **Hiện tượng**:
  - Khi crop frame `v23_002.jpg`, khuôn mặt nhân vật nhìn thẳng và rõ nét. Tuy nhiên, ở đỉnh khung hình có dòng chữ phụ đề màu đỏ `(adj): cực kỳ tuyệt vời`.
  - Thuật toán căn tâm vẽ đường viền tròn xanh cắt ngang qua dòng chữ, khiến phần chân chữ màu đỏ lọt vào bên trong vòng tròn avatar.
- **Phát hiện qua `ag_cli.py ask`**:
  - *"Lỗi nghiêm trọng: Đường viền tròn xanh cắt ngang trực tiếp qua dòng chữ này... Khi crop ảnh theo hình tròn làm avatar, góc trên cùng của avatar sẽ dính các mẩu vụn chữ màu đỏ bị cắt lởm chởm rất mất thẩm mỹ."*
- **Quy tắc xử lý**:
  - Tuyệt đối không chấp nhận ảnh bị viền tròn cắt ngang chữ/caption.
  - Nếu không inpaint được sạch nền, bắt buộc chuyển sang khung hình khác (như `v19_002.jpg`) có khoảng đệm trần/tường trống hoàn toàn sạch chữ trước khi gửi phương án cho Operator.

---

## 4. Bẫy Lỗi Sắp Xếp Trộn Lẫn Kiểu Dữ Liệu Trong `manual_avatar_protected_folders.json`
- **Triệu chứng lỗi**:
  - Khi script Python cập nhật `manual_avatar_protected_folders.json` thêm folder mới:
    ```python
    TypeError: '<' not supported between instances of 'str' and 'int'
    ```
- **Nguyên nhân gốc rễ**:
  - Trong file JSON, mảng `protected_folders` có thể chứa cả số nguyên `[45, 141, 289, 326, ...]` lẫn chuỗi `"467"`, `"219"` do các lần thêm trước đó.
  - Gọi hàm `.sort()` trực tiếp trên list hỗn hợp kiểu dữ liệu trong Python 3 sẽ gây crash ngay lập tức.
- **Giải pháp chuẩn hoá an toàn 100%**:
  ```python
  # Ép toàn bộ phần tử về int và loại bỏ trùng lặp trước khi sort
  protected_folders = sorted(list(set(int(x) for x in protected_folders)))
  data["protected_folders"] = protected_folders

  # Lưu metadata account với key dạng string chuẩn
  data.setdefault("accounts", {})
  for folder_id in [467, 219]:
      data["accounts"][str(folder_id)] = {
          "username": "carlosfwagne2",
          "machine": 59,
          "tik": 3,
          "video_goc": folder_id,
          "description": "Sang tao",
      }
  ```
