# Triage Batch Feed Admin (201-280): Bóc Tách O(1) Log Batch, Mất Phiên Văng Ra Màn "Chào Mừng Bạn Trở Lại", và Khôi Phục Login Thiếu Mật Khẩu TikTok (10/10/2026)

## 1. Trích Xuất & Bóc Tách Tỷ Lệ Lỗi Batch O(1) (Tránh Quét Đĩa Diện Rộng)
- **Vị trí log batch Admin**: `D:/Taadaa/runtime/admin/live/<YYYY-MM-DD>/row-<N>-<HHMMSS>/<RUN_ID>/log.jsonl`.
- **Nguyên tắc O(1)**: Không dùng loop `os.listdir()` hay `glob()` quét qua 80 thư mục máy. File `log.jsonl` tại thư mục batch gốc đã ghi nhận tập trung toàn bộ kết quả của 80 máy (`started`, `success`, `fail`, `manual-needed`, `blocked-proxy-vpn`).
- **Phân loại 4 nhóm lỗi phổ biến trong batch**:
  1. **Hạ tầng Mạng / Thiết bị (`blocked-proxy-vpn`)**:
     - `adb.exe: device offline`: Cáp USB / hub cấp nguồn giàn máy bị lỏng hoặc mất điện.
     - `dumpsys connectivity: Wi-Fi not connected`: Máy rớt kết nối Wi-Fi AP.
     - `global proxy egress IP verification failed / network unreachable`: Port PPPoE MikroTik bị timeout hoặc đứt kết nối.
  2. **Feed Detector Miss & Swipe (`fail`)**:
     - `feed not confirmed`: Mạng chậm hoặc layout TikTok thay đổi khiến detector chưa nhận diện video sau vuốt.
     - `feed swipe command failed`: ADB socket bị stall khi gửi lệnh vuốt.
  3. **Popup / Dialog Ngoại Vi (`manual-needed`)**:
     - `unexpected popup/dialog marker detected`: Popup gợi ý bạn bè, đánh giá, chính sách che màn hình.
  4. **Mất Phiên / Thiếu Session (`manual-needed:login`)**:
     - `login/account screen detected`: Thiết bị mở vào màn hình đăng nhập hoặc One-tap Login ("Chào mừng bạn trở lại").

---

## 2. Bản Chất Màn Hình "Chào Mừng Bạn Trở Lại" (One-Tap Login) & Mất Phiên Active
- **Hiện tượng**: Ca lướt feed chạy bước `tap_profile`, detector gán nhãn `manual-needed:login` với lý do `login/account screen detected`.
- **Kiểm chứng qua Vision / WinRT OCR**:
  - Giao diện hiển thị tiêu đề *"Chào mừng bạn trở lại"*, bên dưới là danh sách 1-3 tài khoản đã từng đăng nhập kèm avatar và email che sao (`k***8@hotmail.com`).
  - Phía dưới có các nút: *"+ Thêm tài khoản khác"*, *"Quản lý tài khoản"*, *"Bạn không có tài khoản? Đăng ký"*.
- **Căn nguyên**:
  - Trên thiết bị không có session nào đang ở trạng thái active (đã bị đăng xuất hoặc chuyển đổi tài khoản dang dở).
  - Tài khoản mục tiêu của Row hiện tại (ví dụ Row 4 `@chikute343`) **không nằm trong danh sách One-tap Login** của máy.
  - Guard `profile_preflight_identity_guard` nhận diện màn hình đăng nhập và dừng an toàn (fail-closed) để không lướt feed trên tài khoản khác.

---

## 3. Quy Trình Khôi Phục Login Cho Cụm Admin (STT 201-280)
Khi cần khôi phục đăng nhập cho tài khoản bị thiếu session trên máy Admin:
1. **Thiết lập biến môi trường bắt buộc**:
   - `TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml"` (để trỏ đúng Master Excel `D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2_updated .xlsx` và `gmail_clean_v2.xlsx`).
   - `ADB_SERVER_SOCKET="tcp:192.168.110.119:5037"` (kết nối remote ADB daemon của giàn Admin).
2. **Xử lý tài khoản thiếu mật khẩu TikTok (`missing_tiktok_pass`)**:
   - Trong Master Excel cụm Admin, nhiều nick chỉ lưu mật khẩu Hotmail mà cột mật khẩu TikTok là `None`.
   - `tiktok_login_v1.py` hỗ trợ cờ `--otp-only` để ép luồng đăng nhập qua mã Email OTP gửi về Hotmail (được chuyển tiếp tự động hoặc bóc tách qua token OAuth).
3. **Lệnh thực thi chuẩn bọc Device Lock**:
   ```bash
   TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml" ADB_SERVER_SOCKET="tcp:192.168.110.119:5037" python D:/Taadaa/tools/with_device_lock.py --machine <N> -- python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <N> --email <username> --ss --no-track --otp-only
   ```
   - Cờ `--no-track`: Bắt buộc để tránh lỗi OneDrive write lock (`BLOCK TRACKING_WORKBOOK_WRITE_LOCKED`).
   - Cờ `--ss`: Chụp ảnh nghiệm thu kết quả.
