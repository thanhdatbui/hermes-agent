# FARM-ASSET-001: Bảo Vệ Tài Sản Nick TikTok Trên Thiết Bị & Cấm Tự Ý Logout (2026-09-25)

## 1. Bối cảnh & Sự cố nghiêm trọng
Trong ca vận hành Máy 3, một tài khoản TikTok (`@annhubvqttr`) đang lưu phiên trên máy nhưng không tìm thấy trong sheet Excel `taikhoan_dat_v2_updated .xlsx` (do lỗi ghi nhận trong quá khứ và việc xóa nhầm email khỏi kho `gmail_clean_v2.xlsx`).
Agent đã vội vã kết luận đây là "nick lạ / nick rác" và thực hiện logout để giải phóng slot thứ 8.
**Hậu quả:** Làm mất phiên đăng nhập của tài khoản chính chủ của User, vi phạm nghiêm trọng quy chuẩn bảo vệ tài sản Farm.

## 2. Quy tắc Bất Biến FARM-ASSET-001
1. **Mọi nick TikTok trên máy farm là TÀI SẢN DOANH NGHIỆP CỦA USER:**
   - Agent chỉ có quyền sử dụng tài sản phục vụ nuôi/tương tác, TUYỆT ĐỐI KHÔNG CÓ QUYỀN ĐỊNH ĐOẠT TÀI SẢN.
   - Nghiêm cấm mọi hành vi tự gán nhãn "nick lạ", "nick rác", "nick test" để logout/xóa phiên.
2. **Quy định logout duy nhất được phép & Cổng kiểm tra máy chính chủ (User chốt 2026-10-02):**
   - CHỈ ĐƯỢC PHÉP LOGOUT NICK KÝ SINH (Nick có chủ sở hữu chính thức ở máy khác: `owner_stt != current_stt`) đã được xác minh bằng OCR readback khớp chính xác.
   - **BẮT BUỘC KIỂM TRA MÁY CHÍNH CHỦ TRƯỚC KHI LOGOUT:** Trước khi thực hiện logout trên máy hiện tại, BẮT BUỘC kiểm tra thực tế trên máy chính chủ (`owner_stt`) xem tài khoản đó ĐÃ CÓ MẶT VÀ ĐANG ĐĂNG NHẬP TRÊN MÁY CHÍNH CHỦ CHƯA (chụp ảnh Switcher/Profile máy chính chủ làm bằng chứng `MEDIA:<path>`). Chỉ khi máy chính chủ ĐÃ CÓ nick đó thì mới được logout trên máy ký sinh; nếu máy chính chủ CHƯA CÓ, tuyệt đối không được logout vì sẽ làm mất phiên duy nhất của nick!
   - Cơ chế này đã được User phê duyệt trước để dọn dẹp chống kẹt 8 acc.
3. **Nick trên máy KHÔNG CÓ TRONG EXCEL:**
   - BẮT BUỘC coi là sự cố LỆCH DỮ LIỆU (Unrecorded Asset / Data Desync).
   - **CẤM TUYỆT ĐỐI LOGOUT.**
   - Bắt buộc thực hiện 4 bước:
     1. Đóng băng thiết bị (dừng mọi thao tác automation trên máy).
     2. Chụp ảnh màn hình Switcher + Profile, OCR lấy username và thông tin tài khoản.
     3. Truy vết ngược trong các bản backup Excel (`backup_clean_v2_*.xlsx`, `taikhoan_dat_v2.bak*`, log reg).
     4. BÁO CÁO USER & CHỜ CHỈ ĐẠO. Không có bất kỳ timeout nào cho phép tự ý xử lý.
4. **Cấm mọi hành vi tương đương logout:**
   - Cấm `pm clear com.ss.android.ugc.trill`.
   - Cấm gỡ cài đặt app TikTok.
   - Cấm xóa cache phiên hoặc "Remove account".
5. **Technical Guard (`logout_guard.py`):**
   - Mọi thao tác logout bắt buộc phải gọi `logout_guard.evaluate_logout()` và `assert_logout_allowed()`.
   - Fail-closed: Mọi mã ngoại trừ `PARASITE` đều ném `LogoutForbidden` và ghi nhận incident JSONL.

## 3. Cạm bẫy Watchdog Child Process Lock Collision
- **Triệu chứng:** Watchdog/Cron chạy định kỳ nhưng kịch bản con (`tiktok_login_v1.py`) luôn thoát ngay lập tức với `exit=2` (`NEEDS_USER_DECISION: device lock active`).
- **Nguyên nhân gốc rễ:** Watchdog cha bọc `with acquire_device_lock(machine=M, ...):` rồi gọi `subprocess.run(["python", "tiktok_login_v1.py", str(M), ...])`. Bản thân `tiktok_login_v1.py` lại tự acquire device lock với PID của chính nó. Vì PID khác nhau, tiến trình con phát hiện lock đang bị giữ bởi PID cha và tự động hủy bỏ (fail-safe).
- **Giải pháp chuẩn:**
  - Watchdog chỉ kiểm tra máy rảnh (`is_machine_busy() == False`).
  - Khi máy rảnh, gọi trực tiếp kịch bản con và ĐỂ KỊCH BẢN CON TỰ QUẢN LÝ DEVICE LOCK của nó.
  - Sau khi kịch bản con hoàn tất nhả lock, watchdog mới vào kiểm tra và chụp ảnh nghiệm thu.

## 4. Cạm bẫy Parser `find_column_indices` trong `logout_guard.py` (2026-10-02)
- **Hiện tượng:** Nick ký sinh rõ ràng thuộc máy khác trong Excel nhưng `evaluate_logout` trả về `code='UNRECORDED'` và chặn logout.
- **Nguyên nhân gốc rễ:** Cột header "Folder Video" chứa chữ "id" trong "v[id]eo". Logic `any(k in h for k in ("tiktok", "tik tok", "username", "id"))` match nhầm "Folder Video" làm `col_id` (chứa số folder như 167) thay vì cột "ID", khiến guard không tìm thấy username và ném lỗi UNRECORDED ảo.
- **Giải pháp chuẩn:** Bắt buộc kiểm tra `(h == "id" or any(k in h for k in ("tiktok", "tik tok", "username"))) and "video" not in h and "device" not in h`.
