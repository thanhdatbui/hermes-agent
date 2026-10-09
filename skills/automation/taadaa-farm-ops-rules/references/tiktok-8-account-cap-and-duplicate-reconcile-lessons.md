# TikTok Multi-Account Cap & Duplicate Slot Reconcile Lessons

## 1. Bản chất sự cố: 8-Account Cap & False "Row Empty"
- Trên ứng dụng TikTok Android, giới hạn cứng tối đa là **8 tài khoản / thiết bị**. Khi đạt 8 nick, nút "Thêm tài khoản" (`Add account`) bị ẩn hoàn toàn khỏi sheet `Chuyển đổi tài khoản`.
- Khi runner kiểm tra Excel thấy một hàng tài khoản trống (ví dụ `Row 7 is empty`), hệ thống sẽ gọi `ensure_row_accounts.py` để reg bù.
- **Nguyên nhân cốt lõi gây kẹt lặp đi lặp lại:**
  1. **Duplicate Slot trong Excel:** File Excel bị copy/paste đè nick ở slot trước xuống slot cuối (như M13, M24 có slot 6 và slot 8 trùng nick, slot 7 để trống). Bộ lọc sync tự động loại bỏ duplicate khiến Row 7/8 bị coi là rỗng.
  2. **Nick bị login chéo máy:** Do lịch sử cấp phát mail cũ không có chốt chặn độc quyền, một số tài khoản đã đăng nhập chéo vào thiết bị khác (M13 chứa nick của M37, M24 chứa nick của M51).
  3. Khi máy thực tế đã đủ 8 nick nhưng Excel báo thiếu, lệnh reg bù sẽ nhảy vào và crash ngay lập tức tại bước `[04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)`.

## 2. Kỷ luật Điều phối & Tránh "Hứa suông / Quên cài Watchdog"
- **Sai lầm nghiêm trọng (Anti-Pattern):** Trả lời "vâng em canh..." nhưng không thực sự tạo cronjob/watchdog trong hệ thống, dẫn đến bỏ lỡ khung giờ trống vàng (Dead-window giữa các phiên/ca nuôi) và trôi sang ca sau.
- **Quy tắc bất di bất dịch:**
  1. Khi nhận lệnh canh theo sự kiện kết thúc phiên/ca, **BẮT BUỘC TẠO CRON WATCHDOG NGAY TẠI TURN ĐÓ** qua công cụ `cronjob(action='create')`.
  2. Script watchdog phải thiết kế theo cơ chế **Event-driven**: Đọc `run_manifest.json` của phiên đang chạy để kiểm tra trường `end_time` VÀ kiểm tra thư mục `device-locks` sạch hoàn toàn (0 locks) mới được nổ task.
  3. Tuyệt đối không dùng mốc giờ cố định cứng nhắc (fixed clock) khi tiến trình thực tế có thể chạy sớm hoặc trễ.

## 3. Quy trình Reconcile & Phục hồi Nút "Thêm tài khoản"
1. **Làm sạch Excel trước:** Quét và xóa bỏ các ID bị duplicate ở các hàng cuối cùng trong `taikhoan_dat_v2_updated .xlsx` về `None`, sau đó sync sang `taikhoan_run_safe.xlsx`.
2. **Kiểm tra thực tế UI Switcher:** Mở sheet `Chuyển đổi tài khoản`, kiểm tra danh sách tài khoản thực tế trên app.
3. **Logout nick ký sinh:** Nếu máy chứa nick đã được quản lý ở máy khác, switch sang nick đó -> vào `Cài đặt và quyền riêng tư` -> cuộn cuối -> `Đăng xuất` để hạ tổng số nick xuống 7.
4. **Xác nhận nút Add Account:** Chụp ảnh màn hình kiểm chứng nút "Thêm tài khoản" đã hiển thị lại trước khi chuyển sang bước reg bù.
