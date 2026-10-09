# FARM-ASSET-001: Bảo Vệ Tài Sản Nick TikTok Trên Thiết Bị & Cấm Tự Ý Logout (2026-09-25)

## 1. Bối cảnh & Bài học xương máu
- Trong quá trình dọn slot máy để reg bù Row 8, Agent đã vội vã kết luận nick `@annhubvqttr` trên Máy 3 là "nick lạ / nick rác" vì không tìm thấy trong sheet Excel `taikhoan_dat_v2_updated .xlsx`.
- Agent đã tự tiện thực hiện logout, làm mất phiên đăng nhập của tài khoản chính chủ của User.
- **Nguyên nhân gốc rễ dữ liệu:** Nick đã được reg thành công trước đó bằng Gmail `an.nhuan.work64541@gmail.com`, nhưng file Excel bị sót ghi nhận và email này sau đó bị script dọn dẹp quét nhầm khỏi kho nguồn `gmail_clean_v2.xlsx`.

## 2. Quy tắc Bất Biến FARM-ASSET-001 (Invariant)
1. **MỌI TÀI KHOẢN TIKTOK ĐANG ĐĂNG NHẬP TRÊN MÁY FARM LÀ TÀI SẢN DOANH NGHIỆP CỦA USER:**
   - Agent chỉ có quyền sử dụng tài sản để phục vụ nuôi/tương tác. Agent TUYỆT ĐỐI KHÔNG CÓ QUYỀN ĐỊNH ĐOẠT TÀI SẢN.
   - Cấm mọi hành vi tự gán nhãn "nick lạ", "nick rác", "nick test" để logout/xóa phiên.
2. **QUY ĐỊNH LOGOUT DUY NHẤT ĐƯỢC PHÉP:**
   - CHỈ ĐƯỢC PHÉP LOGOUT NICK KÝ SINH (Nick có chủ sở hữu chính thức ở máy khác: `owner_stt != current_stt`) đã được xác minh bằng OCR readback khớp chính xác.
   - Cơ chế này đã được User phê duyệt trước để dọn dẹp chống kẹt 8 acc.
3. **NICK TRÊN MÁY KHÔNG CÓ TRONG EXCEL:**
   - BẮT BUỘC coi là sự cố LỆCH DỮ LIỆU (Unrecorded Asset / Data Desync).
   - **CẤM TUYỆT ĐỐI LOGOUT.**
   - Bắt buộc thực hiện 4 bước:
     1. Đóng băng thiết bị (dừng mọi thao tác automation trên máy).
     2. Chụp ảnh màn hình Switcher + Profile, OCR lấy username và thông tin tài khoản.
     3. Truy vết ngược trong các bản backup Excel (`backup_clean_v2_*.xlsx`, `taikhoan_dat_v2.bak*`, log reg).
     4. BÁO CÁO USER & CHỜ CHỈ ĐẠO. Không có bất kỳ timeout nào cho phép tự ý xử lý.
4. **CẤM MỌI HÀNH VI TƯƠNG ĐƯƠNG LOGOUT:**
   - Cấm `pm clear com.ss.android.ugc.trill`.
   - Cấm gỡ cài đặt app TikTok.
   - Cấm xóa cache phiên hoặc "Remove account".
5. **TECHNICAL GUARD (`logout_guard.py`):**
   - Mọi thao tác logout bắt buộc phải gọi `logout_guard.evaluate_logout()` và `assert_logout_allowed()`.
   - Fail-closed: Mọi mã ngoại trừ `PARASITE` đều ném `LogoutForbidden` và ghi nhận incident JSONL.

## 3. Cạm bẫy Watchdog Child Process Lock Collision
- **Triệu chứng:** Watchdog/Cron chạy định kỳ nhưng kịch bản con (`tiktok_login_v1.py`) luôn thoát ngay lập tức với `exit=2` (`NEEDS_USER_DECISION: device lock active`).
- **Nguyên nhân gốc rễ:** Watchdog cha bọc `with acquire_device_lock(machine=M, ...):` rồi gọi `subprocess.run(["python", "tiktok_login_v1.py", str(M), ...])`. Bản thân `tiktok_login_v1.py` lại tự acquire device lock với PID của chính nó. Vì PID khác nhau, tiến trình con phát hiện lock đang bị giữ bởi PID cha và tự động hủy bỏ (fail-safe).
- **Giải pháp chuẩn:**
  - Watchdog chỉ kiểm tra máy rảnh (`is_machine_busy() == False`).
  - Khi máy rảnh, gọi trực tiếp kịch bản con và ĐỂ KỊCH BẢN CON TỰ QUẢN LÝ DEVICE LOCK của nó.
  - Sau khi kịch bản con hoàn tất nhả lock, watchdog mới vào kiểm tra và chụp ảnh nghiệm thu.
