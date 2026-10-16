# Kỷ Luật Tái Sử Dụng Runner Gốc (Chống Đẻ Script Tạm) & Xử Lý Sự Cố Upload Avatar

## 1. Bối Cảnh & Lời Nhắc Nhở Từ Người Dùng
- **Sự cố (16/10/2026 — @giathu0709 M65 Tik 4)**:
  - Khi kích hoạt đổi avatar qua script bọc có sẵn `run_avatar_batch_3accs.py --tik 4 --machine 65`, batch launcher báo lỗi:
    `Workflow target error: Missing required fields: Folder Video`
  - Thay vì kiểm tra trực tiếp tham số và gọi runner module gốc bằng một dòng lệnh terminal duy nhất, Coordinator lại tạo file script trung gian `D:/Taadaa/tmp/test_runner_65.py` để bọc subprocess.
  - User chất vấn thẳng: *"Chưa hiểu vì sao có script upload ava r mà phải đi viết script ms v"*.
- **Kỷ luật cốt lõi Farm (REUSE > EXTEND > NEW)**:
  - **CẤM TUYỆT ĐỐI** tự tiện viết file script python mới (`test_runner_*.py`, `do_upload_*.py`, `run_temp_*.py`) trong thư mục tạm `tmp/` để thực thi thay cho runner chuẩn.
  - Mọi thao tác nạp avatar đơn máy BẮT BUỘC phải dùng trực tiếp runner module gốc có sẵn của Farm.

---

## 2. Nguyên Nhân Lỗi "Missing required fields: Folder Video" & Công Thức Chạy Trực Tiếp Chuẩn O(1)
- **Nguyên nhân gốc rễ**:
  - `run_tiktok_upload_batch.ps1` khi chạy subprocess qua `Start-Job` có thể bị nuốt biến môi trường `PYTHONPATH` hoặc xung đột với workbook header alias khi gọi qua launcher tầng cao.
- **Công thức Direct Invocation chuẩn O(1) (Cấm viết script trung gian)**:
  Khi cần nạp avatar đơn máy cho Máy `<M>` trên Workbook `Tik<N>.xlsx`, gọi trực tiếp module `tiktok_workflow` với Python runtime đã pin và `PYTHONPATH` rõ ràng:
  ```bash
  PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" "D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" -m tiktok_workflow --config "D:/CodexRuntime/tiktok-video/config-machine-62.yaml" --workflow-workbook "D:/OneDrive/TaadaaData/kibe/Tik<N>.xlsx" --machine "<M>" --avatar-smoke --force-avatar-upload --force-avatar-machines "<M>"
  ```
  - Chuyền chuỗi xác nhận `AVATAR-SMOKE` qua stdin nếu cần.
  - Lệnh này chạy trực tiếp, không phụ thuộc PowerShell background job, không bị lỗi mapping trung gian, và trả về report tại `D:\CodexRuntime\tiktok-video\runs\run_<device>_<timestamp>\report.json`.

---

## 3. Cạm Bẫy Màn Hình Đen (avatar-uploaded-confirmed.png mean=0.0 / 12.4KB)
- **Hiện tượng**:
  - Khi runner hoàn tất flow `AVATAR_SMOKE_SUCCESS` và ghi nhận `avatar_status: FORCED_REPLACED_VERIFIED`, file chụp màn hình nghiệm thu cuối cùng `avatar-uploaded-confirmed.png` có dung lượng chính xác `12.491 bytes` và giá trị pixel trung bình `mean = 0.0` (màn hình đen tuyền hoàn toàn).
  - Nguyên nhân: Sau khi lưu avatar thành công, màn hình thiết bị Samsung S7 bị rơi vào trạng thái ngủ (Sleep/Dozing) trước nhịp chụp `screencap` cuối của runner.
- **Quy tắc nghiệm thu thị giác bắt buộc**:
  1. **CẤM GỬI ẢNH ĐEN MÙ**: Tuyệt đối không lấy `avatar-uploaded-confirmed.png` gửi cho User khi chưa soi mắt qua `browser_vision`. Màn hình đen là lỗi hiển thị vi phạm Invariant.
  2. **Đối soát kép qua các Artifacts cùng Run Directory**:
     - Trong thư mục `D:\CodexRuntime\tiktok-video\runs\run_<device>_<timestamp>\`:
       * `avatar-crop-closing-01.png`: Màn hình giao diện cắt ảnh của TikTok (xác nhận ảnh mới đã nằm trọn trong khung tròn cắt ảnh).
       * `avatar-save-surface-guard.png`: Màn hình giao diện "Sửa hồ sơ" ngay sau khi bấm Lưu (xác nhận avatar tròn trên app đã cập nhật ảnh mới).
  3. **Đánh thức và chụp lại màn hình Profile ngoài app**:
     - Nếu cần ảnh ngoài trang cá nhân chính chủ: Gửi lệnh wake (`input keyevent 224`), swipe mở khóa, mở TikTok và chụp fresh profile screen.
