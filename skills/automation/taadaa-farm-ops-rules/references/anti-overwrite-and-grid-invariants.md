# Invariant: Chống Ghi Đè Tài Sản Nick & Khóa Cấu Trúc Lưới Excel Farm

## 1. Bản chất sự cố
- Việc các script remap/deferred tự ý gọi `delete_rows()` và `insert_rows()` làm xô lệch cấu trúc lưới 8 dòng/máy của file `taikhoan_dat_v2_updated .xlsx`, dẫn tới việc các batch đăng ký sau ghi đè tài khoản mới lên tài khoản cũ đang chạy trên máy (như M27, M37 và 69 nick bên Admin).
- Ngoài ra, sự xuất hiện bất ngờ của dialog `UsbDebuggingActivity` làm mất foreground TikTok gây timeout login, và thiếu resource-id `ndk` khiến hệ thống không nhận diện được máy đã đạt trần 8 nick.

## 2. Các quy tắc phòng chống bắt buộc (Hard Guards)
1. **CẤM TUYỆT ĐỐI `delete_rows()` và `insert_rows()` trên sheet tracking chính:**
   - 8 hàng dọc của từng máy là cố định vĩnh viễn theo Folder Video 1..8. Cấm mọi hành vi xóa hay chèn hàng dọc.
   - Được phép mở rộng cột ngang (Columns) từ cột 11 trở đi.
2. **Hard Guard chặn ghi đè tài sản:**
   - Trong mọi hàm ghi dữ liệu (`apply_deferred_result`, `upsert_tracking_account`):
     Bắt buộc kiểm tra nếu ô đích đã có `ID` hoặc `PASS` hoặc `EMAIL` khác với email mới đăng ký thì PHẢI REJECT NGAY LẬP TỨC (`BLOCKED_DATA_CONFLICT` / `CRITICAL_OVERWRITE_PREVENTED`), tuyệt đối không được ghi đè.
3. **Xử lý UsbDebuggingActivity tự động:**
   - Sử dụng `dismiss_usb_debugging_dialog` để tự tick checkbox *"Luôn cho phép"* và nhấn *"OK"*, đưa TikTok trở lại foreground.
4. **Nhận diện trần 8 tài khoản qua resource-id:**
   - Quét đầy đủ `["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"]` để raise `MACHINE_FULL_8_ACCOUNTS`, tự động hủy dropdown và về Home an toàn.
