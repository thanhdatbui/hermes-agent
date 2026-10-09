# Phân Biệt Nick Lệch Display Name vs Mất Nick Thật & Quy Trình Khôi Phục Row 1 An Toàn

## 1. Bản chất sự cố nhận nhầm thiếu tài khoản (Case 142)
Trên các phiên bản TikTok mới (v46+), giao diện Switcher hiển thị **Tên hiển thị (Display Name tiếng Việt)** như `"Anh Hoang"`, `"Anh Pham"` thay vì `@username` (`@hong.bo.anh83`, `@ngc.anh.phm33`).
- **Nguyên nhân gốc rễ**: Các hàm so khớp cũ so sánh chuỗi trực tiếp hoặc chỉ bóc `@` mà không hỗ trợ ánh xạ Display Name, khiến bot tưởng nhầm tài khoản bị mất -> kích hoạt auto-login recovery đè -> gây kẹt OTP hoặc dính trần 8 tài khoản.
- **Quy tắc phân loại**:
  - Khi runner báo `account-switcher-missing-expected`, **BẮT BUỘC** kiểm tra xem nick đích có đang hiển thị dưới dạng Display Name trên Switcher không trước khi kết luận nick bị văng.
  - Phân tích XML Switcher đối chiếu chéo tên hiển thị với họ tên / prefix email trong Master DAT.

## 2. Bẫy tử thần khi "đá nick mới reg" để nạp lại Row 1
Khi một máy chạm trần 8 tài khoản và cần nạp lại nick Row 1 (nick cứng reg từ tháng 2-3/2026):
- **CẢNH BÁO TỐI CAO**: Tuyệt đối **KHÔNG ĐƯỢC ĐÁ NICK MỚI REG TRƯỚC RỒI TÍNH SAU**.
- Các nick mới reg (13-17/09) qua Hotmail/Outlook thường **chưa bật 2FA (`2FA=None`)**. Nếu logout khỏi máy cũ, môi trường fingerprint đổi đột ngột sẽ kích hoạt security checkpoint. Nếu mail Outlook bị block hoặc không đọc được OTP, nick sẽ **chết vĩnh viễn**.
- **Giải pháp chuẩn của Sol Planner**:
  1. Tận dụng các máy còn slot trống trong farm (thường có 30+ máy còn 1-2 slot).
  2. Không logout nick mới ngay trên máy cũ. Phải bật 2FA hoặc xác nhận login an toàn trên máy mới trước khi giải phóng slot cũ.
  3. Với các máy chưa chạm trần 8 nick (như M60 mới có 6 nick), **KHÔNG CẦN ĐÁ NICK NÀO**, bấm trực tiếp vào *"Thêm tài khoản"* để khôi phục.

## 3. Quy trình khôi phục tài khoản qua Fast Login / One-Tap
- Khi bấm *"Thêm tài khoản"*, TikTok thường lưu sẵn profile trong cache *"Chào mừng bạn trở lại"* (Fast Login).
- Tapping trực tiếp vào tài khoản mục tiêu sẽ đưa thẳng vào màn hình xác minh 2FA (OTP qua Hotmail hoặc 2FA TOTP), không cần nhập lại user/pass từ đầu, giảm thiểu 90% rủi ro checkpoint.
