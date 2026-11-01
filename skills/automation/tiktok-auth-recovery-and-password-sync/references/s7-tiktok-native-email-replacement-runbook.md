# S7 TikTok Native Email Replacement Automation Runbook

Tài liệu đúc kết từ phiên giải cứu thay thế toàn diện 41 tài khoản Gmail DIE sang Hotmail sạch có OAuth refresh token trên dàn Samsung Galaxy S7 Phone Farm.

---

### 1. KIẾN TRÚC ĐA LUỒNG & PHÒNG CHỐNG NGHẼN FARM (WATCHDOG 10 WORKERS)

- **Cấm làm thủ công từng máy rồi dừng lại báo cáo/than vãn:**
  Khi xử lý batch đổi email toàn farm, bắt buộc dùng Watchdog đa luồng (`watchdog_change_email.py` sử dụng `ThreadPoolExecutor(max_workers=10)`).
- **Cơ chế bọc an toàn `with_device_lock`:**
  Mọi thao tác can thiệp vào máy bắt buộc phải bọc qua `python D:/Taadaa/tools/with_device_lock.py --machine <N> -- ...`.
  Tuyệt đối không đụng vào máy đang chạy ca nuôi (đang giữ lock của `run_tiktok.py`). Chỉ khi máy kết thúc ca và nhả lock, watchdog mới được cấp quyền nhảy vào thi công.

---

### 2. BẪY UI VÀ THỜI GIAN CHỜ S7 NATIVE APP

1. **Độ trễ Splash Screen trên Samsung S7 (8 - 12 giây):**
   - Samsung Galaxy S7 cấu hình Exynos 8890 cũ tải app TikTok rất chậm. Khi `am start` MainActivity, app hiển thị màn hình đen có logo TikTok trong 8 - 12 giây.
   - **Pitfall:** Nếu tap tọa độ hoặc bóc OCR quá sớm, app chưa load xong sẽ văng vào màn hình feed hoặc tìm kiếm rác.
   - **Fix:** Phải có hàm `wait_app_ready(serial, m_id)` chờ tối thiểu 12s và kiểm tra OCR xuất hiện một trong các anchor (`hö sd`, `trang ch`, `live`, `bạn bè`) mới được tap tab Hồ sơ.

2. **Bẫy Modal 'Thêm vào Nhật ký' (Story Picker Popup):**
   - Sau khi khởi động hoặc chuyển tài khoản, TikTok thường tự bung modal `Thêm vào Nhật ký` / Album ảnh che khuất toàn bộ Menu 3 gạch ở góc trên phải.
   - **Fix:** Phải kiểm tra OCR text nếu thấy `nhật ký` / `gần đây` thì tap dấu `x` ở tọa độ `(84, 144)` để đóng modal trước khi điều hướng.

3. **Bẫy Popup Xác nhận 2 lớp 'Thay đổi email?':**
   - Khi bấm dòng "Thay đổi email", TikTok không mở form nhập mail ngay mà hiện thêm một dialog cảnh báo: *"Thay đổi email? Email mới cũng sẽ dùng cho xác minh 2 bước"* kèm 2 nút "Quay lại" và "Tiếp tục".
   - **Fix:** Bắt buộc chụp màn hình hậu kiểm (`cafter.png`), OCR tìm text `tiếp tục` / `tiép tvc` / `thay d6i email?` và tap vào nút `Tiếp tục` (tọa độ `(651, 1286)` hoặc bounds thực tế) để mở form nhập mail mới.

4. **Bẫy Bóc nhầm Dòng 'Khu vực quốc gia':**
   - Trên màn hình *Thông tin tài khoản*, dòng Email nằm ở khoảng `Y = 460 - 500`. Dưới đó có dòng Ngày sinh và Khu vực tài khoản.
   - **Fix:** Dùng WinRT OCR tìm đúng box có chữ `email` hoặc `@` có tọa độ `Y` nằm trong dải `[350, 600]`, tap trực tiếp vào tâm Y của box đó thay vì click mù tọa độ cố định.

