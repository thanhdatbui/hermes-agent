# Bẫy Khách Mời Phỏng Vấn, Phân Biệt Host Kênh & Chuẩn Hóa Worker Dispatch Avatar (2026-10-15)

## 1. Bẫy Khách Mời / Phỏng Vấn Trong Trích Xuất Khuôn Mặt (Guest / Interviewee Trap)
- **Bản chất sự cố**:
  - Khi trích xuất khuôn mặt tự động bằng Haar Cascade hoặc YOLO từ các video tin tức, phóng sự, talkshow hoặc phỏng vấn đường phố (ví dụ: kênh *Bản tin Tài chính* `@karunmmkx35` - F517/385):
  - Thuật toán quét khuôn mặt tại các mốc thời gian (ví dụ giây 3, 5, 22) sẽ phát hiện nhiều khuôn mặt khác nhau.
  - Tại giây 3: Nữ MC chính diện của bản tin (áo dạ tweed hồng ca-rô, tóc xoăn sóng).
  - Tại giây 22: Nam chuyên gia / đại biểu trung niên (áo vest navy, sơ mi xanh mở cúc, nốt ruồi trán) đang phát biểu tại hội nghị.
  - Nếu chỉ dựa vào kích thước bounding box lớn nhất (`w * h`), hệ thống có thể chọn nhầm khách mời / chuyên gia nam làm avatar cho kênh nữ MC (tên "Mai").
- **Quy tắc đối soát xác định Host chuẩn**:
  1. **Đối chiếu tên hiển thị & Profile**: Tên hiển thị ("Mai", "An", "Thảo") và giới tính của tài khoản trên TikTok.
  2. **Quét đa video trên lưới**: Đối chiếu khuôn mặt xuất hiện xuyên suốt trên các video trong lưới 3x3 (Host là người xuất hiện ở phần lớn video, khách mời chỉ xuất hiện ở 1–2 video hoặc vài giây phóng sự).
  3. **Giám định thị giác độc lập qua Antigravity CLI / Vision**: Soi mắt mô tả chi tiết nhân vật (MC vs Khách mời, bối cảnh trường quay vs bục phát biểu) trước khi đưa ra phương án.

---

## 2. Chuẩn Hóa Hợp Đồng Dispatch Worker (Coordinator T1 Budget Exhaustion)
- **Bối cảnh**:
  - Khi Coordinator đã dùng hết ngân sách T1 (<= 200 dòng ghi file cộng dồn trong session), Coordinator bị chặn `write_file`/`patch` và bắt buộc phải điều phối Worker qua `delegate_task`.
- **Cạm bẫy định dạng `FOCUSED_TEST` giữa Coordinator Guard và Worker Sandbox**:
  1. **Coordinator Guard**: Bắt buộc format regex:
     - Chuẩn: `python -m pytest <path_to_test.py>::<test_node> -q` HOẶC `python -m py_compile <path_to_file.py>`.
     - Nếu truyền `pytest <file.py>` sẽ bị Coordinator Guard ném lỗi `INVALID_FOCUSED_TEST_FORMAT`.
  2. **Worker Sandbox Gate**:
     - Lệnh `python -m py_compile` bị chặn bởi Worker Terminal Whitelist (default-deny).
     - Lệnh `pytest` / `python -m pytest` ĐƯỢC PHÉP trong whitelist của Worker.
  3. **Giải pháp chuẩn O(1)**:
     - Tạo một file test riêng (ví dụ `D:/Taadaa/reports/test_apply_avatars.py`) chứa test node `test_apply_avatars_success()`.
     - Test node trực tiếp thực thi hàm xử lý và `assert` các file ảnh sinh ra tồn tại và dung lượng `> 1000 bytes`.
     - Khai báo contract:
       ```text
       TASK_KIND: CREATE
       FILE: D:/Taadaa/reports/apply_selected_avatars.py
       FOCUSED_TEST: python -m pytest D:/Taadaa/reports/test_apply_avatars.py::test_apply_avatars_success -q
       ```
     - Điều này đảm bảo thỏa mãn cả 2 tầng chốt chặn an toàn: Coordinator Contract Gate chấp thuận và Worker Sandbox thực thi thành công 100%.

---

## 3. Quy Trình Vận Hành Khi User Lệnh "Tự chọn r làm đi"
Khi User ủy quyền toàn quyền tự chọn và thực hiện:
1. **Lựa chọn phương án tối ưu nhất**:
   - Chọn Host chính diện của kênh, phong thái chuyên nghiệp, khẩu hình/biểu cảm tự nhiên.
   - Ưu tiên ảnh có headroom an toàn (cách mép trên viền tròn 30–40px), không bị cụt đầu hay lẹm cằm khi TikTok cắt tròn.
2. **Đồng bộ toàn diện 3 đường dẫn**:
   - `D:/video goc/<F_src>/avatar.jpg`
   - `D:/video goc/<F_out>/avatar.jpg`
   - `D:/TIKTOK-videonuoinick/<F_out>/avatar.jpg`
3. **Khóa cứng bảo vệ chống script quét đè (SSOT Protection)**:
   - Thêm toàn bộ các folder liên quan ($F_{src}$ và $F_{out}$) vào `protected_folders` và `accounts` trong cả 2 file:
     * `D:/Taadaa/data/manual_avatar_protected_folders.json`
     * `D:/Taadaa/Tiktok-video/data/manual_avatar_protected_folders.json`
4. **Cập nhật trạng thái hàng đợi và Excel**:
   - Đặt cột `Avatar` trong `Tik<Slot>.xlsx` thành `PENDING`.
   - Cập nhật SQLite `avatar_replace_queue` sang `status = 'PENDING'` để runner/watchdog nhận diện thiết bị cần nạp avatar mới.
