# GPM WebRTC Data JSON Leak & Google Account Geo-Safety

## 1. Cơ Chế Lộ IP Thật Qua Cờ `--web-rtc-data-json` Của GPM
Khi GPM Login khởi chạy Chromium core (`chrome.exe`), launcher của GPM tự động inject tham số WebRTC vào command line:
```bash
--web-rtc-data-json="{\"fake_in_1\":true,\"fake_relay\":true,\"mode\":\"real\",\"publicIP\":\"<local_ip>\",\"stun_server\":\"stun:stun.12voip.com:3478\"}"
```
- **Hệ quả:** Bản thân Chromium core bị gán cứng `publicIP` là IP mạng thật của máy host (Việt Nam).
- **Hiện tượng:** Dù trên browser có cài extension VPN (TouchVPN, WARP...) hoặc proxy HTTP, traffic duyệt web có thể hiển thị IP ngoại trên `ipinfo.io`, nhưng khi truy cập các trang kiểm tra WebRTC (`browserleaks.com/webrtc`) hoặc các dịch vụ kiểm tra vị trí gắt gao (Meta SSO, Muse AI, TikTok, Google), STUN discovery của WebRTC sẽ bắn thẳng `publicIP` thật của máy host.
- **Dấu hiệu nhận biết:** Trang web đích tự động chuyển sang tiếng Việt (`vi-VN`) hoặc văng vào màn hình Regional Waitlist ("Sản phẩm hiện chưa có ở quốc gia hoặc khu vực của bạn").

### Cách Khắc Phục / Spoof WebRTC Chuẩn:
Khi khởi chạy Chromium core qua script tự động hoặc Playwright CDP, bắt buộc ghi đè cờ này thành mode `fake` kèm IP mục tiêu:
```python
cmd = [
    CHROME_EXE,
    f'--user-data-dir={PROFILE_DIR}',
    f'--load-extension={EXT_DIR}',
    '--remote-debugging-port=49698',
    '--no-first-run',
    '--no-default-browser-check',
    '--lang=en-US',
    # Spoof WebRTC sang IP ngoại:
    f'--web-rtc-data-json={{"fake_in_1":true,"fake_relay":true,"mode":"fake","publicIP":"{TARGET_PROXY_IP}","stun_server":"stun:stun.12voip.com:3478"}}',
    # Chặn triệt để non-proxied UDP leak:
    '--disable-webrtc-multiple-routes',
    '--enforce-webrtc-ip-permission-check',
    '--force-webrtc-ip-handling-policy=disable_non_proxied_udp',
]
```
Trong Playwright context, có thể chèn thêm init script vô hiệu hoá hoàn toàn RTCPeerConnection nếu trang không dùng WebRTC cho voice/video:
```javascript
delete window.RTCPeerConnection;
delete window.webkitRTCPeerConnection;
delete window.RTCSessionDescription;
delete window.RTCIceCandidate;
Object.defineProperty(window, 'RTCPeerConnection', { get: () => undefined });
```

---

## 2. Kỷ Luật Geo-Safety Cho Tài Khoản Google Nuôi Trên GPM (User Invariant)
- **Quy tắc bất biến:** Tài khoản Google/Gmail đã được nuôi trên IP VN (hoặc proxy 4G VN) **CẤM TUYỆT ĐỐI** chuyển đột ngột sang IP US / IP ngoại để đăng nhập dịch vụ bên thứ ba.
- **Hậu quả:** Google AI risk engine phát hiện phiên đăng nhập lệch vị trí địa lý đột ngột (từ VN sang US/EU) -> Kích hoạt ngay Security Checkpoint (bắt xác minh số điện thoại, khóa tạm thời hoặc văng cookie nuôi).
- **Quy trình chuẩn khi cần OAuth Google cho dịch vụ quốc tế:**
  1. Giữ nguyên profile GPM chạy trên đúng IP/Proxy VN nguyên bản của tài khoản Google đó.
  2. Truy cập trang đích / OAuth service trên chính IP VN đó (hầu hết các trang SaaS quốc tế như Lexmount, HuggingFace... không chặn IP VN ở cổng đăng ký).
  3. Chỉ có môi trường thực thi / worker / container phía sau mới cần chạy trên hạ tầng US.

