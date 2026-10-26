# Bóc Tách Trạng Thái Văng Session (NEEDS_LOGIN) Khỏi Hàng Đợi Ngâm 2FA Gmail

## 1. Điểm Mù Khi Thống Kê Profile Bật 2FA
- Hàm phân loại profile `classify_profiles()` trước đây gom chung tất cả profile chưa bật 2FA và chưa đạt điều kiện nuôi thành công vào nhóm `soaking` ("Đang ngâm chờ phiên nuôi").
- Hậu quả: Các tài khoản bị **văng cookie Google (`status == 'NEEDS_LOGIN'`)** hoặc dính checkpoint cũng bị đếm vào `soaking`, tạo ra số liệu ảo khiến người vận hành tin rằng tài khoản đang tích lũy trust bình thường, trong khi thực tế tài khoản đã bị ngừng nuôi hoàn toàn.

## 2. Giải Pháp Chuẩn Hóa
1. **Hàm bóc tách chuyên biệt `get_needs_login_profiles(names, nurture_cache)`:**
   - Duyệt qua danh sách profile, kiểm tra trạng thái trong file cache nuôi dưỡng (`gpm_gmail_nurture_state.json`).
   - Lọc ra các email có `info.get('status') == 'NEEDS_LOGIN'` thành danh sách riêng biệt.
2. **Cập nhật nội dung báo cáo Telegram:**
   - Hiển thị danh mục cảnh báo riêng:
     ```text
     ⚠️ Acc văng cookie (NEEDS_LOGIN): X profile
       - email1@gmail.com
       - email2@gmail.com
     ```
   - Nhóm "Đang ngâm" chỉ còn chứa các profile có phiên session hợp lệ đang chờ đến phiên nuôi tiếp theo.
3. **Cập nhật Telemetry:**
   - Thêm trường `needs_login=len(needs_login)` vào payload `emit_metric()` để các hệ thống giám sát và alert tự động bắt được sự cố văng session.
