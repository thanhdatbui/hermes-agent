# Tracking Never-Overwrite Guard & Farm Safety Rules

## 1. Nguyên tắc tối thượng về tài sản nick
- Mọi tài khoản TikTok đã đăng ký (dù là Gmail hay Hotmail, cũ hay mới) đều là tài sản người dùng.
- TUYỆT ĐỐI CẤM bất kỳ script nào ghi đè hoặc xoá nick cũ trong workbook tracking (`taikhoan_dat_v2_updated .xlsx`).

## 2. Hard Guard trong Deferred Tracking Writer
- Trước khi ghi thông tin đăng ký vào bất kỳ hàng nào (`check.row` / `target_row`), bắt buộc kiểm tra xem ô đích đã có dữ liệu hay chưa.
- Nếu ô đích đã có `ID` hoặc `PASS`, và `GMAIL` hiện có khác với email mới đăng ký (`existing_mail != new_mail`):
  - BẮT BUỘC CHẶN NGAY LẬP TỨC (`status="BLOCKED_DATA_CONFLICT"`, `blocker="OVERWRITE_REJECTED_EXISTING_ACCOUNT_..."` hoặc raise `RuntimeError("CRITICAL_OVERWRITE_PREVENTED")`).
  - Tuyệt đối không được phép ghi đè!

## 2.1. Pitfall khi viết Unit Test mock `_acquire_tracking_write_phase` & `upsert_tracking_account`
- `release_tracking_lock = _acquire_tracking_write_phase(...)` trả về một object và sau đó được gọi như một callable `release_tracking_lock()`. Mọi mock `FakeLock` bắt buộc phải triển khai `__call__(self)` (nếu không sẽ văng `'FakeLock' object is not callable`).
- Trong `upsert_tracking_account`, sau khi ghi workbook có lệnh gọi `os.fsync(locked_file.fileno())`. Nếu mock dùng `io.BytesIO()`, lệnh `.fileno()` sẽ văng `io.UnsupportedOperation: fileno` và bị khối `except Exception` bắt rồi ghi vào `tracking_pending.csv` thay vì raise lỗi logic mong muốn. Khi mock file, cần mock `fileno()` hoặc dùng file thật/tempfile có descriptor hợp lệ.
- Cơ chế tìm `target_row`: `upsert_tracking_account` tìm dòng có `gmail == email`. Nếu truyền email mới khác email cũ mà máy còn chỗ, nó sẽ coi là insert/reuse slot trống chứ không coi là overwrite. Để test guard overwrite, cần đảm bảo điều kiện trigger đúng dòng mục tiêu.

## 3. Cấm biến đổi hàng dọc (Rows)
- File tracking quy định cứng mỗi máy sở hữu đúng 8 hàng (ứng với 8 slot Folder Video).
- CẤM TUYỆT ĐỐI dùng `sheet.delete_rows()` hoặc `sheet.insert_rows()` trên sheet tracking chính vì sẽ phá vỡ trật tự lưới 8 hàng/máy, làm xô lệch toàn bộ chỉ số dòng vật lý của các máy phía sau.
- Thêm cột (Columns chiều ngang: Note, 2FA, Proxy...) thì hoàn toàn được phép vì không làm xô lệch hàng dọc.

## 4. Nhận diện máy đã đủ 8 tài khoản (Limit 8 Nick)
- Khi một máy đã đăng nhập đủ 8 tài khoản, giao diện TikTok sẽ tự ẩn nút "Thêm tài khoản".
- Phải quét toàn bộ các biến thể resource-id của danh sách tài khoản (kể cả obfuscated id như `ndk`, `lrq`, `lli`, `lpw`...):
  - Nếu đếm đủ >= 8 nick: Raise `MACHINE_FULL_8_ACCOUNTS`, bấm Back để đóng dropdown và về Home an toàn.
  - Cấm để lọt rơi xuống exception "Không tìm thấy nút Thêm tài khoản".

## 5. Xử lý popup hệ thống USB Debugging
- Hộp thoại `com.android.systemui.usb.UsbDebuggingActivity` ("Cho phép gỡ lỗi USB?") có thể bất ngờ xuất hiện che mất foreground TikTok ngay sau khi nhập OTP.
- Luôn kiểm tra và gọi `dismiss_usb_debugging_dialog` trong vòng lặp `wait_login_success` và `_dismiss_system_popups`: tự động tick checkbox "Luôn cho phép từ máy tính này" và nhấn "OK" để đưa TikTok trở lại foreground.
