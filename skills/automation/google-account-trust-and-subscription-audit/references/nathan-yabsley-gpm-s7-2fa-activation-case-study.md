# Case Study: Xử Lý Kích Hoạt 2FA Google Authenticator Cho Gmail Ngoại Cổ (Nathan Yabsley)

## 1. Hiện Tượng & Bối Cảnh
- Tài khoản: `nathan.yabsley1990@gmail.com`
- Trong file Excel lưu chuỗi: `MIZSTB35TZHWQLNQRGKXMI7NL2AJI2JQ`.
- Bên bán đăng nhập trên máy Pixel báo: *"Bác bật 2FA lên nhe bác"*.
- Khi mở profile GPM kiểm tra tại `https://myaccount.google.com/security`: Tính năng `2-Step Verification` thực tế đang ở trạng thái **ĐÃ TẮT**.

## 2. Các Bước Vận Hành Cơ Giới Hóa Thực Tế
1. **Khởi động GPM qua CDP:**
   - Cập nhật proxy sang cổng sống `5101` (tránh rớt mạng/proxy cũ).
   - Kết nối Playwright tới `http://127.0.0.1:64082`.
2. **Vượt Google Prompt trên Samsung S7 (Máy 56):**
   - Google yêu cầu nhập số trùng khớp hiển thị trên màn hình máy tính (Số `53`, sau đó số `71`).
   - Dùng lệnh bọc lock an toàn:
     `python D:/Taadaa/tools/with_device_lock.py --machine 56 -- adb -s ce0516055108a70e01 shell input keyevent 224`
   - Chụp màn hình `exec-out screencap -p`, chạy `run_winrt_ocr.py` để tìm tọa độ nút "Có, chọn số trùng khớp" và nút số tương ứng.
   - Bấm `input tap` trực tiếp để phê duyệt phiên.
3. **Kích hoạt 2FA Authenticator:**
   - Điều hướng tới `https://myaccount.google.com/two-step-verification/authenticator?hl=vi`.
   - Bấm "Thiết lập ứng dụng xác thực" -> "Không thể quét mã?".
   - Lấy chuỗi khóa mới hiển thị trên Google:
     `qluk 3yei g56x 4dh2 2tvg l4x4 2m7a nz4k`
   - Xử lý Base32: Thay thế khoảng trắng, chuyển chữ `l` thành `L` -> `QLUK3YEIG56X4DH22TVGL4X42M7ANZ4K`.
   - Sinh OTP bằng Python:
     `pyotp.TOTP('QLUK3YEIG56X4DH22TVGL4X42M7ANZ4K').now()` -> `535665`.
   - Điền OTP vào ô input và bấm "Xác minh".
4. **Hậu Kiểm Bằng Chứng Thị Giác (Gate 6):**
   - Chụp màn hình `D:/Taadaa/evidence/nathan_2fa_final_success.png`.
   - Chạy `run_winrt_ocr.py` xác nhận: dòng `Authenticator | Đã thêm vừa xong` xuất hiện.
5. **Đồng Bộ Dữ Liệu:**
   - Cập nhật `twofa_secret = 'QLUK3YEIG56X4DH22TVGL4X42M7ANZ4K'` vào bảng `mailboxes` và `tiktok_accounts` trong `D:/Taadaa/data/farm_master.db`.
