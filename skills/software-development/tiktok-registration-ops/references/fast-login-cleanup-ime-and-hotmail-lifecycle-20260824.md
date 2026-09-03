# Fast login cleanup, AdbKeyboard IME rules, and Hotmail lifecycle (2026-08-24)

## 1. Màn hình Fast Login / One-tap Login ("Tiếp tục với tên @...")
Khi mở app TikTok gặp màn hình đăng nhập nhanh "Tiếp tục với tên @username":
- **Đối chiếu kho Excel trước khi xóa:** Kiểm tra `@username` hiển thị trên màn hình với toàn bộ các file Excel kho nick (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `Tik1.xlsx` -> `Tik4.xlsx`, `gmail_clean_v2.xlsx`).
- **Nếu nick CÓ trong Excel:** Giữ nguyên phiên đăng nhập, không xóa.
- **Nếu nick KHÔNG có trong bất kỳ file Excel nào (session rác):**
  1. Nhấp vào biểu tượng 3 chấm `...` ở góc trên bên phải màn hình.
  2. Chọn `Xóa tài khoản` (hoặc `Delete account`).
  3. Bấm xác nhận `Xóa`.
  4. Bấm `Sử dụng tài khoản khác` để chuyển sang màn hình đăng ký tài khoản mới.

## 2. Chuẩn hóa Bàn phím (AdbKeyboard vs SamsungKeypad)
- **Vấn đề SamsungKeypad:** Bàn phím mặc định của Samsung thường xuyên gây lỗi:
  - Mất ký tự / mất dấu tiếng Việt Unicode khi điền tên/biệt danh TikTok qua `adb shell input text` hoặc tap phím cứng.
  - Kích hoạt popup hệ thống "Chọn bàn phím" che khuất nút Lưu/Tiếp tục.
  - Thanh gợi ý từ (predictive text) thay đổi chiều cao làm lệch tọa độ fallback.
- **Quy tắc:**
  - Toàn bộ repo farm (`Tiktok_Reg`, `tiktok-log-in`, `Hotmail`, `add mail khoi phuc`): Ép cứng chuyển sang `AdbKeyboard` (`com.github.uiautomator/.AdbKeyboard`) trước khi focus/gõ text, truyền chuỗi qua broadcast `ADB_KEYBOARD_INPUT_TEXT` (Base64 UTF-8).
  - Ngoại lệ duy nhất: Chỉ riêng `register gmail` (`gmail_reg_v10.py`) giữ SamsungKeypad để bypass bot detection của Google Play Services.

## 3. Quy trình lưu trữ vòng đời Hotmail Reg TikTok
- Hotmail mới mua: Lưu tại `D:\Taadaa\Hotmail\hotmail_input.txt`.
- Hotmail đã reg TikTok thành công (xác thực OTP qua Graph API token trên PC, **chưa login trực tiếp vào app Outlook trên máy**):
  1. Đồng bộ thông tin nick (ID TikTok, mật khẩu, email, ngày sinh, ngày reg) vào file tracking chính thức `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`.
  2. Lưu danh sách các hotmail này vào file riêng: `D:\Taadaa\Hotmail\hotmail_reg_success_chua_login_may.txt` để phục vụ luồng login app sau này.
  3. **Xóa các hotmail này ra khỏi `gmail_clean_v2.xlsx`** vì `gmail_clean_v2.xlsx` chỉ lưu các tài khoản mail đã thực sự login trên máy điện thoại.
- File `hotmail_input.txt` chỉ giữ lại các mail chưa sử dụng hoặc chưa reg thành công.

## 4. Gán Proxy / Watcher & Bỏ qua popup ViChanger
- Gán proxy cho thiết bị qua script repo `gan-proxy` (`scripts/gan_proxy_fleet.py run --machines <list>`), không mở app ViChanger thủ công trên điện thoại.
- Popup `"Message: No LSPosed access !!!"` trên app ViChanger là bình thường, runner điều khiển qua broadcast receiver `.AdbCaller`, không phụ thuộc vào giao diện hay quyền LSPosed.

## 5. Báo cáo tiếng Việt ngắn gọn, không gửi log tiếng Anh thô
- Khi batch kết thúc, không in output raw terminal tiếng Anh (như `FAILED_EXIT_1`).
- Báo cáo rõ ràng bằng tiếng Việt: Số máy thành công (kèm ID TikTok, email), số máy lỗi (nêu rõ nguyên nhân tiếng Việt), tổng số nick TikTok hiện có trong kho tracking.
