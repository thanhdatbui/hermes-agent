# Danh mục sản phẩm & Chính sách bảo hành BoxTaiKhoan.com (Hotmail) — 2026-08-21

## 1. Danh mục sản phẩm Hotmail (Cập nhật trực tiếp 21/08/2026)

| Tên sản phẩm | Giá | Định dạng | Tình trạng kho | Đặc điểm & Phân loại nghiệp vụ |
| :--- | :---: | :--- | :---: | :--- |
| **Tài Khoản Hotmail TRUSTED GraphAPI** *(Live Vĩnh Viễn, Mail Khôi Phục Fviainboxes - Chưa Qua Dịch Vụ)* | **262đ** | `mail\|pass` | Còn hàng (~30.7k) | **Loại 1 (Không Token):** Rẻ hơn 131đ/acc. Mail sạch chưa qua dịch vụ, có mail KP `fviainboxes`. Phù hợp workflow: nạp máy S7 qua Outlook app -> reg TikTok -> đổi info sau 7 ngày. |
| **Tài Khoản Hotmail Trust - OAuth2 [IMAP/POP3/GRAPH]** *(Live 12 đến 36 Months - Zin 100% - Còn Skip 7 Ngày)* | **393đ** | `mail\|pass\|refresh_token\|client_id` | Còn hàng (~67.3k) | **Loại 2 (Có Token OAuth2):** Đọc OTP trực tiếp từ xa qua Graph API (`Mail.Read`), không cần mở app Outlook trên thiết bị. Phù hợp reg TikTok song song số lượng lớn. Đổi pass sau 7 ngày sẽ vô hiệu hóa refresh_token. |
| **Tài Khoản Hotmail Trusted Live 3 Đến 6+ Tháng** *(Format OAuth2 - Hàng Qua Reg TikTok)* | **150đ** | `mail\|pass\|refresh_token\|client_id` | Hết hàng (0) | Hàng đã qua sử dụng reg TikTok. |

---

## 2. Quy định & Chính sách bảo hành của Shop (BoxTaiKhoan)

1. **Thời hạn bảo hành:** **24 giờ** kể từ thời điểm mua hàng. Đơn hàng tự động xóa khỏi hệ thống sau 3 ngày.
2. **Trường hợp ĐƯỢC bảo hành:**
   - Đăng nhập lần đầu thất bại do: Sai UID/Email, **Sai Password**, Sai mã 2FA.
   - Tài khoản bị Checkpoint hoặc Die trước thời điểm mua.
   - Thông tin không đúng như mô tả trên website.
3. **Trường hợp TỪ CHỐI bảo hành:**
   - Không bảo hành tài khoản bị die do ngâm lâu không sử dụng hoặc thao tác sai từ phía khách hàng.
   - Không bảo hành trường hợp không Change thông tin bảo mật sau 7 ngày dẫn đến bị back/hack.
   - Sử dụng VPN/Proxy bẩn, IP blacklist, login tool auto không ổn định.
4. **Quy tắc quan trọng khi báo bảo hành cho Shop:**
   - **BẮT BUỘC có bằng chứng sai pass thật:** Chỉ báo shop khi màn hình Microsoft xuất hiện chuỗi cảnh báo đỏ thật sự (`Mật khẩu đó không đúng với tài khoản Microsoft của bạn` / `That password is incorrect`).
   - Tuyệt đối không quy kết sai mật khẩu khi gặp lỗi UI delay, WebView loading trắng, hay proxy timeout.
   - Định dạng gửi báo shop: Chỉ gửi danh sách rút gọn `email|password`, không đính kèm token hay client_id dài dòng.

---

## 3. Web Domain & Tự động hóa mua hàng qua CDP / API (2026-08-22)

- **Domain chuẩn:** `https://boxtaikhoan.com` (tên gọi khác / alias `boxtaikhoanmmo.com` bị lỗi `ERR_NAME_NOT_RESOLVED`, phải điều hướng về đúng `boxtaikhoan.com`).
- **Lấy Cookie / Phiên đăng nhập từ Chrome cá nhân:**
  - Chrome chính của user (`C:\Users\Kibe\AppData\Local\Google\Chrome\User Data`) cần được khởi động kèm cờ `--remote-debugging-port=<port>` (ví dụ `9223`) để mở cổng CDP.
  - Profile mặc định của Hermes chạy trên port `9222` (`AppData\Local\hermes\browser_profile`).
  - **CDP Handshake WebSocket 403 Forbidden:** Chromium mới (Chrome 151+) bắt buộc cấu hình `suppress_origin=True` khi kết nối qua Python `websocket-client` (`ws.connect(url, suppress_origin=True)`) hoặc khởi động Chrome kèm `--remote-allow-origins=*` để tránh lỗi `403 Handshake status`.

