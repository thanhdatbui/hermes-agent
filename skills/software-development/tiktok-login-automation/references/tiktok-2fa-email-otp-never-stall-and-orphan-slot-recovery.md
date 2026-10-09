# Kỷ luật Xử lý 2FA OTP, Khôi phục Nick từ Fast Login và Xử lý Trần 8 Tài Khoản TikTok Farm

Đúc kết từ phiên thực chiến ngày 17/09/2026 trên cụm Samsung S7 (M1, M51, M59, M60, M66).

---

## 1. KỶ LUẬT 2FA OTP — ACTION-FIRST, CẤM DỪNG LẠI HỎI USER TRÁNH DÍNH MAGIC LINK / RATE LIMIT 900s

### Cơ chế trừng phạt của TikTok khi bỏ dở 2FA:
- Khi runner/kỹ thuật viên trigger đăng nhập (One-Tap Fast Login hoặc nhập user/pass) và màn hình TikTok chuyển sang **"Xác minh 2 bước"** (đòi OTP 6 số qua Hotmail/Outlook/Gmail):
- **CẤM TUYỆT ĐỐI** dừng lại hỏi user hay đưa thiết bị về chế độ nghỉ khi chưa nhập mã OTP.
- Nếu bỏ dở màn hình 2FA OTP từ 2-3 lần, TikTok sẽ kích hoạt cơ chế bảo mật nâng cao:
  1. **Chuyển sang Magic Link:** Không cho nhận mã số OTP nữa mà bắt bấm link xác thực gửi trong email (rất khó tự động hóa trên phone farm).
  2. **Rate limit 900s (15 phút):** Khóa tạm thời cổng đăng nhập của tài khoản.

### Quy trình chuẩn xử lý 2FA:
1. **Tra cứu TOTP Secret trước:** Tra cột `2FA` trong `taikhoan_dat_v2_updated .xlsx`. Nếu có Secret Key 32 ký tự, sinh mã bằng `automation_core.totp.generate_totp(secret)` và nhập ngay.
2. **Nếu đòi OTP Email (Hotmail):**
   - Bật app Outlook (`com.microsoft.office.outlook`) trên máy.
   - Đọc thư mới nhất của TikTok.
   - Trích xuất 6 số OTP tươi.
   - Mở lại TikTok và điền mã OTP ngay lập tức.
3. Hoàn tất đăng nhập $\rightarrow$ Chuyển vào Profile $\rightarrow$ Chụp screencap nghiệm thu $\rightarrow$ Mới được bấm `HOME` và tắt màn hình.

---

## 2. NGUYÊN TẮC GIẢI PHÓNG SLOT VÀ XỬ LÝ NICK MỒ CÔI (PARASITE) TRẦN 8 NICK

### Giới hạn trần 8 nick:
- TikTok Android chỉ cho phép tối đa **8 tài khoản** đăng nhập đồng thời trên Switcher.
- Khi chạm trần 8 nick, nút *"Thêm tài khoản"* biến mất hoàn toàn.

### Hiện tượng Nick mồ côi (Parasite) chiếm slot:
- Khi chạy tool bù slot hoặc reg mới, script ghi đè thông tin nick mới vào Excel nhưng **không thực hiện logout nick cũ trên máy thật**.
- Nick cũ vẫn ngồi chiếm chỗ trên máy thật. Khi máy chạm 8 nick, các nick chính chủ (Row 1/Row 2) bị đẩy ra bộ nhớ đệm Fast Login ("Chào mừng bạn trở lại").

### Quy tắc an toàn khi giải phóng slot:
1. **CẤM logout nick mới reg (<7 ngày, chưa có 2FA):** Việc logout nick mới reg sẽ đổi device fingerprint, khi đăng nhập lại TikTok sẽ checkpoint/đòi OTP mail, nếu mail die là mất nick vĩnh viễn!
2. **Quy trình dọn nick mồ côi:**
   - Đối soát Switcher máy thật với `taikhoan_run_safe.xlsx`.
   - Tìm ra nick có trên máy thật nhưng không có trong Excel run_safe (nick mồ côi).
   - Tra cứu backup (`taikhoan_dat_v2_updated.bak-*.xlsx`) để lưu lại: `User`, `Pass TikTok`, `Mail`, `Pass Mail`.
   - Chuyển Switcher sang nick mồ côi $\rightarrow$ Vào `Cài đặt và quyền riêng tư` $\rightarrow$ Chọn `Đăng xuất` đơn lẻ đúng nick đó.
   - Sau khi logout, Switcher sẽ xuất hiện lại nút *"Thêm tài khoản"*.

---

## 3. KHÔI PHỤC NICK CHÍNH TỪ CACHE FAST LOGIN

- Bấm *"Thêm tài khoản"* $\rightarrow$ Chọn nick chính chủ trong danh sách *"Chào mừng bạn trở lại"*.
- Điền pass / 2FA OTP $\rightarrow$ Đăng nhập thành công trở lại Switcher $\rightarrow$ Khớp 100% với Excel.
