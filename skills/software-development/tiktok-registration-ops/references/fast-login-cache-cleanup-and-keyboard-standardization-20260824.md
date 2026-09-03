# Fast-Login Cleanup Protocol & Keyboard Standardization (2026-08-24)

## 1. Màn hình Fast Login / "Tiếp tục với tên @" và Quy tắc đối chiếu Excel
Khi mở TikTok trên máy farm gặp màn hình "Đăng nhập nhanh" / "Tiếp tục với tên @username":
- **BẮT BUỘC ĐỐI CHIẾU KHO EXCEL TRƯỚC KHI XÓA:**
  - Quét danh sách nick hợp lệ từ toàn bộ các file: `Tik1.xlsx` -> `Tik4.xlsx`, `taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `gmail_clean_v2.xlsx`.
  - **Nếu nick CÓ trong Excel:** Giữ nguyên tài khoản, không được xóa.
  - **Nếu nick KHÔNG CÓ trong bất kỳ file Excel nào:** Đây là session rác cũ lưu trong cache app.
- **Quy trình xóa session rác:**
  1. Bấm vào biểu tượng menu 3 chấm (`...`) ở góc trên bên phải màn hình.
  2. Bấm chọn `🗑 Xóa tài khoản` (Delete account).
  3. Bấm xác nhận xóa.
  4. Bấm `Sử dụng tài khoản khác` (Use another account) ở dưới đáy màn hình để vào luồng đăng ký tài khoản mới.

## 2. Tiêu chuẩn Bàn phím Farm (AdbKeyboard vs Samsung Keyboard)
- **Chuẩn hóa 100% sang AdbKeyboard (`com.github.uiautomator/.AdbKeyboard`):**
  - Áp dụng cho toàn bộ repo: `Tiktok_Reg`, `tiktok-log-in`, `Hotmail`, `add mail khoi phuc`.
  - Mọi thao tác nhập text, nickname tiếng Việt, mật khẩu đều phải đi qua broadcast `ADB_KEYBOARD_INPUT_TEXT` (Base64 UTF-8) của `AdbKeyboard`.
  - **Lý do:** Bàn phím Samsung (`SamsungKeypad`) làm mất dấu tiếng Việt, hay hiện popup chọn bàn phím che khuất UI nút bấm và thanh gợi ý làm nhảy layout.
- **Ngoại lệ duy nhất:** Chỉ riêng repo `register gmail` (`gmail_reg_v10.py`) giữ lại SamsungKeypad theo quy tắc giả lập người (`human_type`) để bypass bot-detection của Google Play Services.

## 3. Gán Proxy / VPN qua repo `gan-proxy`
- Gán proxy cho thiết bị BẮT BUỘC chạy qua script `D:\Taadaa\gan-proxy\scripts\gan_proxy_fleet.py` (hoặc `vi_changer_runner.py`), tuyệt đối không mở app thao tác bằng tay.
- Popup `Message: No LSPosed access !!!` trên app ViChanger là hành vi mặc định bình thường khi mở app, không ảnh hưởng đến luồng gán proxy qua broadcast ADB.
- Kiểm tra proxy sống: Gửi broadcast `am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller` nhận `result=200` và `data="<IP>"`.
