# Quy tắc Xử lý 2FA OTP, Khôi phục Nick Lệch Excel và Trần 8 Tài Khoản TikTok Farm

Tài liệu đúc kết từ thực chiến ngày 17/09/2026 trên cụm Samsung S7 (M1, M51, M59, M60, M66).

---

## 1. KỶ LUẬT 2FA OTP & CHỐNG CHUYỂN MAGIC LINK RATE LIMIT (900s)

### Hiện tượng & Rủi ro chí mạng:
Khi bot hoặc kỹ thuật viên kích hoạt đăng nhập lại (nhập mật khẩu hoặc bấm Fast Login) vào một tài khoản có bật 2FA (gửi OTP qua Hotmail/Outlook/Gmail):
- **Cơ chế phòng thủ của TikTok:** Nếu hệ thống đã gửi mã OTP về email mà agent không lấy OTP nhập ngay mà lại dừng lại hỏi người dùng / bỏ dở màn hình xác minh, chỉ sau 2-3 lần bỏ dở TikTok sẽ **tự động chuyển phương thức xác thực sang Magic Link qua email** hoặc áp **Rate limit chặn đăng nhập 900 giây (15 phút)**.
- **Hậu quả:** Mất khả năng tự động hóa đăng nhập, kẹt tài khoản, nguy cơ die checkpoint nếu email không truy cập được trình duyệt.

### Quy tắc bất khả xâm phạm:
1. **Action-First khi chạm cổng 2FA:** Tuyệt đối không dừng lại hỏi user khi đang ở màn hình chờ OTP. Đã trigger login thì BẮT BUỘC phải đọc ngay hộp thư (Outlook app / Graph API / Hotmail) hoặc sinh mã TOTP để điền vào cho xong flow.
2. **Ưu tiên TOTP Secret:** Trước khi lấy OTP mail, luôn tra cột 2FA trong `taikhoan_dat_v2_updated .xlsx`. Nếu có Secret Key 32 ký tự, dùng `automation_core.totp.generate_totp(secret)` nhập ngay trong 30s.
3. **Đọc OTP tươi từ Outlook App:** Nếu nick gửi OTP về Hotmail, mở app Outlook trên thiết bị (`com.microsoft.office.outlook`), đọc tiêu đề thư mới nhất của TikTok, trích xuất 6 số OTP rồi quay lại TikTok điền ngay.

---

## 2. NGUYÊN TẮC GIẢI PHÓNG SLOT & ĐỐI SOÁT TRẦN 8 NICK TRÊN MÁY THẬT

### Giới hạn vật lý:
- Ứng dụng TikTok trên Android giới hạn tối đa **8 tài khoản** đăng nhập đồng thời trên Account Switcher.
- Khi đạt đủ 8 nick, nút *"Thêm tài khoản"* sẽ hoàn toàn biến mất.

### Bẫy lệch dữ liệu (Excel vs Máy thật):
- **Hiện tượng Nick mồ côi (Parasite):** Các đợt chạy script bù slot hoặc reg mới thường ghi đè dữ liệu tài khoản vào Excel nhưng **quên thực hiện lệnh logout trên thiết bị thật**. Hậu quả là nick cũ vẫn nằm chiếm 1 slot trên Switcher máy thật, còn Excel thì tưởng slot đó đã trống.
- **Hậu quả dây chuyền:** Khi nick chính thức (Row 1/Row 2) bị văng ra cache Fast Login, bot không thể nạp lại vào Switcher vì máy đã kẹt cứng 8 nick.

### Quy trình giải phóng slot an toàn tuyệt đối:
1. **CẤM logout nick mới reg (<7 ngày, chưa bật 2FA):** Việc logout nick mới reg sẽ làm thay đổi device fingerprint, khi đăng nhập lại TikTok sẽ ép xác minh qua email hoặc checkpoint, dễ làm chết nick vĩnh viễn nếu mail die.
2. **Chỉ logout nick mồ côi cũ đã có backup:**
   - Tra cứu và đối soát nick mồ côi trong các file backup lịch sử (`taikhoan_dat_v2_updated.bak-*.xlsx`).
   - Đảm bảo đã lưu trữ đủ: `Username`, `Password TikTok`, `Email`, `Password Email`.
3. **Thao tác logout đơn lẻ qua Settings (CẤM `pm clear`):**
   - Chuyển Account Switcher sang đúng nick mồ côi cần logout.
   - Vào `Hồ sơ` -> `Menu 3 gạch` -> `Cài đặt và quyền riêng tư` -> Cuộn xuống đáy -> `Đăng xuất` -> Xác nhận `Đăng xuất`.
   - Kiểm tra Switcher xuất hiện lại nút *"Thêm tài khoản"*.

---

## 3. KHÔI PHỤC NICK CHÍNH CHỦ TỪ CACHE FAST LOGIN (ONE-TAP LOGIN)

Khi nạp lại tài khoản chính chủ (Row 1/Row 2) bị thiếu trên Switcher:
1. Bấm nút *"Thêm tài khoản"*.
2. Tại màn hình *"Chào mừng bạn trở lại"*, TikTok thường lưu sẵn danh sách One-Tap Login (Fast Login).
3. Bấm vào đúng avatar/username của tài khoản cần nạp.
4. Nếu yêu cầu mật khẩu: Điền pass từ Master DAT.
5. Nếu yêu cầu 2FA OTP: Điền TOTP sinh từ Secret hoặc OTP email ngay lập tức.
6. Nghiệm thu màn hình Profile (bắt buộc chụp screencap và verify text node khớp Handle).
7. Hoàn trả trạng thái thiết bị: Bấm phím `HOME` (keyevent 3) và tắt màn hình (keyevent 26) đưa thiết bị về nghỉ an toàn.
