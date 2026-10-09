# Kỷ luật Chẩn đoán Lỗi Đăng nhập: Phân loại Lệch Mapping Excel vs Lỗi Gõ Phím ADB vs Session Expired

## Bối cảnh sự cố thực tế (17/09/2026 - Máy 30)
Khi đăng nhập các tài khoản TikTok phôi trên thiết bị mới (Máy 30):
- Tài khoản `phamnhi1770` (`halongbeat1@hotmail.com`) và `susannemorti9` (`susannemortimerabby9@hotmail.com`).
- Agent nhập mật khẩu từ file Excel `taikhoan_dat_v2_updated .xlsx` và bị TikTok báo đỏ:
  `Sai tài khoản hoặc mật khẩu. Còn 4 lần nhập. Hãy thử lại.`
- User lập tức chất vấn logic và tính toàn vẹn dữ liệu:
  > *"mà đm pass lưu excel do script ghi làm sao mà sai, 1 là m nhập k đúng 2 là hàm lưu pass bị lệch dữ liệu?"*

---

## 1. Phương pháp loại trừ: Lỗi gõ phím ADB (IME Input Corruption)

### Triệu chứng & Nguyên nhân
Khi dùng `adb shell input text "<password>"`:
- Các ký tự đặc biệt shell như `&`, `!`, `$`, `#`, `*`, `;` bị shell Linux hiểu nhầm là lệnh ngầm hoặc toán tử nền.
- Bàn phím Samsung Keypad có thể tự động bật tính năng sửa từ/tiên đoán văn bản (predictive text) dẫn đến nuốt hoặc thêm khoảng trắng.

### Quy chuẩn kiểm tra loại trừ bằng AdbKeyboard (Base64)
Để loại trừ 100% lỗi do gõ phím ADB, **bắt buộc** dùng `AdbKeyboard` (`com.github.uiautomator/.AdbKeyboard`):
```python
import base64

# Kích hoạt AdbKeyboard
adb.shell(['ime', 'enable', 'com.github.uiautomator/.AdbKeyboard'])
adb.shell(['ime', 'set', 'com.github.uiautomator/.AdbKeyboard'])

# Gửi chuỗi mã hóa base64 qua broadcast intent
encoded = base64.b64encode(password.encode('utf-8')).decode('ascii')
adb.shell(['am', 'broadcast', '-a', 'ADB_KEYBOARD_INPUT_TEXT', '--es', 'text', encoded])
```
- **Quy tắc phán đoán:** Nếu nhập qua AdbKeyboard mà server TikTok vẫn báo `Sai tài khoản hoặc mật khẩu` ➔ **Loại trừ hoàn toàn lỗi do gõ phím.**

---

## 2. Phương pháp phát hiện: Lệch Mapping Dữ Liệu Excel (Data Misalignment)

### Bản chất kỹ thuật
Trong các đợt chạy batch reg hàng loạt (đặc biệt là reg Hotmail/Outlook):
- Cột `ID` TikTok, cột `PASS` TikTok và cột `GMAIL` / `PASS MAIL` trong file Excel quản lý (`taikhoan_dat_v2_updated .xlsx`) có thể bị ghi lệch dòng nếu một tác vụ bị gián đoạn giữa chừng hoặc ghi đè sai index.
- Thao tác kiểm chứng tính toàn vẹn của một dòng tài khoản:
  1. Thử đăng nhập bằng Email `halongbeat1@hotmail.com` ➔ TikTok nhận diện có tài khoản và cho nhận OTP.
  2. Thử đăng nhập bằng ID TikTok `phamnhi1770` ➔ TikTok báo đỏ: **`Tài khoản không tồn tại`**.
- 👉 **Kết luận vững chắc:** Dòng dữ liệu này đã bị mapping sai: username `phamnhi1770` không thuộc về email `halongbeat1@hotmail.com`, dẫn đến mật khẩu `PASS` lưu ở cột đó thực chất là của một tài khoản khác.

---

## 3. Bẫy Reset Mật Khẩu: Lỗi Phiên Hết Hạn (Expired Session / Action Restriction)

### Hiện tượng
Khi tài khoản bị nhập sai pass quá nhiều lần liên tiếp, Agent bấm vào:
`Bạn cần trợ giúp đăng nhập?` ➔ `Đặt lại mật khẩu bằng email` ➔ Nhập email ➔ Bấm `Tiếp tục`.
Màn hình TikTok lập tức báo đỏ:
> **`Phiên đã hết hạn. Hãy thoát ứng dụng và thử lại.`**

### Cơ chế bảo vệ của TikTok
- TikTok phát hiện thiết bị và phiên đăng nhập này đang có hành vi thử mật khẩu bất thường (Brute-force / Credential Stuffing).
- Nó không cấp phát mã OTP đặt lại mật khẩu mới qua email cho phiên này mà tạm thời vô hiệu hóa luồng reset pass trên thiết bị (Action Restriction).

---

## 4. Kỷ luật phản hồi & Hướng xử lý bắt buộc

1. **Không suy đoán cảm tính:** Khi mật khẩu báo sai, phải kiểm tra ngay cả 2 nhánh (IME gõ phím vs Mapping Excel) bằng bằng chứng thực nghiệm (AdbKeyboard + thử ID TikTok trực tiếp).
2. **Đối với dàn tài khoản phôi (`Video Đã Đăng = 0`):**
   - Nếu phát hiện tài khoản bị lệch mapping pass hoặc kẹt phiên reset mật khẩu: CẤM cố chấp brute-force làm cháy IP máy farm.
   - Báo cáo rõ ràng tình trạng lệch dữ liệu cho user và đề xuất thay thế bằng tài khoản mới có sẵn token/pass chuẩn từ kho.
