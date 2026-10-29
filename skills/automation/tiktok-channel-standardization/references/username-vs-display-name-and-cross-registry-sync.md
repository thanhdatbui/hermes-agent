# Username vs Display Name & Cross-Registry Synchronicity Protocol

## 1. Phân Biệt Bản Chất Tên Hiển Thị (Nickname) vs Username (Handle)
- **Tên hiển thị (Display Name / Nickname):**
  - Giới hạn: Đổi 1 lần / 7 ngày.
  - Mục đích: Định vị nhân vật người thật (Persona), dùng tiếng Việt có dấu chuẩn mực (ví dụ: `Lý Thị Hoàn`, `Thùy Dung`, `Lý Kim Loan`).
  - Tác động hạ tầng: Thuần túy là nhãn UI, KHÔNG ảnh hưởng đến Primary Key của hệ thống automation.
- **Username (TikTok ID / Handle `@...`):**
  - Giới hạn: Đổi 1 lần / 30 ngày (TikTok giới hạn cứng toàn cầu).
  - Hiện trạng farm: Đa số nick reg tự động bằng Hotmail/Outlook ban đầu mang ID mặc định rác (`user51904226`) hoặc chuỗi ký tự ngẫu nhiên (`slosspbb3qo`, `arianjwj9qm`).
  - Tác động hạ tầng: **LÀ KHÓA ĐỊNH DANH DUY NHẤT (PRIMARY KEY)** của tài khoản xuyên suốt toàn bộ hệ sinh thái Phone Farm.

## 2. Tiêu Chuẩn Chọn Username Chuẩn Hóa
- **Quy tắc đặt tên:**
  - Viết liền không dấu, chỉ gồm chữ thường (`a-z`), số (`0-9`), gạch dưới (`_`) hoặc dấu chấm (`.`).
  - Bám sát Họ Tên hiển thị + Năm sinh / Hậu tố ngách sạch sẽ:
    - *Chuẩn cá nhân:* `lythihoan2508`, `lythihoan_official`
    - *Gọn đẹp / Ngách:* `lyhoan.music`, `hoanly.daily`
    - *Tự nhiên:* `hoanly_98`, `lythihoan.vn`
  - Tuyệt đối tránh: Chuỗi ký tự vô nghĩa khó nhớ, số đuôi quá dài (`user51904226`), ký tự nhạy cảm.

## 3. Quy Trình Thi Công & Bẫy Mất Đồng Bộ Đa Tầng (Cross-Registry Trap)
*CẢNH BÁO BẢO VỆ TOÀN FARM: Đổi Username trên app TikTok mà không đồng bộ ngay cơ sở dữ liệu sẽ khiến toàn bộ Runner (Feed, Upload Hook, Follow Watchdog) ở các ca kế tiếp bị tê liệt (báo lỗi `account_missing` hoặc không switch được profile).*

### Bước 1: Kiểm Tra Điều Kiện & Đổi Trên Thiết Bị Thật
1. Kiểm tra ngày reg / lần đổi trước: Phải đủ $\ge 30$ ngày.
2. Điều hướng vào TikTok: `Hồ sơ` ➔ `Sửa hồ sơ` ➔ `Tên người dùng`.
3. Nhập Username mới, đợi TikTok tick xanh xác nhận tên chưa bị trùng trên toàn cầu ➔ Bấm `Lưu` ➔ Bấm `Đặt tên người dùng`.
4. Chụp ảnh nghiệm thu UI xác nhận màn hình Profile hiển thị đúng Handle mới.

### Bước 2: Bắt Buộc Đồng Bộ Nguyên Tử (Atomic Cross-Registry Sync)
Ngay sau khi đổi thành công trên thiết bị, Coordinator BẮT BUỘC cập nhật đồng thời 3 tầng dữ liệu:
1. **Workbook phân ca tương ứng:**
   - Cập nhật cột `ID TikTok` (Cột C) trong file `Tik<N>.xlsx` tương ứng (`D:/OneDrive/TaadaaData/kibe/Tik<N>.xlsx` hoặc `admin/Tik<N>.xlsx`).
2. **Master Workbook chạy an toàn:**
   - Cập nhật dòng của Máy/Slot đó trong `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` và `taikhoan_dat_v2_updated .xlsx`.
3. **Cơ sở dữ liệu SQLite Tracker:**
   - Trong `D:/OneDrive/TaadaaData/tiktok_tracker.db`:
     ```sql
     UPDATE account_mapping SET username = '<new_uid>' WHERE username = '<old_uid>' AND may = <may> AND tik = <tik>;
     UPDATE farm_account_info SET username = '<new_uid>' WHERE username = '<old_uid>' AND may = <may> AND tik = <tik>;
     ```
4. **Kiểm chứng:** Chạy lệnh đọc lại hàng từ `account_source.py` hoặc inspect O(1) để xác nhận bot đã nhận diện ID mới 100%.
