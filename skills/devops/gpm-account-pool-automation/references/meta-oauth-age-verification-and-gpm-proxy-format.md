# Meta OAuth Age Verification & GPM Proxy Format Patterns

## 1. GPM v3 Proxy Format Rule
Khi cập nhật proxy có User/Password vào GPM profile qua API `http://127.0.0.1:19995/api/v3/profiles/update/<profile_id>`:
- **CẤM DÙNG:** `http://user:pass@ip:port` hoặc `socks5://user:pass@ip:port` (GPM sẽ parse lỗi `ERR_NO_SUPPORTED_PROXIES` hoặc trả về "Không thể kết nối tới proxy").
- **CHUẨN BẮT BUỘC:** `ip:port:username:password` (4 trường cách nhau bằng dấu hai chấm `:`).
  * Ví dụ Webshare Free US: `198.46.161.42:5092:opmighkf:htikm8njcmjb`

## 2. Webshare Free Account Proxy Pool
- Tài khoản Webshare miễn phí (`thanhdatbui1995@gmail.com`) có 10 proxy cố định / 1 GB bandwidth.
- Có sẵn 4 IP US Datacenter (Los Angeles & Piscataway) sống 100%:
  * `198.46.161.42:5092` (LA)
  * `198.23.243.226:6361` (LA)
  * `38.154.185.97:6370` (Piscataway)
  * `191.96.254.138:6185` (LA)
- Dùng các IP này vượt geoblock Muse AI / US services mà không lo timeout như proxy public free.

## 3. Meta (Facebook / Instagram) OAuth & Age Verification
- **Instagram OAuth qua Playwright:**
  * Hỗ trợ tự động điền form và giải mã TOTP 2FA qua script (`hmac.sha1` / `pyotp`).
  * **Cạm bẫy:** Nếu nick Instagram đã từng liên kết với một Meta Account Center khác trước đó, Meta sẽ chặn với thông báo: *"Không thể thêm vì trang cá nhân này đã thuộc Tài khoản Meta này rồi"*. Cần dùng nick Instagram nguyên bản chưa từng link Meta Account.
- **Facebook OAuth Client Bot Protection:**
  * Form đăng nhập Facebook web có cơ chế hash `enc_password` và dynamic payload. Tool tự động click hoặc submit form JS dễ bị lỗi *"Không thể xử lý yêu cầu của bạn"* (CSRF / Anti-bot).
  * **Xử lý chuẩn:** Tool mở sẵn popup OAuth, căn chỉnh giao diện sạch sẽ, chụp ảnh kiểm chứng (GATE 6), và bàn giao thông tin đăng nhập (UID/Pass/2FA) để thao tác thủ công khi cần thiết.
