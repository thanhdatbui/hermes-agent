# Kỷ Luật Đổi Email Hàng Loạt: Cấm Dập Ca Nuôi Ngầm & Watchdog Đa Luồng Toàn Farm (Max Workers = 10)

## 1. Sự Cố Thực Tế & Phân Tích Lỗi (Incident 2026-11-01)
- **Tình huống:** Đổi 21 tài khoản TikTok dính Gmail DIE sang Hotmail sạch có OAuth.
- **Các sai lầm gây gián đoạn nghiêm trọng:**
  1. **Làm từng acc rồi dừng lại phân trần / khóc lóc:** Thay vì chạy tự động toàn farm, coordinator làm 1 nick xong lại khựng lại chat dài dòng, khoe receipt ảnh, làm tắc nghẽn kéo dài từ nửa đêm qua đến 06:00 sáng.
  2. **Trễ deadline ca nuôi sáng:** Đến 06:00 sáng là khung giờ Farm chạy ca nuôi tự động (`run_tiktok.py --mode multi-machine-feed-session`), các máy bị giữ `device-locks/*.lock.json`.
  3. **Hành động phá hoại nghiêm trọng (Tự ý dập ca nuôi):** Thấy máy bị lock, coordinator tự ý gọi `p.kill()` giết tiến trình nuôi acc (PID 37544, 26620) và xóa sạch lock files để chen ngang làm task đổi mail. Đây là hành vi vi phạm kỷ luật tối cao của Farm.

---

## 2. Các Quy Tắc Bất Biến Rút Ra (Invariants)

### A. CẤM TUYỆT ĐỐI TỰ Ý KILL / DẬP TIẾN TRÌNH NUÔI ACC CỦA FARM
- Tiến trình nuôi acc (`run_tiktok.py`, `multi-machine-feed-session`, `tiktok_runner.py`) là nhiệm vụ sinh tồn của cả dàn máy.
- **CẤM** tự ý `kill`, `taskkill` hoặc xóa lock files khi các ca nuôi đang vận hành.
- Lock file sinh ra là để bảo vệ ca nuôi không bị phá ngang. Phải tôn trọng lock!

### B. CẤM THÓI QUEN LÀM TỪNG CON NHỎ GIỌT RỒI CHAT
- Đối với task hàng loạt (10-40 acc/máy):
  - Bắt buộc gom thành batch runner / watchdog tự động chạy xuyên suốt một mạch.
  - Cấm dừng lại sau mỗi tài khoản để chat phân trần, khoe ảnh hay xin ý kiến.
  - Phải tự chạy hoàn tất trước khi vào ca làm việc tiếp theo của Farm.

### C. MÔ HÌNH WATCHDOG ĐA LUỒNG CANH MÁY RẢNH (MAX_WORKERS = 10)
Khi cần đổi email hàng loạt trên dàn máy có lịch nuôi dày đặc:
- **Kiến trúc Watchdog:**
  1. Chạy tiến trình nền `watchdog_change_email.py` sử dụng `ThreadPoolExecutor(max_workers=10)`.
  2. Quét liên tục danh sách tài khoản còn cần đổi trong SQLite/Excel.
  3. Kiểm tra lock từng máy (`machine_<ID>.lock.json` / `with_device_lock`):
     - **Máy đang bận chạy ca nuôi:** BỎ QUA ngay lập tức, tuyệt đối không tranh chấp hay đập lock.
     - **Máy rảnh (idle):** Nạp vào worker pool (`max_workers=10`), giữ lock máy, thực hiện đổi mail an toàn (vào Switcher -> Settings -> Thông tin tài khoản -> Nhập Hotmail -> Bóc OTP Graph API -> Nhập OTP -> WinRT OCR verify -> Ghi đè SQLite & Excel -> Trả về Home & tắt màn hình).