5. **Bẫy Fuzzy OCR tên tài khoản trong Switcher (l vs I vs 1):**
   - WinRT OCR trên font chữ mảnh của TikTok thường nhận nhầm chữ `l` (thường) thành `I` (hoa) hoặc số `1` (ví dụ `l.thanh.ngn311` thành `I.thanh.ngn311`, `phungloan0138` thành `phungIoan0138`).
   - **Fix:** Bắt buộc chuẩn hóa tên trước khi so khớp:
     `def norm_name(s): return s.lower().replace('l', 'i').replace('1', 'i').replace('.', '').replace('_', '').strip()`

---

### 3. QUẢN TRỊ TOKEN HOTMAIL OAUTH & CHỐNG TRANH CHẤP CONCURRENCY

1. **Tranh chấp bốc trùng mail giữa các worker song song:**
   - Khi 10 workers chạy cùng lúc, nếu query `SELECT ... FROM mailboxes WHERE ta.email IS NULL` mà không khóa, nhiều worker sẽ cùng bốc 1 email làm fail hàng loạt.
   - **Fix:** Ngay khi bốc email, worker phải chạy ngay `UPDATE mailboxes SET oauth_status = 'HOLD_CHANGE' WHERE email = ?` để cách ly email đó.
   - Nếu worker fail hoặc timeout OTP, bắt buộc revert lại `oauth_status = 'READY'` (hoặc `NULL`) để giải phóng tài nguyên.

2. **Lọc triệt để Hotmail dính lỗi AADSTS70000 (invalid_grant):**
   - Kho Hotmail mua từ bên thứ 3 có thể có tài khoản bị đổi mật khẩu hoặc hết hạn refresh token.
   - **Triệu chứng:** Gọi Microsoft Graph API lấy access token ném ra lỗi `HTTP Error 400: Bad Request` với mô tả `invalid_grant / The grant is expired`.
   - **Fix:** Phải chạy script pre-flight xác thực token định kỳ hoặc bắt ngoại lệ `HTTPError 400`: lập tức đánh dấu `oauth_status = 'EXPIRED'` để loại bỏ khỏi pool cấp phát, không để worker bốc phải mail chết làm treo vòng lặp.

3. **Vượt qua màn hình 'Xác minh danh tính' (Identity Challenge):**
   - Một số tài khoản khi bấm đổi email bị TikTok bắt xác minh danh tính. Form thường cho 2 lựa chọn: (a) Gửi OTP về Gmail DIE cũ (Bế tắc), hoặc (b) Nhập Mật khẩu TikTok.
   - **Fix:** Bóc mật khẩu từ cột `Password` trong Excel Master (`master_gmail_manager.xlsx`), tap chọn radio button `Mật khẩu`, bấm `Tiếp`, điền mật khẩu tài khoản để mở khóa form đổi email. Nếu nick nào chỉ cho gửi OTP về Gmail DIE cũ, lập tức đánh dấu `BLOCKED_IDENTITY_GMAIL_DIE` và skip sang máy khác.

---

### 4. ĐỒNG BỘ DỮ LIỆU KÉP (DUAL-SINK SSOT)

Đổi email thành công trên app chỉ được coi là hoàn tất khi:
1. Có bằng chứng ảnh chụp thực tế màn hình *Thông tin tài khoản* hiển thị rõ email mới dạng `x***y@hotmail.com` qua WinRT OCR và Browser Vision (Gate 6).
2. SQLite `D:/Taadaa/data/farm_master.db`:
   - `UPDATE tiktok_accounts SET email = ? WHERE username = ?`
   - `UPDATE mailboxes SET oauth_status = 'ASSIGNED_TIKTOK' WHERE email = ?`
3. Master Excel Kibe `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx`:
   - Tìm đúng dòng `username`, ghi đè email mới vào cột Email.
