# Admin Cluster Remote ADB Isolation & Upload Create Button Triage

## 1. Cảnh Báo Chẩn Đoán Sai "Văng Máy Cụm Admin" (XiaoWei vs Remote ADB)
- **Hiện tượng:** Chạy `inspect_machine.py` hoặc `adb -H 192.168.110.119 -P 5037 devices` từ Kibe chỉ thấy 27/80 máy online, báo lỗi `device not found` cho hàng loạt máy.
- **Bẫy điều phối (CẤM SUY ĐOÁN TUỘT CÁP):**
  * XiaoWei trên máy Admin chạy local và chiếm giữ luồng stream của 79/80 máy qua `localhost:5037`.
  * Daemon ADB trên Admin không chia sẻ đầy đủ thiết bị qua card mạng LAN (`192.168.110.119:5037`).
  * Thực tế trên màn hình XiaoWei, 79 máy vẫn hiển thị mượt mà 100%. Cụm Admin chạy runner local trực tiếp trên máy Admin (`D:\Taadaa\tiktok-video`), KHÔNG phụ thuộc vào remote ADB từ Kibe.
- **Quy tắc:** Tuyệt đối cấm kết luận dàn máy Admin bị tuột cáp/sập nguồn khi chưa kiểm tra màn hình XiaoWei hoặc chạy lệnh nội bộ qua SSH trên máy Admin.

## 2. Lỗi Nhận Diện Nút Tạo Clip `_find_bounded_create_button`
- **Nguyên nhân:** TikTok liên tục cập nhật nhãn nút Tạo (`+`):
  * Nhãn mới: `"Đăng"`, `"Quay video"`, `"Tải lên"`, `"post"`, `"camera"`.
  * Bộ lọc cũ chỉ chấp nhận đúng 4 từ: `"+", "quay", "tạo", "create"`, khiến bot báo lỗi `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED]`.
- **Giải pháp chuẩn:**
  1. Mở rộng `allowed_tokens = {"+", "quay", "tạo", "create", "đăng", "post", "tải lên", "upload", "camera"}`.
  2. Dùng `any(tok in label for tok in allowed_tokens)` thay vì so sánh bằng tuyệt đối.
  3. Bổ sung Pass 2 cho nút không có text/content-desc: Kiểm tra node clickable nằm trong dải đáy trung tâm màn hình (`x: 40% - 60%`, `y >= 88%`).

## 3. Lệch Dữ Liệu Sổ Cái Liên Cụm (`Tik*.xlsx` Missing ID TikTok)
- **Triệu chứng:** Runner crash sau vài giây với lỗi `Missing required fields: ID TikTok`.
- **Nguyên nhân:** File `Tik*.xlsx` trên máy Admin bị trống cột `ID` (giá trị `None`) do sync OneDrive bị lỗi hoặc chưa điền, trong khi file trên Kibe đã có.
- **Xử lý:** Đối soát trực tiếp giữa Kibe và Admin qua script Python (SCP script lên Admin chạy và cập nhật workbook tại chỗ), sau đó kiểm chứng bằng `--dry-run` trước khi chạy thật.
