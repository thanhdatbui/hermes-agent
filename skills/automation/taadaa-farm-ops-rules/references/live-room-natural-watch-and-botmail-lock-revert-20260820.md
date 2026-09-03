# Xem LIVE Tự Nhiên (5-10s) & Revert Patch Sai Do Va Chạm Khóa Botmail (20/08/2026)

## 1. QUY TẮC XEM LIVESTREAM TIKTOK TRƯỚC KHI THOÁT
- **Hiện tượng**: Khi đang lướt feed ngẫu nhiên lọt vào phòng phát trực tiếp (LIVE room).
- **Hành vi tự nhiên hóa bắt buộc**:
  - Không được bấm thoát hoặc Back ngay lập tức (dễ bị nhận diện là bot).
  - Bắt buộc dừng lại xem LIVE trong khoảng **5.0 – 9.5 giây** (`random.uniform(5.0, 9.5)`) như người dùng thật.
  - Sau đó mới thực hiện tap vào nút **✕** (`id/close`, `id/e63`, `id/e6n` hoặc tọa độ `[945, 45]`), nếu vẫn chưa ra thì gửi phím `BACK` để trở lại video feed For You.

---

## 2. BẢO VỆ DEVICE LOCK LIÊN TIẾN TRÌNH & REVERT PATCH SAI DO VA CHẠM KHÓA
- **Nguyên nhân gốc rễ sự cố**:
  - Khi tiến trình `Hotmail / Botmail login` đang chạy trên máy (ví dụ Máy 1, Máy 38, Máy 44), màn hình hệ thống Android hiển thị form *"Thêm tài khoản / Cài đặt Email / Thiết lập tài khoản"*.
  - Tiến trình Cron nuôi acc chạy trùng thời điểm $\rightarrow$ nhầm tưởng TikTok gặp popup lạ $\rightarrow$ AI Auto-Recovery tự động sinh ra các handler đóng màn hình email (`dismiss_add_account_screen`, `dismiss_email_account_setup_screen`, `dismiss_email_update_popup`).
- **Xử lý & Khắc phục chuẩn**:
  - **Revert toàn bộ**: Đã gỡ bỏ sạch sẽ các hàm can thiệp màn hình email/account setup sai lệch ra khỏi `benign_popup.py`.
  - **Preflight Lock Gate**: Bắt buộc kiểm tra `inspect_device_lock(machine)` tại ngay **Bước 0** của AI Auto-Recovery và Feed Runner. Nếu máy đang có lock active từ flow khác $\rightarrow$ **DỪNG NGAY LẬP TỨC**, tuyệt đối không can thiệp, không gửi lệnh ADB và không tự ý sinh code patch.