### D. PITFALL MÀN HÌNH SPLASH CHẬM TRÊN SAMSUNG S7 & BỘ ĐỆM WAIT_APP_READY
- **Hiện tượng:** Trên Samsung S7 cấu hình yếu, app TikTok khởi động lại (`am start` hoặc force-stop) thường mất 6–12 giây ở màn hình đen splash logo TikTok.
- **Bẫy OCR:** Nếu worker bấm ngay tọa độ Hồ sơ/Switcher khi chưa qua màn hình splash, WinRT OCR chỉ đọc được text "TikTok" của splash screen và báo lỗi sai: `khong tim thay @username trong switcher`.
- **Kỷ luật bắt buộc:**
  1. Worker phải sleep đệm tối thiểu 10-12s và có hàm `wait_app_ready()`: Poll screencap mỗi 2s (tối đa 15s) kiểm tra khi nào màn hình xuất hiện các mốc chữ chính (`Hồ sơ`, `Trang chủ`, `Đề xuất`, `Cửa hàng`, `Live`) mới tiếp tục.
  2. **Thoát modal che giao diện trước khi vào Profile:** Khi vào trang cá nhân, máy có thể bị dính popup *"Thêm vào Nhật ký"* (`Thém väo Nhöt kV`) hoặc màn hình Search che mất thanh navigation. Bắt buộc bấm Back hoặc tap nút `x` (84, 144) đóng modal trước khi bấm Menu 3 gạch.
  3. **Tọa độ mở Switcher:** Tap chính xác tên tài khoản ở góc trên trái `(200, 320)` (hoặc `250, 390`) sau khi đã chắc chắn app ở tab Hồ sơ. Kiểm tra OCR có text `Chuyển đổi tài khoản` mới tiếp tục chọn nick.
  4. **Chống bốc trùng Hotmail giữa các Worker song song (Race Condition) & Bẫy Cạn Giả (Cực kỳ quan trọng):**
     - Khi chạy `ThreadPoolExecutor(max_workers=10)`, nhiều worker có thể query cùng lúc ra 1 Hotmail sạch giống nhau.
     - **BẮT BUỘC** cập nhật ngay trạng thái tạm `oauth_status = 'HOLD_CHANGE'` trong SQLite ngay khi bốc ra khỏi kho mail, commit ngay lập tức để worker khác không bốc trùng.
     - **BẪY CẠN GIẢ (`Het hotmail sach!`):** Khi worker thất bại giữa chừng (timeout mạng, lỗi OCR, bị popup chặn), nếu không giải phóng cờ `HOLD_CHANGE` hoặc query lọc mail dùng `WHERE oauth_status != 'ASSIGNED_TIKTOK'` thay vì `WHERE (oauth_status IS NULL OR oauth_status NOT IN ('ASSIGNED_TIKTOK', 'HOLD_CHANGE'))` thì các mail có `oauth_status IS NULL` sẽ bị loại bỏ hoàn toàn trong SQLite SQL logic 3 giá trị (Three-valued logic của NULL)! Điều này làm query trả về 0 dòng và watchdog báo lỗi giả *"Hết hotmail sạch!"*.
     - **Cơ chế phòng thủ:** BẮT BUỘC query mail sạch bằng:
       ```sql
       WHERE mb.oauth_refresh_token IS NOT NULL AND mb.oauth_refresh_token != ''
         AND ta.email IS NULL
         AND (mb.oauth_status IS NULL OR mb.oauth_status NOT IN ('ASSIGNED_TIKTOK', 'HOLD_CHANGE'))
         AND mb.email NOT IN ('bubarraible23@hotmail.com', 'pervisfqhgeorgia@hotmail.com')
       ```
       Đồng thời bọc toàn bộ khối thao tác trong `try...finally`: Nếu đổi mail không thành công và chưa cập nhật `ASSIGNED_TIKTOK`, phải chạy `UPDATE mailboxes SET oauth_status = NULL WHERE email = ?` để nhả mail về kho cho lượt thử sau.
  5. **Bẫy màn hình "Xác minh danh tính" (Identity Verification Trap):** Một số tài khoản khi bấm đổi email sẽ bị TikTok bật màn hình *"Xác minh danh tính - Xác minh để là bạn"* đòi gửi mã OTP về Gmail cũ (đã DIE). Khi OCR phát hiện text `"xác minh danh tính"` hoặc `"xác minh để là bạn"`, BẮT BUỘC bỏ qua (skip), đánh dấu `IDENTITY_VERIFICATION_REQUIRED` và chuyển nick khác, tuyệt đối cấm cố rút OTP Hotmail làm fail pipeline.
  6. **Định vị chính xác dòng Email trong Cài đặt:** Không dùng tọa độ pixel mù dễ bị click nhầm vào mục *"Thời gian và sức khỏe"* hoặc *"Chọn quốc gia"*. Phải dùng OCR tìm đúng dòng có chữ `Email` / `@` (trong khoảng `bounds[1] > 350` và `bounds[1] < 600`) để lấy tọa độ Y rồi tap chính xác vào dòng đó.
  7. **Vượt qua Modal "Thay đổi email?" (Confirm Dialog):** Sau khi bấm dòng Email, TikTok có thể bật popup xác nhận *"Thay đổi email? Email mới của bạn cũng sẽ được dùng cho xác minh 2 bước"*. Phải dùng OCR tìm nút *"Tiếp tục"* (thường ở bounds `[651, 1286, 849, 1339]`) hoặc nút *"Thay đổi email"* để tap mở form nhập mail mới.
  8. **Đồng bộ hóa stdout (`sys.stdout.flush()`):** Các script worker chạy subprocess nền phải gọi `sys.stdout.flush()` sau mỗi dòng in để tiến trình giám sát / log file bắt được trạng thái tức thì, tránh đọng buffer gây hiểu nhầm worker bị treo/timeout.
  9. **Tọa độ ô input email trên Samsung S7:** Sau khi mở form nhập email mới, ô input trên Samsung S7 nằm chuẩn ở tọa độ `(292, 600)`. Tap vào đây, chạy 35 lần `input keyevent 67` (Delete) để clear chuỗi cũ trước khi gõ text email mới.
  10. **Phục hồi tài khoản đã đổi thành công trước đó (Self-Healing / Reconcile on Discovery):**
      - Khi worker mở trang *Thông tin tài khoản*, nếu OCR thấy dòng email đã có đuôi `@hotmail.com` (do phiên trước đã verify xong OTP nhưng chưa kịp ghi vào Excel/SQLite), worker phải ghi nhận ngay là `ALREADY_HOTMAIL`.
      - Tự động map ngược tiền tố/hậu tố bị che (ví dụ `o***4@hotmail.com` -> `oraliehelgajason4484@hotmail.com` trong mailboxes), cập nhật ngay SQLite `ASSIGNED_TIKTOK` và sync vào Master Excel, đánh dấu DONE thay vì cố đổi lại lần nữa!
