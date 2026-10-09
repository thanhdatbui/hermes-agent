# Checkmail.live Full Inventory Automation & Security Policy

## 1. Nguyên tắc Bảo mật Bất Biến (Zero-Credential Leak)
- Khi gọi các dịch vụ kiểm tra trạng thái email bên ngoài (`checkmail.live`, các API check live):
  - **CHỈ ĐƯỢC PHÉP** gửi danh sách địa chỉ email thô (định dạng `xxx@gmail.com`).
  - **CẤM TUYỆT ĐỐI** đọc, bóc tách, ghép chuỗi hoặc gửi mật khẩu, Recovery Email, mã OTP, TOTP Secret Key lên tool ngoài.

## 2. Kỹ thuật Bypass & CodeMirror Automation (2026-09-04)
- Trang `checkmail.live` yêu cầu session đăng nhập để cấp `API Key` (tránh popup alert *"You are not logged in"*).
- **Cơ chế vượt Cloudflare Turnstile:**
  - Sử dụng Playwright persistent context kết nối qua Mobile Proxy Farm: `http://test.taadaa.click:5101` (`mobi1:TaadaaMobi#2026!`).
  - Args: `--disable-blink-features=AutomationControlled`, Chrome Core 142.
  - Tự động nạp API key vào `document.getElementById('api-key')`.
- **Tương tác CodeMirror:**
  - Nhập dữ liệu: `window.editor.setValue(email_payload)`
  - Kích hoạt check: `document.getElementById('btn-check').click()`
  - Lấy kết quả thời gian thực: `window.liveResultEditor.getValue()`
  - Tốc độ xử lý: ~75 email / 1.5 giây.

## 3. Quy trình Kiểm tra Toàn Bộ Kho Gmail Tổng (497 Tài khoản)
1. **Nguồn dữ liệu:**
   - `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (4 sheets)
   - `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`
   - `D:\OneDrive\TaadaaData\kibe\gmail_live_tong.txt`
2. **Deduplicate:** Gộp tất cả các nguồn và lọc unique trước khi gửi.
3. **Phân loại kết quả:**
   - `[Live]`: Lưu vào `D:\OneDrive\TaadaaData\kibe\gmail_live_tong.txt` và cập nhật cột `Trạng Thái = LIVE`.
   - `[die]`, `[Disabled]`, `[Unregistered]`: Lưu vào `checkmail_results/gmail_die_list.txt` và cập nhật cột `Trạng Thái = DIE`.
4. **Tự động sao lưu Workbook:** Luôn tạo bản sao lưu trong `workbook-backups/` trước khi ghi đè cột trạng thái.
