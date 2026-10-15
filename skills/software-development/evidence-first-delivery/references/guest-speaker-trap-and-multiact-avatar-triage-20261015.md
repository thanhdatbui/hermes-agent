# Bẫy Khách Mời Phỏng Vấn (Guest Speaker Trap) & Phân Tầng Thẩm Định Đa Kênh (2026-10-15)

## 1. Bối Cảnh & Hiện Tượng (Incident Context)
Khi người dùng gửi ảnh chụp màn hình 3 kênh TikTok yêu cầu "Đổi ava 3 nick này":
- Kênh 1 (`@karunmmkx35` - Tên hiển thị: "Mai", Máy 65, Tik 5): Lưới video phát chương trình "BẢN TIN TÀI CHÍNH" của Thời báo Tài chính Việt Nam.
- Kênh 2 (`@ancilqaz063` - Tên hiển thị: "An", Máy 31, Tik 4): Kênh "Dì Hoan" chăm sóc mẹ & bé sau sinh.
- Kênh 3 (`@thibabxy1nr` - Tên hiển thị: "Thảo", Máy 55, Tik 4): Kênh diễn giả nam chia sẻ tư duy kinh doanh & tự do tài chính.

## 2. Bẫy Nguy Hiểm: Khách Mời Phỏng Vấn / Nhân Vật Phụ (Guest Speaker Trap)
- **Cạm bẫy**: Khi dùng thuật toán trích xuất khuôn mặt (Haar Cascade / YOLO) từ video tin tức (`1.mp4` trong F517):
  - Khung hình tại giây 3: Nữ MC dẫn tin (áo tweed hồng phấn, tóc dài uốn sóng).
  - Khung hình tại giây 22: Nam chuyên gia / đại biểu trung niên (áo vest navy, sơ mi xanh mở cúc, nốt ruồi trán) đang phát biểu tại hội trường sự kiện.
  - Cả 2 đều có kích thước bounding box mặt lớn ($w \ge 140\text{px}$). Nếu chỉ căn cứ vào diện tích khuôn mặt hoặc độ nét để tự động chọn frame, hệ thống sẽ chọn nhầm ảnh người đàn ông trung niên làm avatar cho kênh nữ MC có tên "Mai"!
- **Quy tắc giải quyết bất biến**:
  1. **Định danh Host Kênh**: So khớp giới tính và ngoại hình nhân vật với tên hiển thị của tài khoản ("Mai" là nữ, "Thảo" nhưng video là nam diễn giả...).
  2. **Tần suất xuất hiện trên lưới video**: Host là người xuất hiện trên đa số video của kênh; khách mời/người phỏng vấn chỉ xuất hiện vài giây trong 1 phóng sự.
  3. **Thẩm định độc lập qua Antigravity CLI / Vision**: Soi mắt mô tả chi tiết nhân vật (MC trường quay vs Khách mời bục sự kiện) trước khi gán avatar.

## 3. Quy Chuẩn Kỹ Thuật: FOCUSED_TEST Khi Dispatch Worker Cho Task Avatar
Khi Coordinator hết ngân sách T1 (<= 200 dòng):
- Coordinator Guard đòi hỏi format: `python -m pytest <file.py>::<test_node> -q` hoặc `python -m py_compile <file.py>`.
- Worker Sandbox chặn `python -m py_compile` (default-deny terminal), chỉ cho phép `pytest`.
- **Giải pháp**: Tạo file test pytest (ví dụ `test_apply_avatars.py`) chứa test node `test_apply_avatars_success()`. Worker thực thi và nghiệm thu bằng `python -m pytest ...`, vượt qua an toàn cả 2 lớp guard.
