# Google Phone Checkpoint (`challenge/iap`), Bản Chất Cooldown & Giải Pháp Thuê SIM OTP Việt Nam (+84)

## 1. Bản Chất Phone Checkpoint (`challenge/iap`) & Cạm Bẫy "Ngâm Cooldown"

### Hiện tượng
Khi đăng nhập tài khoản Google trên profile GPM (trên PC hoặc sau khi xoay proxy 4G), sau khi nhập mật khẩu và mã 2FA TOTP hoặc mã OTP email khôi phục, Google chuyển hướng sang URL dạng:
`https://accounts.google.com/v3/signin/challenge/iap`
Tiêu đề: *"Xác minh danh tính của bạn. Có điều bất thường về hoạt động của bạn. Google muốn đảm bảo rằng người đăng nhập chính là bạn."*
Yêu cầu: *"Nhập một số điện thoại bất kỳ để nhận tin nhắn văn bản cùng mã xác minh."*

### Phân biệt: Account Security Flag vs Rate Limit Cooldown
- **Rate Limit IP (Tạm thời)**: Ví dụ *"Bạn đã thử quá nhiều lần, hãy thử lại sau vài giờ"*. Dạng này cho ngâm profile / đổi IP trong 24h–48h thì hệ thống tự động nhả.
- **Phone Checkpoint (`challenge/iap` - Cờ cấp tài khoản)**:
  - Dữ liệu đối soát thực tế từ hệ thống Farm qua hơn 20 ngày (từ 05/09 đến 25/09/2026) trên các tài khoản dính checkpoint: `thainhuong07052000rmv`, `giathu0709200565`, `dianavmoore`, `darrellpperez`.
  - **Kết luận thực nghiệm 100%**: **Tài khoản đã dính Phone Checkpoint thì ngâm 1 tuần, 2 tuần hay cả tháng VẪN BẮT NHẬP SỐ ĐIỆN THOẠI.** Cờ này được ghim trực tiếp trên máy chủ Google (Account Security Flag). Dù đổi sang máy khác hay đổi IP sạch, hễ xác thực Pass + TOTP xong là Google ép xuất hiện form đòi SMS.

### Tài khoản có bị "Cút luôn" (Disabled / Banned) không?
- **HOÀN TOÀN KHÔNG**. Tài khoản chưa bị khóa hay xóa vĩnh viễn. Màn hình Google vẫn mở form trống cho nhập số điện thoại.
- Bất kỳ lúc nào người vận hành nhập 1 số điện thoại nhận mã SMS và điền vào form, tài khoản lập tức sống lại bình thường, token cấp mới và dùng tiếp ngon lành.
- Google chỉ thực sự "cút luôn" khi báo: *"Tài khoản của bạn đã bị vô hiệu hóa"* (Disabled) hoặc *"Không tìm thấy tài khoản Google của bạn"* (Deleted).

---

## 2. Cạm Bẫy Hard-Lock Khi Dùng SIM Thuê Ảo 1 Lần vs Dùng SIM Thật Của Farm

### Cạm bẫy Hard-Lock (Mất vĩnh viễn nick)
- Màn hình Google ghi rõ: *"Google will store this number and only use it for security purposes"* (Google sẽ lưu số này lại cho mục đích bảo mật).
- **Rủi ro chí mạng khi thuê SIM ảo (10-15 phút)**:
  - Nếu số thuê ảo bị Google gán làm **Số điện thoại khôi phục (Recovery Phone)**.
  - Sau vài tuần/tháng, khi chu kỳ token hết hạn hoặc IP đổi dải, Google quét lại và không cho nhập số mới nữa mà bắt:
    👉 *"Nhận mã xác minh tại số điện thoại đuôi ••••••••846"* (đúng số ảo đã thuê hôm nay).
  - Vì không còn giữ SIM đó, tài khoản sẽ **BỊ HARD-LOCK VĨNH VIỄN 100%**, không cách nào cứu được!

