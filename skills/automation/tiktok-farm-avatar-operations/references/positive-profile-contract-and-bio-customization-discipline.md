# Positive Profile Contract & Bio Customization Discipline

## 1. User Feedback & Anti-Template Bio Discipline
- **CẤM RẬP KHUÔN VĂN MẪU:** Tuyệt đối không dùng các công thức sáo rỗng lặp đi lặp lại như `"Chia sẻ [X] và [Y] mỗi ngày"` hoặc `"Chia sẻ ... mỗi ngày"` trên các tài khoản trong farm.
- **Bám sát thực tế video (Ground Truth First):**
  - Không tự suy diễn hay over-engineer ngách dựa vào keyword chung chung trong file Excel (ví dụ: thấy keyword "Âm nhạc" nhưng video thực tế là vlog troll/đời sống hài hước thì không được tự đặt tên hay viết bio về đàn Piano).
  - Phải kiểm tra nội dung/hashtag thực tế của các clip đang có trên kênh để đặt Bio phù hợp.
- **Tiêu chuẩn Bio đạt chuẩn:**
  - 100% tiếng Việt có dấu, độ dài <= 80 ký tự.
  - Văn phong tự nhiên, hài hước, có cá tính hoặc năng lượng tích cực ngắn gọn, không lảm nhảm đạo lý.
  - Bắt buộc gõ bằng `AdbKeyboard` qua Base64 UTF-8; trước khi nạp phải dọn sạch (0/160 ký tự) bằng broadcast `ADB_KEYBOARD_CLEAR_TEXT` hoặc tap `Clear Text` `(400, 1865)`.

## 2. Kiến Trúc Positive Contract Verifier (`verify_profile_positive.py`)
- **Triệt tiêu Claim Gaming:** Không dùng Consistency Gate (so khớp lời khai văn xuôi với OCR) vì Agent dễ lách bằng cách bỏ qua claim (claim omission) hoặc bịa ngoại lệ.
- **Tiêu chí Fail-Closed:**
  - `HANDLE`: Bắt buộc xuất hiện trên OCR.
  - `NAME`: Word-level match với tên kỳ vọng (chống false positive do trùng substring với handle).
  - `BIO`: Khớp token nội dung mới VÀ vắng mặt 100% các nút rỗng (`+ Thêm tiểu sử`, `+ Add bio`).
  - `PIN`: Nếu kênh có video >= 1.000 view, bắt buộc phải có nhãn `Đã ghi(m)` / `Pin` ở ô video đầu tiên.
- **Action-Forcing FSM (Chống bại liệt):**
  - Khi Verifier trả về `FAIL`, bắt buộc cấp danh sách `missing_fields` kèm `next_action` (hướng dẫn cụ thể + tool hint) để Agent tiếp tục hành động ngay thay vì đóng băng hoặc than khóc.
- **Whitelist BLOCKED Reasons:** Chỉ công nhận các lý do khách quan có bằng chứng máy thật (`NAME_CHANGE_COOLDOWN` khi OCR thấy phạt 7 ngày, `DEVICE_OFFLINE`, `SESSION_LOGGED_OUT`).

## 3. Thao Tác UI Profile Trên Samsung S7 (1080x1920)
- **Vào Sửa hồ sơ:** Icon cây bút ở góc trên bên trái `(75, 150)` (trên layout mới không có nút Sửa hồ sơ ở giữa).
- **Mở Bio:** Tap dòng Tiểu sử tại `(500, 950)`.
- **Lưu Bio:** Tap nút `LƯU` ở góc trên bên phải `(980, 150)`.
- **Ghim video:** Mở video top view -> tap nút 3 chấm / Chia sẻ tại `(1000, 1420)` -> tap icon `Ghim` tại `(650, 1800)` -> xác nhận toast `Đã ghim lên trên cùng hồ sơ`.

## 4. Điều Phối ADB Cụm Admin Khi Port 5037 LAN Bị Ngắt
- Nếu kết nối remote ADB từ Kibe sang Admin (`192.168.110.119:5037`) bị timeout / connection reset:
  - Chạy lệnh ADB cục bộ trên máy Admin qua SSH:
    ```bash
    python D:/Taadaa/tools/with_device_lock.py --machine <N> --serial <SERIAL> --force-preempt -- \
      python D:/Taadaa/tools/admin_ssh.py "python D:/Taadaa/tools/remote_admin_adb.py --ip 127.0.0.1 -s <SERIAL> <ADB_ARGS>"
    ```
  - Tránh spam compound command có `sleep` hay cú pháp phức tạp dễ bị Coordinator guard chặn.
