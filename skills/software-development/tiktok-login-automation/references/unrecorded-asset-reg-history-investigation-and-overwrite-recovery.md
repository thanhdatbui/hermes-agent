# Điều Tra Lịch Sử Đăng Ký (Reg History) Cho Tài Khoản Lệch Dữ Liệu & Phục Hồi Hàng Bị Ghi Đè (2026-10-02)

## 1. Bối cảnh & Hiện tượng (Sự cố Nick `@gaetiwcu04c` trên Máy 66)
- Khi đối soát Account Switcher trên Máy 66, phát hiện tài khoản `@gaetiwcu04c` đang active trên máy nhưng tìm kiếm trong `taikhoan_run_safe.xlsx` và `taikhoan_dat_v2_updated .xlsx` hoàn toàn không có thông tin.
- Nếu vội vàng kết luận là "nick rác / nick lạ" và logout, nông trại sẽ mất vĩnh viễn một tài khoản TikTok đã được ngâm và nuôi ổn định suốt nhiều tuần.

---

## 2. Quy Trình Điều Tra Lịch Sử Reg Gốc (A-Z Investigation)
Khi gặp một nick lạ trên máy không có trong master workbook, bắt buộc thực hiện quy trình truy vết theo thứ tự:

### Bước 1: Tra cứu nhanh trong Log Đăng Ký Tổng Quan
- **Đường dẫn**: `D:\Taadaa\Tiktok_Reg\social_reg_log.txt`
- **Cách tìm (O(1) không quét đĩa)**:
  Đọc file tìm chuỗi username (ví dụ `gaetiwcu` hoặc `@gaetiwcu04c`).
- **Dữ liệu thu được**:
  - Dòng ghi nhận profile: `[profile] handle=@gaetiwcu04c name='Đinh Phương Nam'`
  - Đường dẫn file JSON deferred tracking tương ứng trong batch chạy:
    `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\20260826-075147\batch_2\stt_66\tracking_result_stt66_gaeticiaalou_hotmail.com.json`

### Bước 2: Đọc File Kết Quả Deferred Tracking JSON
Mọi phiên đăng ký thành công của farm đều lưu một bản ghi JSON độc lập chứa toàn bộ credential:
- `stt`: Máy đăng ký (ví dụ `66`)
- `serial`: Serial thiết bị (ví dụ `ce12160c2a99962905`)
- `tik`: Số thứ tự tik / folder video
- `tracking_row`: Vị trí dòng Excel được gán lúc đăng ký (ví dụ dòng `527`)
- `tiktok_id`: Username TikTok (`gaetiwcu04c`)
- `password`: Mật khẩu TikTok gốc (`4#1Uf9eqE%0NB$`)
- `email`: Hòm thư đăng ký (`gaeticiaalou@hotmail.com`)
- `mail_password`: Mật khẩu mail (`d4s11singh`)
- `created_date`: Ngày đăng ký (`2026-08-25`)
- `proof_screenshot`: Ảnh chụp màn hình Profile sau đăng ký (`D:\Taadaa\Tiktok_Reg\screenshots_social\profile_66_after_ensure_*.png`)

---

## 3. Bản Chất Kỹ Thuật: Cạm Bẫy Ghi Đè Dòng Excel (Row Overwrite Trap)
- **Cơ chế gây lỗi**:
  1. Ngày 26/08, hệ thống đăng ký thành công `@gaetiwcu04c` cho Máy 66 và ghi vào dòng 527.
  2. Ngày 13/09 (18 ngày sau), một đợt đăng ký mới chạy và gán nick mới `michamehywy` vào đúng dòng 527 trong Excel mà không kiểm tra dòng đó đã có tài khoản đang sống trên máy.
  3. Excel bị ghi đè thông tin nick mới, nhưng trên thiết bị Android Máy 66, nick cũ `@gaetiwcu04c` **chưa bao giờ bị logout**.
  4. Hậu quả: Máy 66 thực tế chứa cả 2 nick (`gaetiwcu04c` và `michamehywy`), khiến tổng số nick trên máy đạt trần 8 nick, trong khi Excel lại gán thêm một nick khác (`phamnam1805`) vào dòng 523 dẫn đến lỗi `ACCOUNT_MISSING`.

---

## 4. Kỷ Luật Xử Lý & Khôi Phục Tài Sản
1. **Tuyệt đối KHÔNG LOGOUT nick được tìm thấy lịch sử reg gốc**:
   - Đây là tài sản chính chủ 100% của thiết bị đó, được tạo bởi chính hệ thống farm.
2. **Quy trình đồng bộ hóa ngược (Backfill Sync)**:
   - Cập nhật lại thông tin credential đầy đủ (ID, Pass, Mail, Pass Mail, Ngày tạo) từ file JSON deferred result vào lại `taikhoan_dat_v2_updated .xlsx` và `taikhoan_run_safe.xlsx`.
   - Điều chỉnh vị trí hàng tương ứng cho máy để phản ánh đúng 8 tài khoản thực tế đang hoạt động trên thiết bị.
