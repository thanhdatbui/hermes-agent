# TikTok Reg: Cascading Submit dẫn đến "Please try again or log in with a different method"

## Hiện tượng & Triệu chứng
- Trên màn hình nhập email của TikTok: Ô nhập email bị viền đỏ, phía dưới xuất hiện icon tam giác cảnh báo đỏ (`Lỗi`) và dòng chữ:
  > `⚠️ Please try again or log in with a different method.` (resource-id `com.ss.android.ugc.trill:id/i14`)
- Người dùng đặt câu hỏi điều tra: Lỗi này bấm 1 lần bị hay bấm nhiều lần không được mới bị đỏ?

## Bằng chứng cơ chế gây lỗi (Root Cause: Cascading Submit Spam)
Lỗi này **KHÔNG PHẢI BẤM 1 LẦN BỊ**, mà do script tự động bấm lặp nhiều lần dồn dập (3 lần liên tiếp trong ~2 phút) khi gặp mạng lag:

1. **Lần bấm 1 (Bước [7] `fill_email_and_next`):**
   - Script nhập email và bấm `Tiếp tục` (tọa độ `(540, 1806)`).
   - Do mạng/proxy bị nghẽn (status bar Wi-Fi ghi nhận: `desc="Tín hiệu Wi-Fi đủ.,Không có Internet."`), TikTok không phản hồi kịp và không chuyển màn hình.
   - `detect_after_continue` timeout. Nhánh `unknown fallback` do lỏng matcher nên phán đoán nhầm là "registered" (đã có tài khoản) và cho chạy tiếp thay vì dừng/báo lỗi.

2. **Lần bấm 2 (Bước [7c] Confirm email check):**
   - Main flow chạy đến bước 7c, kiểm tra thấy màn hình vẫn còn `Nhập địa chỉ email` và `Tiếp tục`.
   - Script tưởng nhầm là màn "Confirm email lần 2 trước khi nhận OTP", tiến hành gõ lại full email và **bấm `Tiếp tục` lần thứ 2** (tọa độ `(540, 1681)`).

3. **Lần bấm 3 (Bước [8b-0] `handle_post_auth_screens`):**
   - Bước [8] (password) không thấy màn password nên bỏ qua.
   - Bước [8b] (`handle_post_auth_screens`) ở round 0 quét XML thấy màn hình vẫn còn `Nhập địa chỉ email` và `Tiếp tục`.
   - Match nhánh email confirm trong post-auth, tiếp tục gõ lại email và **bấm `Tiếp tục` lần thứ 3** (tọa độ `(495, 594)` / `(540, 1681)`).

4. **Kích hoạt Rate-limit / Anti-spam của TikTok:**
   - So sánh 2 file UI XML:
     - `debug_34_postauth_1_*.xml` (sau 3 lần bấm): Form vẫn sạch, **chưa hề có lỗi đỏ**.
     - `timeout_34_login_success_*.xml` (trong lúc bước [9] đếm chờ 30s): TikTok xử lý chuỗi request dồn dập trên cùng 1 IP/thiết bị, đánh dấu spam và trả về thông báo lỗi đỏ `Please try again or log in with a different method.`.

## Kỹ thuật điều tra O(1) trên Farm (Log 200MB+)
- File `social_reg_log.txt` thường rất lớn (200MB - 1GB). CẤM dùng `grep` trực tiếp trong bash MSYS vì pipe buffer dễ bị deadlock/timeout.
- Trích xuất nhanh O(1) qua Python một dòng bằng cách seek từ cuối file (`f.seek(max(0, size - 15MB))`) rồi quét ngược các mốc timestamp/máy cần tra.
- Đối chiếu các file XML dump tuần tự (`debug_*_postauth`, `timeout_*_login_success`) để xác định chính xác thời điểm node lỗi (`com.ss.android.ugc.trill:id/i14`) xuất hiện.

## Nguyên tắc phòng ngừa trong Codebase (`social_reg_v1.py`)
- **Khóa van Cascading Submit:**
  - Ở bước [7], nếu `detect_after_continue` trả về `form_still_visible` hoặc màn hình không thay đổi, TUYỆT ĐỐI KHÔNG coi là "registered" trong unknown fallback.
  - Các bước sau ([7c], [8b]) khi thấy màn `Nhập địa chỉ email`: PHẢI kiểm tra cờ trạng thái xem email đó vừa được submit ở bước trước hay chưa. Nếu màn hình chưa bao giờ chuyển trạng thái kể từ lần submit trước, coi là kẹt màn/lag mạng và fail-closed, KHÔNG được bấm `Tiếp tục` lần 2, lần 3.
