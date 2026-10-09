# Bảo Toàn Tài Sản Farm: Quy Tắc Xử Lý Máy Full 8 Nick & Khắc Phục MtpApplication USB

## 1. Không Có Khái Niệm "Nick Rác Lạ" Trên Farm
- Mọi tài khoản hiện diện trên account switcher của TikTok đều là **tài sản hợp lệ của user** (được reg từ các đợt chạy trước hoặc nằm trong cache deferred tracking `D:/Taadaa/runtime/kibe/artifacts/runs/social-batch-all`).
- TUYỆT ĐỐI CẤM Coordinator/Worker kết luận là "nick ký sinh ngoài" hay "nick rác" rồi vội vã logout.
- BẮT BUỘC tra cứu artifact JSON hoặc các bản backup master (`.bak-clean-tatieu...`) để lấy đầy đủ:
  - TikTok Username
  - TikTok Password
  - Email đăng ký
  - Mật khẩu Email

## 2. Bản Chất Lỗi Báo Full 8 Nick & Ẩn Nút "Thêm tài khoản"
- Khi TikTok đã nạp đủ 8 nick trên switcher, app tự động ẩn nút `Thêm tài khoản`.
- Trên TikTok bản cũ: `social_reg_v1.py` nhận diện đủ 8 nick `lli` -> ném `MACHINE_FULL_8_ACCOUNTS`.
- Trên TikTok bản mới 46.x: resource-id đổi thành `omm`, `omr`, `onj`... nên code không đếm được, nhưng vì nút "Thêm tài khoản" bị ẩn -> ném lỗi `Không tìm thấy: ('Thêm tài khoản'...)`.
- **Nguyên nhân gốc rễ**: Trước commit `fc80f09` (17/09/2026), script chạy batch ở chế độ "proof-only" chỉ lưu JSON deferred mà không đồng bộ vào Excel. Khi chạy reg bù Row 8, detector thấy slot trống nên tiếp tục dispatch reg lại, đụng phải 8 nick có sẵn trên máy.

## 3. Quy Trình Backfill Slot Row 8 An Toàn
1. Quét danh sách nick thực tế trên máy qua ATX JSON-RPC dump.
2. Tra cứu info nick trong artifact JSON deferred hoặc file backup master.
3. Kiểm tra xem nick đó có bị trùng lặp ở máy khác không trên `Tik1.xlsx` -> `Tik8.xlsx`.
4. Nếu nick độc quyền trên máy đó:
   - Gán nick vào slot Row 8 của máy trong `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx`.
   - Gán username vào `D:/OneDrive/TaadaaData/kibe/Tik8.xlsx`.
   - Tạo bản backup trước khi sửa file Excel.

## 4. Tắt Vĩnh Viễn Popup USB Connection Trên Samsung Galaxy S7
- Dialog `com.samsung.android.MtpApplication/.USBConnection` ("Chú ý: Thiết bị được kết nối không thể truy cập...") gây cản trở ADB bridge, làm văng timeout 20s.
- Lệnh tắt tận gốc (chạy 1 lần tắt vĩnh viễn):
  ```bash
  adb -s <serial> shell pm disable-user --user 0 com.samsung.android.MtpApplication
  ```
