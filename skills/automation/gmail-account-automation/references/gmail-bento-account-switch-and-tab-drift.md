# Gmail Account Switching & Google Bento Popup Safeguards (2026-09-20)

## 1. Cơ Chế Switch Account Chuẩn Trên App Gmail (S7 / Phone Farm)

### Hiện tượng & Cạm bẫy:
Trên điện thoại Android Phone Farm, thường có đồng thời từ 3 đến 8 tài khoản Google được nạp trên cùng một máy. Khi thực hiện flow tự động hóa cần đọc email / mã OTP của một nick vừa đăng ký hoặc vừa nạp:
- App Gmail thường mở ra hòm thư của nick active mặc định trước đó (thường là nick TikTok hoặc tài khoản cũ).
- Nếu script chỉ gọi `am start com.google.android.gm` rồi regex quét mã 6 chữ số mù quáng trên màn hình: Script sẽ **bốc nhầm mã OTP cũ** của TikTok hoặc các thông báo bảo mật trước đó $\rightarrow$ Thất bại với lỗi *"Mã không chính xác"*.

### Cạm bẫy tử huyệt: Tap trúng Header Bento Popup
Khi tap vào Avatar góc trên bên phải (`985, 138`) để mở popup chuyển tài khoản (Google Bento Popup):
- Tài khoản đang active nằm ở phần đầu: `resource-id="com.google.android.gm:id/og_compact_header_secondary_text"`.
- Các tài khoản phụ khác nằm ở danh sách bên dưới: `resource-id="com.google.android.gm:id/og_secondary_account_information"`.
- **HẬU QUẢ NGHIÊM TRỌNG:** Nếu hàm tìm kiếm `find_node_in_xml(xml, target_email)` tìm trúng node header compact và thực hiện `tap` vào tọa độ đó, Google sẽ mở ra toàn màn hình trang **Quản lý Tài khoản Google (Google Account Management)**! Trang này che khuất hoàn toàn app Gmail và script không thể đọc được hòm thư nữa.

---

## 2. Quy Trình Chuyển Đổi Tài Khoản An Toàn (`ensure_gmail_account_active`)

1. **Mở Gmail & Bật Popup:**
   - Khởi chạy Gmail intent: `am start -n com.google.android.gm/.ConversationListActivityGmail`.
   - Tap avatar góc trên phải: `(985, 138)`.
2. **Kiểm tra trạng thái Active:**
   - Đọc XML. Nếu `target_email` nằm trong `og_compact_header`: Tài khoản **đã đang active**!
   - **BẮT BUỘC:** CẤM tap vào header này. Thực hiện tap ra ngoài vùng popup (ví dụ `(540, 1800)`) để đóng popup và tiếp tục đọc thư.
3. **Switch nếu là tài khoản phụ:**
   - Nếu `target_email` nằm trong `og_secondary_account_information`: Tap vào node để chuyển sang nick mới.
   - Xử lý dọn dẹp các popup chào mừng / duyệt web an toàn xuất hiện sau khi switch (*"Không, cảm ơn"*, *"Bỏ qua"*).
4. **Lọc OTP nghiêm ngặt:**
   - Chỉ trích xuất mã OTP khi tiêu đề hoặc nội dung email xác nhận đúng là từ dịch vụ mục tiêu (ví dụ `OpenAI` / `ChatGPT`). Tuyệt đối không lấy mã từ email TikTok hay dịch vụ khác.

---

## 3. Chống Trôi Tab Chrome Khi Chuyển App (Chrome Tab Drift Protection)

- Khi switch qua lại giữa Gmail và Chrome, nếu chỉ gọi `am start -n com.android.chrome.Main`, Chrome có thể mở lại tab nền gần nhất trước đó (ví dụ tab tìm kiếm Google cũ `google.com/search?q=...`), dẫn đến việc script click nhầm vào kết quả tìm kiếm Google.
- **Biện pháp:** Luôn kiểm tra URL sau khi foreground Chrome; nếu bị trôi sang `google.com` hoặc tab lạ, lập tức bắn lại intent `VIEW` trỏ đúng vào URL mục tiêu.