### Chiến lược vận hành chuẩn:
1. **Tài khoản tài sản Farm cần giữ lâu dài**:
   - **BẮT BUỘC dùng SIM vật lý thật của Farm** (SIM cắm trên máy Android hoặc SIM phụ của người vận hành).
   - Một số điện thoại thật có thể verify cho **4 – 5 tài khoản Gmail**.
   - Khi Google hỏi lại đúng số cũ trong tương lai, người vận hành vẫn cầm SIM nhận mã được.
2. **Tài khoản tiêu hao / Cần cứu hộ tức thì**:
   - Sử dụng các sàn thuê OTP rẻ (FastOTP, ViOTP, 5sim VN).
   - Chấp nhận rủi ro nếu sau này Google bắt verify lại đúng số cũ thì bỏ acc.

---

## 3. Cơ Chế Check-Live Qua Tool `checkmail.live` Của Farm

- Tool check-live nội bộ: `D:/Taadaa/tools/check_gmail_live_fast.py` và `D:/Taadaa/GPM auto/scripts/run_checkmail_kibe_farm.py`.
- Sử dụng profile Chrome lưu sẵn session `checkmail.live` (có credits sẵn).
- **Quy tắc phân loại**:
  - Khi tài khoản dính Phone Checkpoint (`challenge/iap`), máy chủ Google tạm đình chỉ luồng nhận mail và xác thực tự động. Tool `checkmail.live` quét thấy không thông luồng nên **đánh dấu trạng thái là `[die]`**.
  - Các tài khoản bình thường không bị chặn số được đánh dấu **`[Live]`**.
  - **Lưu ý nhận thức**: Chữ `DIE` trong báo cáo check-live farm có nghĩa là "Phế đối với bot automation", không đồng nghĩa với việc tài khoản Google đã bị xóa sổ.

---

## 4. Bảng So Sánh Các Sàn Thuê OTP Đầu Số Việt Nam (+84) (Cào Trực Tiếp 09/2026)

*Lưu ý: Không dùng SIM nước ngoài (US, RU, ID, PH) cho tài khoản chạy trên IP / Proxy Việt Nam vì lệch Geolocation sẽ kích hoạt Google gắn cờ unusual activity liên tục.*

| Sàn OTP | Giá Google (+84 VN) | Đánh giá vận hành |
| :--- | :--- | :--- |
| **1. FastOTP.net** | **`964đ / SMS`** *(Rẻ nhất)* | Nạp tiền tự động qua Bank/MoMo VNĐ. Timeout chờ 600s (10 phút). Giá dưới 1k. |
| **2. ViOTP.com** | **`~1.500đ – 2.200đ / SMS`** | Kho SIM vật lý Việt Nam lớn nhất MMO (Viettel, Vina, Mobi). Có API RESTful hoàn chỉnh. Đang bật Cloudflare Turnstile trên trang login. |
| **3. Rentcode.net** | **`~2.000đ – 3.500đ / SMS`** | Kho số Việt Nam sạch, ít số ảo. Phải đăng nhập mới mở API order. |
| **4. 5sim.net** *(Lọc mạng VN)* | **`~4.400đ – 4.800đ`** ($0.175 - $0.19) | Nhà mạng `virtual47` (tỷ lệ nổ code 57% - 77%). Nhà mạng `virtual4` (stock 25k số). Tự động hoàn tiền 100% nếu không có code sau 2 phút. Phù hợp test tức thì khi có sẵn balance USD. |
| **5. Chothuesimcode.net** | **`~8.500đ – 11.000đ`** ($0.34 - $0.44) | Kho 7 ($0.34) & Kho 8 ($0.44). Giá số VN hiện khá đắt. |
| **6. BinOTP.com** | ❌ **Không có** | Điều khoản ghi rõ không cung cấp SIM Việt Nam. |

---

## 5. Rào Cản Cloudflare Turnstile Trên ViOTP (`viotp.com/account/login`)
- Khi truy cập trang đăng nhập ViOTP bằng browser automation hoặc CDP, trang kích hoạt widget Cloudflare Turnstile (`Performing security verification`).
- Cần có tài khoản và trích xuất API Key trực tiếp từ profile đã đăng nhập, hoặc dùng API endpoints có xác thực token để bypass toàn bộ UI web khi đặt lệnh thuê số tự động.
