# Xử lý Lỗi 8/8 Nick Ẩn Nút Thêm Tài Khoản (Add Account) & Cơ Chế Chống Trùng Mail

## 1. Triệu chứng & Bằng chứng hiện trường
- Khi chạy script reg bù (`ensure_row_accounts.py <row>` hoặc `_run_all_targets.py`):
  - Script văng lỗi tại Step 4:
    ```
    RuntimeError: [04_add_account] Không tìm thấy: ('Thêm tài khoản', 'Add account', 'Thêm tài khoản khác', 'Add another account', 'add_account')
    ```
  - Trong file UI dump `fail_04_add_account_*.xml`:
    - Menu chuyển đổi tài khoản (`com.ss.android.ugc.trill:id/pq2`) mở ra nhưng chỉ liệt kê đúng 8 nick đăng nhập.
    - Hoàn toàn KHÔNG có node nào mang text/content-desc "Thêm tài khoản" hay "Add account" (`com.ss.android.ugc.trill:id/lpw`).

## 2. Nguyên nhân cốt lõi (Anti-Pattern)
1. **Giới hạn 8 tài khoản của TikTok:**
   - Phiên bản ứng dụng TikTok (v46+) giới hạn tối đa đúng 8 tài khoản đăng nhập song song trên một thiết bị.
   - Khi đã đạt đủ 8 nick, TikTok **ẩn hoàn toàn nút "Thêm tài khoản"**.
2. **Nguyên nhân dính nick lạ (Log nhầm từ reg trùng mail cũ):**
   - Trước ngày 29/08/2026, kho `gmail_clean_v2.xlsx` từng bị trùng 1 email giữa 2 máy (ví dụ STT 19 và STT 40 cùng có `gabrundozarache@hotmail.com`).
   - Khi Máy 40 reg trước tạo nick, sau đó Máy 19 reg sau dùng cùng email đó, TikTok tự động chuyển hướng sang luồng Đăng nhập (OTP xác minh qua Graph API).
   - Script nhập OTP thành công dẫn tới việc **nick của Máy 40 bị đăng nhập ké vào Máy 19**, trong khi workbook tracking sau đó chỉ map nick cho Máy 40.
   - Hậu quả: Máy 19 bị đầy 8/8 nick ảo, khiến slot Row 6 (đang trống trên sheet) không thể reg thêm được.

## 3. Quy trình gỡ nick giải phóng slot (Safe Logout Protocol)
1. **Xác định nick lạ cần đăng xuất:**
   - Dump UI dropdown tài khoản trên máy, đối chiếu với 8 slot được phân bổ trong `taikhoan_run_safe.xlsx`.
   - Tìm ra nick đang nằm trên máy nhưng không thuộc STT của máy đó.
2. **Thao tác chuyển nick và đăng xuất an toàn:**
   - Tap vào nick lạ trên dropdown để switch active sang nick đó:
     `tap(device_id, x, y)`
   - Chờ app chuyển profile, mở Menu hồ sơ (góc phải trên: bounds `[954,96][1056,204]`).
   - Vào *Cài đặt và quyền riêng tư* (bounds `[204,1176][1038,1320]`).
   - Vuốt xuống cuối trang (2-3 lần swipe lên: `input swipe 540 1700 540 300 400`).
   - Bấm vào mục *Đăng xuất* (bounds `[24,1581][1056,1755]`).
   - Tại dialog xác nhận ("Bạn có chắc chắn muốn đăng xuất?"), tap nút *Đăng xuất* đỏ (bounds `[0,1584][1080,1740]`).
3. **Xác nhận nút "Thêm tài khoản" đã phục hồi:**
   - Kiểm tra lại dropdown tài khoản, xác nhận danh sách còn 7 nick và node *Thêm tài khoản* (`id/lpw`) đã xuất hiện trở lại ở cuối danh sách.

## 4. Cơ chế bảo vệ 3 lớp chống trùng mail & nick (Hiện hành)
1. **Lớp 1 (Global Clean Filter):** `gmail_clean_v2.xlsx` được audit liên tục để đảm bảo 100% email là duy nhất trên toàn farm (`Total duplicates: 0`).
2. **Lớp 2 (Cross-Check Tracking):** `get_available_mails_by_machine` bắt buộc nạp toàn bộ `used_emails` từ sheet `Tài Khoản` của workbook tracking để loại bỏ mọi email đã từng có nick trước khi cấp phát cho bất kỳ máy nào.
3. **Lớp 3 (In-Flight Duplicate Handle Guard):** Trong `social_reg_v1.py` (bước 10), nếu TikTok tạo xong profile mà handle trùng với tài khoản đã tồn tại trong tracking ở row khác, script sẽ lập tức phát hiện `BLOCKED_DUPLICATE_HANDLE_DETECTED` và fail-closed, tuyệt đối không ghi đè tracking.
