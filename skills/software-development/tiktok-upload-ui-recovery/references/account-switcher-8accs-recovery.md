# Account Switcher Recovery (Galaxy S7 - 8 Accounts Farm)

## Triệu chứng
- Workflow dừng tại state `ACCOUNT_SWITCHER`:
  `[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found`.

## Nguyên nhân gốc rễ (Root Causes)
1. **Bottom Sheet Tràn Màn Hình (Viewport Overflow)**:
   - Trên Galaxy S7 (1080x1920), bottom sheet "Chuyển đổi tài khoản" chỉ hiển thị 4 account đầu tiên.
   - Các account thuộc slot Tik4..Tik8 (máy nạp 8 nicks) nằm ngoài viewport, XML dump ban đầu không có node text của target account.
   - Code cũ thiếu logic cuộn màn hình khi gặp `ACCOUNT_MISSING`.

2. **Bẫy Anchor Header Profile (Story / Prompt Traps)**:
   - Giao diện TikTok liên tục cập nhật các nút/badge trên profile header: "Số lượt xem hồ sơ", "Profile views", prompt "Tám chuyện nào", "Thì thầm to nhỏ".
   - Bộ nhận diện anchor trong `find_switcher_anchor` nếu không lọc kỹ các control markers này sẽ nhận nhầm làm anchor hoặc tap nhầm làm bung composer tạo Story/Nhật ký thay vì dropdown Switcher.
   - Khi composer Story bật lên, màn hình bị khóa bởi EditText/bàn phím khiến việc dump XML sau đó hoàn toàn không có danh sách switcher.

## Giải pháp & Kỹ thuật xử lý chuẩn
1. **Xử lý cuộn tự động trong `automation_core.tiktok.account_switcher`**:
   - Trong hàm `select_exact_account`: khi bắt ngoại lệ `ACCOUNT_MISSING`, kiểm tra method `adapter.swipe`.
   - Thực hiện lặp vuốt tối đa 3 lần:
     `start_x, start_y = width // 2, int(height * 0.80)`
     `end_x, end_y = width // 2, int(height * 0.50)`
     `duration_ms = 450`
   - Chờ settle `time.sleep(max(1.0, settle * 2))` để animation dừng hẳn rồi redump UI tìm lại.

2. **Chặn nhận nhầm anchor bằng `_PROFILE_HEADER_CONTROL_MARKERS`**:
   - Thêm vào blacklist các cụm từ:
     `"số lượt xem hồ sơ"`, `"profile views"`, `"lượt xem hồ sơ"`, `"tám chuyện nào"`, `"tám chuyện"`, `"thì thầm to nhỏ"`.

3. **Tọa độ Fallback mở Switcher trên Samsung S7 (1080x1920)**:
   - Tọa độ tâm vùng tên tài khoản trên màn hình Profile chuẩn: `(540, 552)`.
   - Tránh tap vào đỉnh header `(539, 140)` khi có prompt Story/Nhật ký xuất hiện.
