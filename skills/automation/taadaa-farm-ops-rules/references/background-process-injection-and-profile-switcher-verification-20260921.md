# Kỷ Luật Xử Lý Thông Báo Tiến Trình Nền & Kiểm Tra Account Switcher TikTok 47.x (2026-09-21)

## 1. Kỷ Luật Xử Lý Thông Báo Tiến Trình Nền (Background Process Injections)

### 1.1. Bản chất sự cố
- Khi một tiến trình nền chạy lâu (ví dụ cron login, batch script, watchdog) hoàn tất, runtime Hermes tự động đẩy thông báo vào chat:
  `[IMPORTANT: Background process proc_... completed normally (exit code 0). Command: ... Output: ...]`
- Khi User gửi phản hồi ngắn như `?` ngay sau thông báo này:
  - **Ý nghĩa thực tế của User**: *"Cái thông báo này là gì thế? Có liên quan đến việc đang làm không?"*
  - **Sai lầm chết người của Agent**: Hiểu nhầm User đang yêu cầu xử lý lỗi trong output của tiến trình đó, lập tức nhảy sang mổ xẻ script login, làm loãng và trật bánh (derail) toàn bộ công việc chính đang triển khai.

### 1.2. Quy tắc phản hồi chuẩn
1. **Xác định nguồn gốc**: Kiểm tra `session_id` hoặc command xem có thuộc scope công việc hiện tại không.
2. **Phản hồi minh bạch, dứt khoát**:
   - Giải thích ngay: *"Đây là thông báo tiến trình nền cũ [tên script/tác vụ] vừa chạy xong trong background, hệ thống tự động đẩy kết quả vào chat. Tác vụ chính của phiên hiện tại không bị ảnh hưởng."*
   - CẤM tự ý nhảy sang fix bug hay login tài khoản của tiến trình nền đó trừ khi User phát lệnh rõ ràng.

---

## 2. Quy Chuẩn Kiểm Tra Account Switcher TikTok 47.x (Chống Báo Động Giả / False Panic)

### 2.1. Cạm bẫy giao diện TikTok 47.0.3
- **Sai lầm thường gặp**: Agent điều hướng vào `Menu hồ sơ (954, 96) -> Cài đặt và quyền riêng tư -> Cuộn xuống đáy -> Chuyển đổi tài khoản`.
- **Hậu quả**: Trên bản 47.0.3, giao diện này có thể bị co gọn (collapsed) hoặc chỉ render 2 tài khoản đầu tiên nếu chưa cuộn hết. Agent vội vàng kết luận: *"Máy bị mất nick, chỉ còn 2 nick!"*, trong khi thực tế 7-8 nick vẫn nguyên vẹn trong SQLite/SharedPreferences của app.

### 2.2. Thao tác chuẩn xác 100% để bung trọn vẹn Switcher
- **Bước 1**: Mở app TikTok vào tab Hồ sơ: `input tap 972 1857`.
- **Bước 2**: Tap thẳng vào Header/Display name của nick active ở giữa màn hình: tọa độ `(500, 290)` (hoặc vùng `Y = 250..300`).
- **Bước 3**: Bottom Sheet chuẩn sẽ bung lên từ đáy màn hình:
  - Container: `rid='g1z'` (Trang tính dưới cùng).
  - Title: `rid='psy'` (`text='Chuyển đổi tài khoản'`).
  - Danh sách tài khoản: mỗi row có `rid='ls_'` và tên hiển thị `rid='ndk'`.
  - Nút thêm nick: `text='Thêm tài khoản'`.
- **Bất biến**: CHỈ kết luận số lượng nick thực tế sau khi đã dump UI XML từ đúng Bottom Sheet `rid='psy'` mở từ Profile Header.

---

## 3. Triage Độc Lập: Lỗi Đọc OTP Gmail Khác Hoàn Toàn Với "Văng Nick"

### 3.1. Phân định ranh giới kỹ thuật
- **Lỗi đọc OTP**: Khi login nick TikTok liên kết Gmail, script `tiktok_login_v1.py` mở app Gmail trên thiết bị để tìm hòm thư đọc mã OTP 6 số.
  - Nếu app Gmail trên máy chưa đăng nhập email đích, script fallback sang `checkmail.live`.
  - `checkmail.live` CHỈ kiểm tra email còn tồn tại hay không (LIVE/DIE), KHÔNG ĐỌC ĐƯỢC NỘI DUNG THƯ / MÃ OTP.
  - Hậu quả: Script dừng với thông báo `[7c] Không lấy được OTP từ ...@gmail.com`.
- **Trạng thái session TikTok**: Việc script login nick mới bị dừng ở bước đọc OTP hoàn toàn ĐỘC LẬP với các tài khoản TikTok đã đăng nhập sẵn trong máy.
- **Kỷ luật báo cáo**: Tuyệt đối không quy chụp lỗi thiếu hòm thư đọc OTP thành "TikTok văng account" hay "update app làm mất nick". Luôn đối soát thực tế trên Switcher trước khi đưa ra nhận định.
