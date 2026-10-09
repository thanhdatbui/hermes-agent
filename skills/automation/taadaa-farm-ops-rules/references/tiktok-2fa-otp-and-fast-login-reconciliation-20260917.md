# TikTok 2FA OTP Recovery, One-Tap Fast Login & Parasite Slot Reconciliation (2026-09-17)

## 1. Ngữ cảnh & Triệu chứng
- Khi danh sách tài khoản trên ứng dụng TikTok (Account Switcher) bị thiếu các nick Row 1 (hoặc các nick chính), runner báo lỗi `manual-needed:account-switcher-missing-expected`.
- Nếu bot tự động trigger auto-login (`reconcile_tiktok_accounts.py` hoặc login tay) mà bỏ dở màn hình OTP 2FA nhiều lần (hỏi user lòng vòng, timeout):
  - **Magic Link Trap**: TikTok tự động chuyển cơ chế xác thực từ nhập mã OTP 6 số sang bắt buộc bấm vào liên kết xác thực (Magic Link) gửi qua email, hoặc áp trần rate limit `Mã xác minh email đã hết hạn` / kẹt countdown.
  - **Trần 8 tài khoản (Hard Cap 8)**: Nếu máy đã chạm trần 8 nick trên Switcher, TikTok sẽ ẩn hoàn toàn nút "Thêm tài khoản" và từ chối nạp thêm.

## 2. Quy tắc hành động dứt khoát khi đối mặt màn hình 2FA OTP
- **CẤM DỪNG LẠI HỎI USER KHI ĐÃ ĐẾN MÀN HÌNH NHẬP OTP**:
  - Khi đã bấm vào tài khoản và màn hình hiển thị "Xác minh 2 bước" (gửi mã qua Email/Outlook hoặc Ứng dụng xác thực TOTP):
    1. **BẮT BUỘC ĐỌC OTP VÀ ĐIỀN NGAY LẬP TỨC**:
       - Với nick 2FA TOTP: Sinh mã tươi qua `automation_core.totp.generate_totp(secret)` và nhập vào `input text <code>` ngay.
       - Với nick xác minh qua Email Hotmail: Mở Outlook app trên máy (`com.microsoft.office.outlook`), đăng nhập nếu chưa có, vuốt làm mới hòm thư đến lấy mã OTP 6 số mới nhất, quay lại TikTok điền ngay lập tức.
    2. Tuyệt đối không dừng lại hỏi xin phép kiểu "anh có muốn em đọc mail lấy OTP không?", vì mỗi lần gửi mã mà không nhập kịp sẽ kích hoạt Magic Link hoặc làm mã hết hạn.

## 3. Khôi phục One-Tap Fast Login ("Chào mừng bạn trở lại")
- Khi bấm nút *"Thêm tài khoản"* ở đáy danh sách Switcher, TikTok thường mở màn hình **Fast Login ("Chào mừng bạn trở lại")** chứa cache các tài khoản từng đăng nhập trên máy đó.
- Ưu tiên tap trực tiếp vào dòng tài khoản trong danh sách Fast Login để khôi phục session ngay tại chỗ:
  - Nếu nick có 2FA TOTP: Nhập TOTP $\rightarrow$ Đăng nhập tức thì.
  - Nếu nick lưu session hoàn chỉnh: TikTok khôi phục thẳng vào Profile mà không cần challenge lại mật khẩu.

## 4. Cơ chế giải phóng Slot cho máy chạm trần 8 nick (Parasite Eviction)
- Khi máy chạm trần 8 nick mà thiếu nick chính (Row 1):
  - **BƯỚC 1: ĐỐI SOÁT TÌM NICK MỒ CÔI (PARASITE ACCOUNT)**:
    - So sánh 8 nick thực tế trên Switcher với 8 nick được phân bổ trong `taikhoan_run_safe.xlsx`.
    - Nick nào có trên máy thật nhưng **KHÔNG CÓ trong `taikhoan_run_safe.xlsx`** (do các đợt reg bù / swap trước đây chưa logout) chính là nick mồ côi.
  - **BƯỚC 2: SAO LƯU TRƯỚC KHI ĐĂNG XUẤT**:
    - Truy vết trong các bản backup của `taikhoan_dat_v2_updated .xlsx` để lấy đầy đủ: Tài khoản, Mật khẩu TikTok, Email đăng ký, Mật khẩu Mail.
    - Lưu trữ hồ sơ để chuyển sang máy còn slot trống (ví dụ máy chỉ có 6 hoặc 7 nick).
  - **BƯỚC 3: ĐĂNG XUẤT ĐƠN LẺ AN TOÀN TRÊN THIẾT BỊ**:
    - Chuyển sang nick mồ côi đó trên Switcher.
    - Vào `Hồ sơ` $\rightarrow$ `Menu 3 gạch (Menu hồ sơ)` $\rightarrow$ `Cài đặt và quyền riêng tư` $\rightarrow$ Cuộn xuống đáy $\rightarrow$ Chọn `Đăng xuất` đơn lẻ đúng tài khoản đó.
    - Sau khi đăng xuất, nút *"Thêm tài khoản"* xuất hiện trở lại ở đáy Switcher, sẵn sàng nạp nick chính.
