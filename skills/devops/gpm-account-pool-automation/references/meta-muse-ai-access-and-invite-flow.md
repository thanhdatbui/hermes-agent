# Meta Muse AI — Đăng ký, Truy cập & Nhập Invite Code

## 1. Bối cảnh

Muse AI (`muse.ai`) là sản phẩm AI agent của Meta, yêu cầu:
- Tài khoản Meta hợp lệ (login qua Facebook/Instagram OAuth hoặc đăng ký email).
- **IP US hợp lệ:** Muse chỉ available ở Hoa Kỳ và một số khu vực. Dùng IP VPN Extension Datacenter (TouchVPN, SetupVPN...) bị phát hiện và bị kẹt ở màn hình Waitlist.

## 2. Luồng đăng ký tài khoản Meta mới bằng temp-email (Cập nhật 2026-10-23)

### Bước 0: Tránh bẫy chuyển hướng Instagram SSO / Facebook Redirect Cycle
- Nếu profile có session/cookie cũ, truy cập `https://muse.ai/` sẽ bị redirect 307 `auth.muse.ai/aymh/` -> `facebook.com/aymh/redirect-cycle/` -> `instagram.com/#`.
- **Xử lý:** Bắt buộc gọi `context.clear_cookies()` trước khi `page.goto('https://muse.ai/', wait_until='networkidle')` để tải trang chủ sạch của Muse AI.

### Bước 1: Điền email, nhận OTP
- Mở `https://muse.ai/` trên trình duyệt antidetect (GPM/Chromium).
- Điền email vào ô `input` (placeholder *"Số di động hoặc email bắt buộc"*), bấm **Tiếp tục** (`div[role="button"]:has-text("Tiếp tục")`).
- Meta gửi mã xác nhận 6 chữ số từ `support@meta.com` (tiêu đề *"Xác nhận email cho Tài khoản Meta mới"*).
- Bóc OTP 6 số từ API TempMail.Plus:
  ```bash
  curl "https://tempmail.plus/api/mails?email=<user>@fextemp.com&limit=5"
  curl "https://tempmail.plus/api/mails/<mail_id>?email=<user>@fextemp.com"
  # Trích chuỗi regex r'\b(\d{6})\b': "Mã xác nhận 460215"
  ```

### Bước 2: Điền OTP và bẫy nút "Xác nhận"
- Điền OTP 6 số vào ô input `muse.ai`.
- Bấm nút **Xác nhận** (`button[type="submit"]:has-text("Xác nhận")`).
- API `POST https://muse.ai/api/auth/native/confirm-otp` trả về `HTTP 200 OK`:
  `{"registration_state":"completion_required","tos":...}`.

### Bước 3: Khai báo ngày sinh & Cạm bẫy Modal Picker "OK"
- Giao diện chuyển sang *"Ngày sinh của bạn là khi nào?"* với 3 dropdown: Ngày, Tháng, Năm.
- **Bẫy UI 1 - Năm mặc định:** Mặc định năm là `2026` (chưa đủ 18 tuổi) nên nút Xác nhận bị mờ (disabled). Bắt buộc `select_option('1997')` hoặc năm sinh < 2008.
- **Bẫy UI 2 - Overlay Picker:** Khi click dropdown trên Chromium, xuất hiện modal/overlay nút `OK` (`button:has-text("OK")`) che khuất form submit. Bắt buộc click nút `OK` này để đóng picker trước khi bấm nút `Xác nhận` submit ngày sinh.

### Bước 4: Chặn IP Datacenter tại `register-completion` (Lỗi 403 csrfFailed)
- Khi submit ngày sinh, client gửi request:
  `POST https://muse.ai/api/auth/native/register-completion`
  Payload: `{"date_of_birth":"1997-10-23","tos_content_version":"ntm_create_account:default_v1_meta_account_v2+docs_v1","remember_device":true}`
- **Bản chất lỗi "Phiên đăng nhập của bạn đã hết hạn":**
  Nếu dùng IP Datacenter (như Webshare ASN 36352 Colocrossing), Meta Risk Engine trả về:
  `HTTP 403 Forbidden`
  `{"type":"csrfFailed","title":"Request blocked","detail":"Refresh the page and try again.","status":403}`
  Và giao diện frontend ngụy trang lỗi thành dòng đỏ: *"Phiên đăng nhập của bạn đã hết hạn. Hãy thử lại."*
- Đây KHÔNG phải lỗi hết hạn session thực tế, mà là cờ chặn IP Datacenter của Meta. Bắt buộc phải dùng IP US Residential sạch (AT&T, Verizon Business) hoặc Cloud Browser thật như Lexmount.

### Bước 3: Màn hình /access — hai trạng thái

| IP Type | Kết quả |
|---|---|
| IP Residential US thật | Hiện giao diện chat đầy đủ hoặc màn hình nhập Invite Code (`Do you have an invite code?`) |
| IP VPN Datacenter / Extension VPN | Hiện thông báo `"Muse hiện chưa có ở quốc gia hoặc khu vực của bạn"` — Waitlist |

Khi bị Waitlist: chỉ có nút **Tham gia danh sách chờ**. **Không có ô nhập Invite Code.**

## 3. Invite Codes đang lưu hành (trích từ bài chia sẻ cộng đồng)

| Mã | Nguồn | Ghi chú |
|---|---|---|
| `6ZJFNW` | Trần Thành Đạt (bài hướng dẫn Lexmount) | Dùng trong Lexmount Cloud Browser |
| `VIIG65` | Du Lương (Codex VN group) | Chữ `I` viết hoa — không phải `1` |
| `HWPB0W` | Phạm Cường (comment cùng bài) | Ký tự thứ 5 là số `0`, không phải `O` |

**Mã có thể đã hết hoặc bị revoke.** Muse AI API trả về response `{success: false, reason: "used_up" | "revoked" | "invalid"}`.

## 4. Cách nhập Invite Code đúng

Khi trên IP US Residential (không bị chặn), vào `muse.ai/access`:
1. Màn hình hiển thị giao diện chat đầy đủ (thanh sidebar, composer...).
2. Vào **Settings → Redeem Code** → nhập mã invite.
3. Hoặc navigate trực tiếp tới route `hatch://redeem_invite_code` (deep-link nội bộ — mở từ native app, không hoạt động trên web browser thông thường).

## 5. Phương án thay thế khi không có Residential Proxy US

Theo tác giả bài hướng dẫn gốc:
- **Lexmount Playground** (`https://browser.lexmount.com/playground`) — Cloud Browser chạy trên server US thật. Đăng nhập bằng GitHub để nhận session. Guest trial đã đóng (2026-10-06), cần tài khoản Lexmount hữu hiệu (stargazer tier miễn phí hoặc paid plan).
- Nếu không có cả hai → đăng ký waitlist bằng tài khoản Meta vừa tạo, đợi Meta mở rộng khu vực.

## 6. Pitfalls

- **VPN Extension ≠ Residential US:** TouchVPN, SetupVPN dùng IP Datacenter (ASN GTHost, Akamai...). Meta phát hiện và chặn hiển thị Invite Code form.
- **GPM profile có thể restart và mất CDP port:** Sau khi tắt Chrome GPM, CDP reconnect cần bind lại port từ netstat trước khi gọi playwright.connect_over_cdp.
- **Invite code flow không accessible từ web khi bị Waitlist:** Dù inject cookie đúng, Meta SSO callback thành công, nếu IP không pass check thì redirect luôn về `/access` Waitlist. Không có workaround phía client.
