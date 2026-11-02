# Quy Trình Mở Profile GPM Bằng Tay / Bán Tự Động Cho User Quét QR Checkpoint

## 1. Ngữ Cảnh Kích Hoạt
- Khi tài khoản Google gặp `PHONE_CHECKPOINT` (`challenge/iap`, yêu cầu quét mã QR bằng camera điện thoại thật).
- User yêu cầu: "Mở GPM để đó tao lấy camera máy tao quét xem sao" (hoặc muốn tự tay tương tác để giải cứu session).

## 2. Các Bước Vận Hành Chuẩn
1. **Tra cứu Profile ID & Proxy:**
   - Đọc CSDL GPM tại `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`.
   - Trích xuất `Id`, `Name` và chuỗi `Proxy` từ cột `JsonData`.
   - Test nhanh proxy port qua `test.taadaa.click:<port>` bằng `urllib.request.ProxyHandler` để đảm bảo proxy không bị chết / lỗi 407.
2. **Khởi động Profile qua GPM API:**
   - Gửi GET tới `http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`.
   - Nhận về `remote_debugging_address` (e.g. `127.0.0.1:57896`) và `process_id`.
3. **Điều hướng Tự Động đến Màn Hình Checkpoint (CDP):**
   - Kết nối Playwright qua `browser = p.chromium.connect_over_cdp(...)`.
   - Mở `https://accounts.google.com/ServiceLogin`.
   - Nhập đúng Email và Mật khẩu (lưu ý đối soát pass chuẩn từ `master_gmail_manager.xlsx` / `gmail_clean_v2.xlsx`).
   - Nếu gặp reCAPTCHA Enterprise (`challenge/recaptcha`):
     - Không bấm nút ngoài nếu checkbox nằm trong iframe con (`recaptcha-anchor` / `.recaptcha-checkbox`).
     - Tự động click checkbox trong frame con để pass reCAPTCHA.
   - Nếu gặp màn hình Chọn cách đăng nhập (`challenge/selection`):
     - Nếu có lựa chọn `Xác nhận email khôi phục` (`data-challengetype="12"`), điền recovery email `thanhdatbui1995@gmail.com`.
     - Nếu Google vẫn yêu cầu thiết bị / phone check: Giữ nguyên màn hình `Quét mã QR bằng điện thoại`.
4. **Hậu Kiểm & Bằng Chứng Thị Giác (Gate 6 Invariant):**
   - Chụp ảnh màn hình (`page.screenshot`) và crop vùng trung tâm chứa mã QR code.
   - BẮT BUỘC dùng `browser_vision` kiểm tra ảnh trước khi gửi: xác nhận mã QR rõ nét, email đúng, không bị che khuất.
   - Gửi ảnh qua `MEDIA:<path>` và để nguyên cửa sổ trình duyệt GPM trên màn hình cho User quét.
