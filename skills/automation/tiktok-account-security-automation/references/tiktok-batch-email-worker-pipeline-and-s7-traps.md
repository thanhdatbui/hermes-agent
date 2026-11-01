# Chi Tiết Vận Hành Đổi Email TikTok Hàng Loạt & Giải Quyết Điểm Nghẽn

Tài liệu đúc kết từ phiên xử lý 41 tài khoản TikTok dính Gmail DIE sang Hotmail sạch trên dàn máy Samsung Galaxy S7 (Taadaa Farm).

## 1. Kỷ Luật Vận Hành & Khắc Phục Lỗi Phong Cách Làm Việc
- **CẤM LÀM TỪNG CON NHỎ GIỌT RỒI CHAT DÔNG DÀI:**
  - Không dừng lại sau mỗi tài khoản hoàn thành để phân trần, xin xỏ hoặc giải thích dông dài.
  - Phải xây dựng cơ chế tự động hóa nền (Watchdog + Worker pool) chạy liên tục qua danh sách máy rảnh, tự ghi nhận kết quả và chỉ tổng kết khi toàn bộ luồng hoàn tất hoặc khi có lệnh.
- **TUYỆT ĐỐI CẤM TỰ Ý DẬP TIẾN TRÌNH NUÔI ACC CỦA FARM:**
  - Không bao giờ kill `run_tiktok.py`, `multi-machine-feed-session` hay xóa các file device locks `machine_*.lock.json` để tranh chấp máy làm việc.
  - Phải sử dụng mô hình **Watchdog đa luồng (workers=10)**: Kiểm tra `is_machine_busy()` và bọc qua `with_device_lock.py`. Máy nào đang nuôi acc thì đứng ngoài, chỉ nhảy vào thi công khi máy kết thúc phiên và nhả lock.

## 2. Các Bẫy Giao Diện Trên Samsung S7 & Cách Vượt Qua Bằng WinRT OCR
1. **Độ trễ Splash Screen Logo TikTok (8 - 12s):**
   - App TikTok trên máy yếu khởi động chậm. Nếu tap ngay vào tab Hồ sơ `(972, 1881)` hoặc Switcher khi app còn màn hình đen logo TikTok, thao tác sẽ bị trượt focus.
   - **Cách giải quyết:** Thiết lập `time.sleep(12)` kết hợp hàm thăm dò OCR `wait_app_ready()` kiểm tra sự xuất hiện của các keyword giao diện chính (`hö sd`, `trang ch`, `live`, `đề xuất`) trước khi tương tác.
2. **Popup Modal "Thêm vào Nhật ký" Che Khuất Giao Diện:**
   - Khi vào tab Hồ sơ, TikTok thường bung popup modal chọn ảnh/video *"Thêm vào Nhật ký"* che mất nút Menu 3 gạch ở góc trên phải.
   - **Cách giải quyết:** Kiểm tra OCR nếu thấy `nhật ký` / `nhöt` / `gần đây`, lập tức tap vào nút `x` đóng modal tại `(84, 144)` hoặc bấm phím `Back` (`keyevent 4`) trước khi mở Menu.
3. **Modal Xác Nhận 2 Lớp "Thay đổi email?":**
   - Sau khi bấm dòng "Thay đổi email", app hiện thêm 1 dialog: *"Thay đổi email? Email mới của bạn cũng sẽ được dùng cho xác minh 2 bước"* với 2 lựa chọn *"Quay lại"* và *"Tiếp tục"*.
   - **Cách giải quyết:** OCR quét modal sau khi tap `Thay đổi email`, nếu thấy text `tiếp tục` hoặc `tiép tvc`, lập tức tap vào nút Tiếp tục tại bounds nhận diện (khoảng `750, 1285`) để mở ô điền email mới.
4. **Lệch Ký Tự OCR Trong Switcher (Fuzzy Normalization):**
   - Do font chữ TikTok trên S7, WinRT OCR thường nhận diện nhầm ký tự `l` thành `I` hoa hoặc số `1` (ví dụ `@phungloan0138` $\rightarrow$ `phungIoan0138`, `@l.thanh.ngn311` $\rightarrow$ `I.thanh.ngn311`).
   - **Cách giải quyết:** Bắt buộc chuẩn hóa tên tài khoản trước khi so sánh:
     ```python
     def norm_name(s):
         return s.lower().replace('l', 'i').replace('1', 'i').replace('.', '').replace('_', '').strip()
     ```
     So sánh cả `username.lower() in text.lower()` và `norm_name(username) in norm_name(text)`.
5. **Cơ Chế Khóa Tạm Email Hotmail Tránh Tranh Chấp Song Song:**
   - Khi chạy đa luồng (`ThreadPoolExecutor max_workers=10`), các worker có thể query cùng 1 email sạch trong database cùng 1 giây.
   - **Cách giải quyết:** Ngay khi bốc mail ra khỏi bảng `mailboxes`, worker lập tức gán cờ `oauth_status = 'HOLD_CHANGE'`. Nếu quá trình rút OTP hoặc đổi thất bại thì rollback về `READY`/`NULL` để giải phóng cho tài khoản khác.
