# Hard Guard: Chống Ghi Đè Tài Sản Nick & Nhận Diện Đủ 8 Tài Khoản TikTok

## 1. Nguyên nhân lỗi gốc rễ (Root Cause)
- **Lệch mapping / ghi đè bậy:** Khi chạy các script remap hoặc deferred apply, việc tùy tiện gọi `delete_rows()` / `insert_rows()` làm lệch cấu trúc lưới 8 dòng cố định của từng máy trên file Excel tracking (`taikhoan_dat_v2_updated .xlsx`). Kết quả là nick mới reg bị ghi đè lên nick cũ đang hoạt động (như trường hợp M27, M37 và 69 nick bên Admin).
- **Hộp thoại USB Debugging che màn hình:** Pop-up hệ thống `UsbDebuggingActivity` bất ngờ nhảy ra sau khi nhập OTP khiến TikTok mất foreground, làm hàm `wait_login_success` bị timeout.
- **Ẩn nút "Thêm tài khoản" khi máy đủ 8 nick:** TikTok app đổi resource-id text username sang `ndk`. Nếu không quét `ndk`, hàm đếm tài khoản không phát hiện đủ 8 nick, rơi xuống báo lỗi `Không tìm thấy: ('Thêm tài khoản'` thay vì `MACHINE_FULL_8_ACCOUNTS`.

## 2. Quy tắc bảo vệ bất biến (Invariants)
1. **CẤM TUYỆT ĐỐI `delete_rows()` và `insert_rows()` trên sheet tracking chính:**
   - Mỗi máy được phân bổ cố định đúng 8 hàng dọc (theo 8 slot Folder Video). Mọi can thiệp xóa/chèn hàng dọc đều làm trôi toàn bộ các máy phía sau.
   - Thêm cột ngang (Columns) từ cột 11 trở đi được phép hoàn toàn.
2. **Hard Guard chống ghi đè ô đã có nick:**
   - Trước khi ghi bất kỳ tài khoản mới nào vào Excel tracking, bắt buộc kiểm tra:
     `if (existing_id or existing_pass) and (existing_mail and existing_mail != incoming_mail): REJECT`
   - Nếu phát hiện ô đích đã có tài khoản khác, BẮT BUỘC trả về `BLOCKED_DATA_CONFLICT` kèm blocker `OVERWRITE_REJECTED_EXISTING_ACCOUNT...` và dừng ghi. Tuyệt đối không được xóa đè nick cũ.
3. **Tự động xử lý pop-up USB Debugging:**
   - Sử dụng hàm `dismiss_usb_debugging_dialog` để tự tick *"Luôn cho phép từ máy tính này"* và bấm *"OK"* ngay khi phát hiện `UsbDebuggingActivity` trong vòng lặp chờ login.
4. **Nhận diện trần 8 tài khoản qua resource-id:**
   - Bộ đếm tài khoản trong `tap_add_account` bắt buộc phải chứa đầy đủ danh sách resource-id:
     `["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"]`
   - Khi `_acc_count >= 8`: log `MACHINE_FULL_8_ACCOUNTS`, bấm Back đóng dropdown, về Home an toàn.