---

## 3. Nhận Diện Cloud Browser Sandbox Bị Khóa Đăng Ký (`signup_disabled`)
Khi có các đợt bùng nổ token/airdrop (như Muse AI 1B token), các nền tảng Cloud Browser Sandbox (ví dụ `browser.lexmount.com/playground`):
- Có thể âm thầm tắt cổng đăng ký tài khoản mới ở backend.
- Phía Google OAuth vẫn hoàn tất consent bình thường, nhưng khi redirect về callback URL sẽ trả về:
  `https://browser.lexmount.com/auth/error?callbackUrl=...&error=signup_disabled`
- **Xử lý:** Khi gặp mã lỗi `error=signup_disabled`, dừng ngay việc tạo thêm tài khoản mới và báo cáo trạng thái dịch vụ đã đóng đăng ký công khai.

---

## 4. Phân Biệt IP ASN Datacenter vs Residential & Bẫy Proxy Free / VPN Extension
- **Bẫy VPN Extension Miễn Phí (TouchVPN, UrbanVPN, WARP):**
  * Các extension VPN miễn phí KHÔNG phải là rotating residential proxy. Chúng dùng các gateway cố định (Pango, GTHost, Cloudflare, Choopa).
  * Tất cả các gateway này đều có ASN đăng ký thuộc nhóm **Datacenter/Hosting/VPN**.
  * Các dịch vụ có risk engine khắt khe (Meta SSO, Muse AI, TikTok): Kiểm tra trực tiếp ASN database. Khi phát hiện IP Datacenter, hệ thống lập tức chặn cổng chính hoặc đẩy vào danh sách chờ khu vực (Regional Waitlist), bất kể IP đó định vị địa lý ở US và đã spoof WebRTC sạch sẽ.
- **Bẫy SOCKS5 Proxy Công Cộng (ProxyScrape, Free Proxy Lists):**
  * Phần lớn SOCKS5 proxy công cộng quét được trên mạng đều dính lỗi can thiệp SSL (MITM with self-signed certificate, gây lỗi `CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain`) hoặc timeout khi bắt tay TLS 443.
  * Tuyệt đối không mất thời gian scan proxy free công cộng cho các tác vụ login Meta/Google SSO. Bắt buộc phải dùng **Residential Proxy (IP Dân cư)** có xác thực user/pass.

---

## 5. Phân Biệt "AI Proxy" (OmniRoute/9Router) vs "Network Egress Proxy" (SOCKS5/Residential)
- **Bẫy hiểu nhầm khái niệm:** Trong các hệ thống điều phối AI (như OmniRoute / 9Router / CLIProxyAPI), các mục mang tên "Proxy / Reverse Proxy / Proxy Pools" phục vụ mục đích:
  1. *AI Reverse Proxy:* Cổng trung gian chuyển tiếp định dạng gọi API LLM (Claude, OpenAI, Gemini).
  2. *Proxy Pools in OmniRoute:* Danh sách IP do người dùng tự nhập để xoay vòng tránh rate-limit khi gọi API LLM, **không phải** dịch vụ cấp sẵn proxy duyệt web US miễn phí.
- Khi cần vượt geoblock (Meta, Muse AI, TikTok), **không tìm kiếm proxy trong OmniRoute/9Router** mà phải cấu hình Network Egress Proxy (SOCKS5 Residential) cấp trực tiếp vào GPM/Playwright.

---

