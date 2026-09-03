# Recovery Email Trade-offs, Sign Out Everywhere, and Outlook App Re-authentication (2026-08-22)

## 1. Nguyên Tắc Cốt Tử: Không Tự Ý Gắn Gmail Cá Nhân Làm Mail Khôi Phục (Recovery Mail)

### Bối cảnh & Rủi ro thực tế:
- **Dính bẫy treo 30 ngày (30-day security pending):** Khi vào trang Microsoft Account để xóa hoặc thay thế phương thức khôi phục duy nhất, Microsoft sẽ khóa tính năng quản lý bảo mật và bắt chờ 30 ngày mới có hiệu lực hoàn toàn. Trong 30 ngày này tài khoản bị hạn chế tính năng và không thể bàn giao tài khoản sạch cho khách.
- **Khách dính Checkpoint khi đăng nhập IP lạ:** Khi xuất bán kênh/tài khoản (định dạng chuẩn `User TT | Pass TT | Hotmail | Pass Hotmail`), khách login Hotmail từ thiết bị lạ, Microsoft sẽ chặn và bắt gửi OTP về Gmail cá nhân của chủ farm (`th*****@gmail.com`) -> Khách không có quyền truy cập -> Khiếu nại/bắt đền đơn.
- **Chiến lược chuẩn khi nuôi Farm:**
  1. **Chỉ đăng nhập bằng `User | Pass` thẳng vào App Microsoft Outlook trên Android**: App di động nhận OTP TikTok mượt mà, không bắt ép thêm Mail KP như trên trình duyệt Web.
  2. **Nếu lỡ vào Web bị hỏi bảo vệ tài khoản:** Bấm *"Bỏ qua / Để sau"* (Skip for now).
  3. **Nếu điện thoại bị hỏng/đổi máy mới:** Chỉ cần `Mail | Pass` đăng nhập lại vào App Outlook trên máy mới. Nếu Microsoft yêu cầu xác minh bảo mật, có thể dùng bất kỳ số điện thoại/OTP tạm thời nào (thuê sim rác 1k) để vượt qua ngay tại thời điểm đó mà không bị trói buộc vào Gmail cá nhân.

---

## 2. Quy Trình Takeover & Change-Info Toàn Diện (Full Lifecycle)

Quy trình bảo vệ tài khoản Hotmail chuẩn sau khi ngâm đủ 7 ngày gồm 4 bước liên hoàn:

```
┌─────────────────────────┐
│ 1. Đổi Mật Khẩu         │ -> Đổi mật khẩu mạnh trên Web Microsoft, ghi ngay Excel + backup.
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ 2. Sign Out Everywhere  │ -> Vào `account.live.com/proofs/manage/additional` bấm "Đăng xuất khỏi mọi nơi"
└───────────┬─────────────┘    để thu hồi/revoke toàn bộ session token cũ trong vòng 24h.
            ▼
┌─────────────────────────┐
│ 3. Đồng Bộ Outlook App  │ -> Mở App Outlook trên máy farm, nhập mật khẩu mới (hoặc xác thực OTP),
└───────────┬─────────────┘    đưa app về trạng thái Inbox sạch (mất thanh đen cảnh báo).
            ▼
┌─────────────────────────┐
│ 4. Lưu Kho & Khóa Máy   │ -> Cập nhật workbook, giữ lock máy nếu đang trong phiên bảo trì.
└─────────────────────────┘
```

---

## 3. Thao Tác Kỹ Thuật Khi "Đăng Xuất Khỏi Mọi Nơi" (Sign Out Everywhere)

1. **URL trực tiếp:** `https://account.live.com/proofs/manage/additional` (Tùy chọn bảo mật bổ sung).
2. **Xác thực danh tính trước khi vào:**
   - Microsoft có thể yêu cầu xác nhận lại mật khẩu hoặc gửi mã OTP về email khôi phục đã liên kết.
   - Chọn *"Sử dụng mật khẩu của bạn"* hoặc nhập OTP từ IMAP reader.
3. **Cuộn trang tìm mục:**
   - Mục **"Đăng xuất khỏi mọi nơi"** nằm ở khoảng 70% – 85% chiều dọc của trang (phía trên mục *Windows Hello* và *Mã phục hồi*).
   - Bấm vào dòng chữ xanh **"Đăng xuất khỏi mọi nơi"** -> Xuất hiện Modal Dialog *"Đăng xuất khỏi mọi nơi?"*.
4. **Xác nhận Đăng xuất:**
   - Tap nút màu xanh **"Đăng xuất"** -> Xuất hiện popup thông báo thành công có dấu tích xanh:
     > **"Chúng tôi đã bắt đầu đăng xuất cho bạn"**
     > *"Trong 24 giờ tới, bạn sẽ bị đăng xuất khỏi nhiều nơi khác nhau mà tài khoản của bạn được dùng để đăng nhập..."*
   - Tap **"Tiếp tục"** hoặc đóng Chrome.

---

## 4. Xử Lý Đồng Bộ Lại App Outlook Sau Khi Đổi Pass / Sign Out

Sau khi đổi mật khẩu trên Web và bấm Sign Out Everywhere:
1. Mở lại **App Outlook** trên máy (`com.microsoft.office.outlook`).
2. Nếu app hiện thanh thông báo đen ở dưới cùng: *"Vui lòng đăng nhập vào <email> [ĐĂNG NHẬP]"*:
   - Tap nút **"ĐĂNG NHẬP"**.
   - Nhập mật khẩu mới vừa đổi (hoặc nhận OTP xác thực nếu được hỏi).
3. Sau khi xác thực xong, vuốt làm mới hộp thư -> Kiểm tra thanh đen cảnh báo biến mất hoàn toàn và danh sách thư hiển thị bình thường -> Hoàn tất.
