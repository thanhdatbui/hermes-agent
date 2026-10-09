# QUY TẮC AN TOÀN KHI CỨU GMAIL BẰNG 5SIM & RANH GIỚI FARM S7 vs GPM PC

> **Bài học thực chiến (2026-09-21):**
> 1. Tránh đốt tiền oan khi thuê số ảo 5sim giải checkpoint Google.
> 2. Cấm tự tiện bốc tài khoản thuộc Farm Phone (Samsung S7) lên PC chạy GPMLogin.

---

## 1. RANH GIỚI FARM S7 vs GPM PC (BẢO VỆ TÀI SẢN FARM)

### Vấn đề cốt lõi:
- Mọi Gmail có cột `Số Máy Farm != None` (hoặc `Model != None` như Máy 01 -> Máy 80) là tài sản thuộc **Pipeline điện thoại Samsung S7**.
- Điện thoại đã có môi trường phần cứng, MAC, IP và fingerprint quen thuộc của Google.
- **HẬU QUẢ KHI TỰ BỐC LÊN PC**:
  - Đưa acc Farm lên trình duyệt GPMLogin trên PC khiến Google phát hiện ngay lập tức môi trường lạ (*Unusual activity / New device detected*).
  - Kể cả khi acc **ĐÃ CÓ 2FA TOTP (Google Authenticator)**, Google vẫn kích hoạt thêm bước bảo vệ tăng cường (**Step-up Verification**) bắt buộc phải nhập số điện thoại nhận mã SMS.
  - Vừa làm rủi ro DIE acc Farm, vừa tốn tiền thuê số vô ích.

### Quy tắc bất biến:
1. **CẤM TUYỆT ĐỐI** tự tiện lấy acc có `Số Máy Farm != None` làm mẫu thử nghiệm (test) trên GPM PC.
2. Khi User yêu cầu "lấy 1 gmail test/cứu":
   - **CHỈ ĐƯỢC CHỌN** các acc tự do (`Số Máy Farm == None`, acc chưa gán máy).
   - Nếu bắt buộc phải đụng vào acc có máy Farm: **BẮT BUỘC DỪNG LẠI HỎI USER** trước khi tạo profile GPM.

---

## 2. NGUYÊN TẮC ƯU TIÊN KÊNH 0Đ TRƯỚC TIÊN (FREE CHANNEL FIRST)

Trước khi tính đến chuyện gọi API mua số tốn tiền (5sim, OTP...):
1. **Kiểm tra Recovery Email (Email khôi phục)**:
   - Nhiều tài khoản có email khôi phục chính chủ (như `khoaleemagic@gmail.com`).
   - Màn hình checkpoint Google luôn có nút **"Thử cách khác (Try another way)"** -> Chọn **"Nhận mã xác minh tại email khôi phục"**.
   - Kênh này **hoàn toàn MIỄN PHÍ 0đ**, an toàn tuyệt đối.
2. **Kiểm tra 2FA TOTP (Google Authenticator)**:
   - Dùng `pyotp.TOTP(secret).now()` giải mã trước.
3. **CẤM mua 5sim** khi tài khoản vẫn còn kênh 0đ chưa thử nghiệm.

---

## 3. KỸ THUẬT & CƠ CHẾ THỰC TẾ KHI DÙNG 5SIM CHO GOOGLE

### A. Thời gian chờ OTP (Timeout):
- Google gửi SMS đến mạng ảo của 5sim có thể mất từ 10s đến 90s.
- Bắt buộc đặt vòng lặp thăm dò (polling) **ít nhất 150s - 240s (3 - 4 phút)**. Nếu để timeout quá ngắn (<60s) sẽ bị lỡ mã và mất đơn.

### B. Cơ chế trừ tiền của 5sim:
- **Nhận được OTP**: 5sim trừ tiền ngay lập tức (khoảng $0.175 - $0.19 cho Google VN). Không hoàn tiền được.
- **Hết thời gian không nhận được OTP**: Bắt buộc script phải gọi endpoint `/user/cancel/<order_id>` -> 5sim sẽ **hoàn tiền 100% về số dư**.

### C. Nguy cơ "Mất tiền oan" (Rate-limit sau OTP):
- Nếu một tài khoản vừa bị Google bắt challenge reCAPTCHA, session expired nhiều lần trong phiên:
  - Dù 5sim nhận OTP thành công và nhập vào, Google vẫn có thể chặn tiếp ở cửa cuối: *"Quá nhiều lần thử không thành công, hãy thử lại sau vài giờ nữa"*.
  - Lúc này 5sim **đã trừ tiền** nhưng tài khoản **vẫn không vào được**.
- **Giải pháp**: Nếu acc đã dính captcha/lỗi thử >2 lần trong ngày -> **NGÂM TĨNH COOLDOWN 24H-48H**, tuyệt đối cấm đè số 5sim vào đốt tiền tiếp.

### D. Số 5sim có bị gắn vào tài khoản không?
- **KHÔNG!** Khi Google yêu cầu *"Nhập số điện thoại để nhận mã xác minh"*, Google chỉ mượn số để giải checkpoint tức thời.
- Sau khi login thành công, kiểm tra `myaccount.google.com/phone` vẫn hiển thị *"Chưa có số điện thoại nào"*. User không cần phải tốn công tìm cách xóa số.