## 6. Kỷ Luật Thử Nghiệm Đăng Ký Tránh Tiêu Hao Tài Khoản Farm (Temp Mail First)
- Khi thử nghiệm vượt rào cản địa lý (geo-fence) hoặc đăng ký dịch vụ mới chưa rõ tỷ lệ thành công:
  * **CẤM TUYỆT ĐỐI** dùng email thật, tài khoản Gmail/Hotmail nuôi trong farm hoặc tài khoản cá nhân của User để test mò mẫm.
  * BẮT BUỘC sử dụng disposable temporary email tự động qua API (ví dụ `tempmail.plus` với domain `@fextemp.com`) để sinh email ngẫu nhiên và tự động đọc mã OTP qua REST API.
  * Chỉ khi luồng đăng ký và redeem code đã được xác minh thành công (VERIFIED_SUCCESS) trên temp mail mới chuyển sang gắn tài khoản chính thức.
  * Thông báo rõ ràng cho User ngay từ đầu để tránh gây hoang mang, hiểu lầm là đã "tiêu tốn tài khoản" của farm.

---

## 7. Bẫy Desync Giữa GPM Profile Proxy API vs Extension VPN Trong Trình Duyệt
- **Nguyên nhân sâu xa:** Khi một profile GPM được tạo với cấu hình mạng Direct (không điền proxy):
  * Launcher của GPM tự động lấy IP thật của host máy tính (ví dụ Viettel VN) nạp vào cờ khởi động `--web-rtc-data-json="{\"mode\":\"real\",\"publicIP\":\"<IP_VN>\"}"`.
  * Nếu agent hoặc user cài thêm extension VPN (TouchVPN, UrbanVPN) vào profile đó để fake IP sang US/EU:
    - Traffic HTTP/HTTPS được extension bẻ sang IP ngoại.
    - Nhưng ở tầng Chromium core, STUN/WebRTC engine vẫn gửi đi IP VN đã bị bake cứng từ lúc boot!
- **Giải pháp chuẩn:** BẮT BUỘC cập nhật proxy trực tiếp vào GPM qua API trước khi start profile:
  ```bash
  POST http://127.0.0.1:19995/api/v3/profiles/update/<profile_id>
  Body: {"raw_proxy": "socks5://user:pass@host:port"}
  ```
  Khi GPM thấy profile có `raw_proxy`, nó sẽ tự động tính toán spoof WebRTC, múi giờ, định vị và WebGL đồng bộ, loại bỏ hoàn toàn tình trạng "lệch pha" giữa HTTP và WebRTC.

---

## 8. Bẫy Tự Động Hóa Đăng Nhập Facebook OAuth Để Xác Minh Tuổi (Age Verification)
- **Cơ chế phòng thủ của Facebook Web:** Trên form đăng nhập web hiện đại của Facebook (`facebook.com/login` hoặc cửa sổ OAuth popup `fxauth`):
  * Facebook áp dụng mã hóa mật khẩu client-side (`enc_password`) kết hợp phát hiện tương tác tự động.
  * Khi script Playwright/Selenium tự điền credentials và trigger `submit` bằng `form.requestSubmit()` hoặc click synthetic, Facebook thường xuyên chặn và báo giả: *"Bạn đã nhập sai thông tin đăng nhập"* (hoặc treo timeout) dù UID, Pass và 2FA hoàn toàn chính xác.
- **Quy tắc điều phối an toàn:**
  * **CẤM TUYỆT ĐỐI** chạy vòng lặp ngầm (loop) thử lại liên tục trên form đăng nhập Facebook khi gặp lỗi sai thông tin hoặc timeout. Việc này dễ làm chết tài khoản (checkpoint 956/282) và gây nghẽn phiên điều phối.
  * **Giải pháp 1 (Ưu tiên):** Import sẵn cookie phiên live đầy đủ (`c_user`, `xs`, `fr`, `datr`) vào browser context trước khi mở URL OAuth popup. Khi popup mở ra, nó sẽ nhận diện phiên đã đăng nhập và chỉ hiện nút *"Tiếp tục dưới tên [Tên]"*.
  * **Giải pháp 2 (Handoff kịp thời):** Nếu không có cookie live hợp lệ hoặc Facebook bắt đăng nhập lại từ đầu, dừng script và thông báo User mở cửa sổ GPM để tự đăng nhập tay (30 giây), tránh để tool brute-force gây bực dọc cho User.
