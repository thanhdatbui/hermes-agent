# Pitfalls chẩn đoán lỗi Preflight Reg & Login TikTok

## 1. Pop-up USB Debugging (`UsbDebuggingActivity`) gây giả lập `Timeout cho login`
- **Triệu chứng:** Script báo `Timeout cho login` (ví dụ trên Máy 20, 46, 63), dù trước đó log đã ghi nhận nhập OTP thành công.
- **Hiện trường XML:**
  - `mCurrentFocus`: `com.android.systemui/com.android.systemui.usb.UsbDebuggingActivity`
  - Tiêu đề: `Cho phép gỡ lỗi USB?` / `Allow USB debugging?`
  - Checkbox: `Luôn cho phép từ máy tính này` / `Always allow from this computer` (`com.android.systemui:id/checkBoxText`)
  - Nút: `OK` (`android:id/button1`)
- **Nguyên nhân:** Khi ADB reset hoặc key RSA chưa lưu vĩnh viễn, pop-up hệ thống nhảy ra đè lên màn hình TikTok lúc app đang chuyển sang Home Feed / Profile. Foreground bị chiếm bởi System UI khiến `wait_login_success` không thấy `com.ss.android.ugc.trill`, rơi vào vòng lặp chờ rồi ném Timeout.
- **Xử lý:**
  - Bổ sung hàm `dismiss_usb_debugging_dialog(device_id, xml)`: Tự động tìm text *"Luôn cho phép từ máy tính này"*, tick checkbox, sau đó tap nút *"OK"*.
  - Tích hợp vào `_dismiss_system_popups` và ngay đầu vòng lặp `wait_login_success` để khôi phục foreground TikTok.

## 2. Máy đủ 8 tài khoản ẩn nút "Thêm tài khoản" (`04_add_account`)
- **Triệu chứng:** Báo lỗi `[04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)` (ví dụ trên Máy 27, 37).
- **Hiện trường XML:**
  - Màn hình: Sheet `Chuyển đổi tài khoản` (`com.ss.android.ugc.trill:id/g1z`, title `psy`).
  - Danh sách tài khoản: Đã có đúng 8 user nodes.
  - Trên TikTok app, khi đạt trần 8 nick, nút *"Thêm tài khoản"* sẽ tự động bị ẩn hoàn toàn.
- **Nguyên nhân:**
  - Hàm kiểm tra số lượng tài khoản cũ chỉ đếm các resource-id cũ: `["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli"]`.
  - Trên các phiên bản TikTok mới (v30+), resource-id của username đổi sang `com.ss.android.ugc.trill:id/ndk` (container `ls_`).
  - Khi không khớp ID cũ, số lượng tài khoản đếm được là 0 $\rightarrow$ script không ném `MACHINE_FULL_8_ACCOUNTS` mà trôi xuống dưới báo lỗi UI không tìm thấy nút.
- **Xử lý:**
  - Thêm `ndk` vào danh sách keys kiểm tra: `["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"]`.
  - Kiểm tra nếu `_acc_count >= 8`: raise `MACHINE_FULL_8_ACCOUNTS` và thoát an toàn về Home.

## 3. Tránh nghẽn I/O khi inspect hiện trường Farm (Timeout 180s)
- Thư mục `screenshots_social` chứa hàng chục nghìn ảnh, và file `social_reg_log.txt` nặng >200MB.
- **CẤM:** Dùng `ls -lt`, `find`, hay `readlines()` quét toàn bộ thư mục/file lớn vì sẽ gây treo 180s trên Windows NTFS / MSYS git-bash.
- **CHUẨN:**
  - Dùng `python D:/Taadaa/tools/inspect_machine.py <N>` lấy focus/pin/màn hình $O(1)$.
  - Trích xuất log đuôi bằng Python `f.seek(max(0, size - N))` O(1).
  - Đọc trực tiếp UI XML dump gần nhất trong `D:\Taadaa\runtime\kibe\artifacts\ui_dumps\`.
