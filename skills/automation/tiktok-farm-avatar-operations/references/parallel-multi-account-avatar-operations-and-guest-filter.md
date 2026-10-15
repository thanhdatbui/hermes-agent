# Vận Hành Đổi Avatar Song Song Đa Tài Khoản & Bẫy Khách Mời Tin Tức / Nhắm Mắt (Cập nhật 2026-10-15)

## 1. Cạm Bẫy Thị Giác: Khách Mời Tin Tức vs MC Chính & Khung Hình Nhắm Mắt
Khi người dùng gửi ảnh màn hình kênh TikTok yêu cầu đổi avatar theo nhân vật trong video:

### Bẫy 1: Khách mời / Chuyên gia trong video tin tức (News Guest Speaker vs Anchor Trap)
- **Hiện tượng thực tế (Kênh Bản tin Tài chính `@karunmmkx35` - M65 Tik 5)**:
  - Video tin tức có cấu trúc: Nữ MC dẫn đầu bản tin $\rightarrow$ Chuyển cảnh sang phỏng vấn chuyên gia / khách mời tại hội thảo $\rightarrow$ Quay lại nữ MC.
  - Bộ phát hiện khuôn mặt tự động (Haar Cascade / YOLO) tìm thấy nhiều khuôn mặt to rõ ở giữa video (ví dụ giây 22 là chuyên gia nam trung niên đeo kính phát biểu).
  - Nếu chỉ dựa vào kích thước hộp mặt mà không soi mắt bằng `browser_vision` / `ag_cli.py`, hệ thống sẽ crop nhầm ảnh chuyên gia nam làm avatar cho kênh nữ MC "Mai"!
- **Kỷ luật khắc phục**:
  - BẮT BUỘC soi mắt kiểm định từng ứng viên qua `browser_vision` và `python D:/Taadaa/tools/ag_cli.py ask --file "<path>" "..."`.
  - Đối chiếu nhân vật với lưới 9 video trên profile người dùng cung cấp để xác định đúng ai là chủ kênh chính, ai là khách mời tạm thời.

### Bẫy 2: Diễn giả nhắm mắt / chớp mắt khi thuyết trình (Eye-Closed Speaker Trap)
- **Hiện tượng thực tế (Kênh Diễn giả Kinh doanh `@thibabxy1nr` - M55 Tik 4)**:
  - Diễn giả khi nói say sưa thường có các khoảnh khắc nhắm nghiền mắt suy tư hoặc chớp mắt dài.
  - Khung hình nhắm mắt trông rất thiếu sức sống và không đạt chuẩn avatar chuyên nghiệp.
- **Kỷ luật khắc phục**:
  - Tạo tối thiểu 2 phương án crop từ các giây khác nhau.
  - Giám định qua Vision: BẮT BUỘC xác nhận mắt mở to, ánh nhìn tập trung về phía ống kính trước khi chọn làm avatar chính thức.

---

## 2. Kỷ Luật Vận Hành Song Song Đa Thiết Bị (Parallel Multi-Device Avatar Runner)
Khi operator yêu cầu "Cho chạy song song đi" trên nhiều nick/máy:

### 1. Không gộp chung batch nếu các máy khác Tik hoặc có nguy cơ rớt USB
- Nếu gộp chung một lệnh batch nhiều máy, khi một máy bị rớt USB hoặc treo transport (như Máy 31 rớt cáp `device not found`), toàn bộ batch có thể bị abort hoặc kéo dài thời gian chờ không cần thiết.
- **Giải pháp chuẩn**: Khởi chạy các runner riêng biệt cho từng máy qua background terminal:
  ```python
  # Máy 55 (Tik 4)
  terminal(command="python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik 4 --machine 55", background=True, notify_on_complete=True, timeout=300)
  # Máy 65 (Tik 5)
  terminal(command="python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik 5 --machine 65", background=True, notify_on_complete=True, timeout=300)
  ```
- Lợi ích: Máy nào xong trước thì harness đánh thức trước, nghiệm thu dứt điểm máy đó (`exit=0, verified=True`) mà không bị nghẽn bởi máy gặp sự cố phần cứng.

---

## 3. Quy Trình Đồng Bộ & Khóa Bảo Vệ 3 Đầu Thư Mục
Trước khi kích chạy runner, BẮT BUỘC hoàn tất 3 bước chuẩn bị dữ liệu:
1. **Copy ảnh đại diện vào cả 3 đường dẫn**:
   - `D:/video goc/<F_src>/avatar.jpg`
   - `D:/video goc/<F_out>/avatar.jpg`
   - `D:/TIKTOK-videonuoinick/<F_out>/avatar.jpg`
2. **Khóa cứng chống script quét đè (SSOT Protection)**:
   - Thêm cả $F_{src}$ và $F_{out}$ vào `protected_folders` và `accounts` trong cả 2 file:
     * `D:/Taadaa/data/manual_avatar_protected_folders.json`
     * `D:/Taadaa/Tiktok-video/data/manual_avatar_protected_folders.json`
3. **Cập nhật hàng đợi**:
   - Đặt cột `Avatar` trong `Tik<Slot>.xlsx` thành `PENDING`.
   - Cập nhật bảng `avatar_replace_queue` trong SQLite `tiktok_tracker.db`.

---

## 4. Nghiệm Thu Màn Hình Máy Thật (`avatar-uploaded-confirmed.png`)
Sau khi runner báo `exit=0, verified=True`:
1. Mở thư mục run mới nhất:
   `D:/CodexRuntime/tiktok-video/runs/run_<serial>_<timestamp>/avatar-uploaded-confirmed.png`
2. Soi mắt kiểm định bằng `browser_vision` hoặc `ag_cli.py`:
   - Xác nhận đúng màn hình "Sửa hồ sơ" (Edit profile).
   - Đúng Tên (Display Name) và Username mục tiêu.
   - Vòng tròn avatar ở giữa hiển thị đúng ảnh mới, có icon máy ảnh trắng và nút chữ xanh "Thay đổi ảnh".
   - Không có popup che khuất hoặc thông báo lỗi hệ thống.
3. Đính kèm thẻ `MEDIA:<path>` trên một dòng độc lập trong báo cáo gửi User.
