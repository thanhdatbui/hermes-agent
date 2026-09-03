# Quy Tắc Tự Động Unlock Sau Khi Hoàn Tất & Bẫy Mail Khôi Phục Của Shop Phôi (2026-08-22)

## 1. Quy Tắc Tự Động Unlock Sau Khi Hoàn Thành Nhiệm Vụ (User Invariant)
- **Trong quá trình thực thi / sửa lỗi live:** BẮT BUỘC giữ lease lock để ngăn các tiến trình farm khác can thiệp.
- **Sau khi hoàn thành 100% quy trình Takeover:** BẮT BUỘC **TỰ ĐỘNG UNLOCK NGAY** (xóa file `machine_<N>.lock.json` trong `C:\Users\Kibe\.codex\device-locks`), tuyệt đối không để máy bị khóa cứng làm cản trở lịch chạy farm tiếp theo.

## 2. Phân Loại Hotmail Mua Phôi Trong Kho (`gmail_clean_v2.xlsx`)
Khi rà soát đổi mật khẩu hàng loạt cho các Hotmail đủ tuổi (> 7 ngày), xuất hiện 2 nhóm tài khoản rõ rệt:

### Nhóm A: Tài khoản đã gắn Mail KP của mình (`thanhdatbui1995@gmail.com`) hoặc Trắng Thông Tin
- **Hiện trường:** Khi đăng nhập vào web Microsoft hoặc Reset password, Microsoft gửi mã về Gmail của mình.
- **Xử lý:** Chạy Full quy trình 4 bước Takeover:
  1. Đổi Pass mới -> Ghi Excel cột 3.
  2. Bấm "Đăng xuất khỏi mọi nơi" (Sign out everywhere).
  3. Mở App Outlook -> Xác thực lại OTP từ Gmail -> Đảm bảo Inbox hoạt động bình thường.
  4. Tự động Unlock máy.

### Nhóm B: Hotmail mua phôi cũ còn dính Mail KP của shop (`kh*****@gmail.com` - Ví dụ Máy 1 `lipseybaroua@hotmail.com`)
- **Hiện trường:**
  - Nhập đúng mật khẩu cũ trên Web Microsoft -> Microsoft yêu cầu: *"Sắp hoàn thành: Xác minh danh tính - Gửi mã đến kh*****@gmail.com"*.
  - Vì không có quyền truy cập vào hộp thư `khoaleemagic@gmail.com` / `khoalemagic@gmail.com` của shop phôi ban đầu, không thể vượt qua bước xác minh trên web để đổi pass.
- **Trạng thái thực tế trên Farm:**
  - Trong **App Microsoft Outlook** trên điện thoại: Tài khoản đã được đăng nhập từ trước, phiên đăng nhập (OAuth session) vẫn hoạt động 100%, Inbox đang nhận mail OTP TikTok mượt mà (ví dụ mã TikTok `068876` nhận hôm qua).
- **Hành động chuẩn:**
  - **KHÔNG cố gắng đổi pass trên Web** (sẽ làm đứt session hoặc kẹt checkpoint).
  - Giữ nguyên tài khoản trong App Outlook trên máy để tiếp tục nhận mã TikTok phục vụ nuôi farm / đăng ký.
  - Tự động Nhả Lock máy ngay sau khi kiểm tra.
