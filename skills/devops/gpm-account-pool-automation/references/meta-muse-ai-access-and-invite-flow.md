# Meta Muse AI — Đăng ký, Truy cập & Nhập Invite Code

## 1. Bối cảnh

Muse AI (`muse.ai`) là sản phẩm AI agent của Meta, yêu cầu:
- Tài khoản Meta hợp lệ (login qua Facebook/Instagram OAuth hoặc đăng ký email).
- **IP US hợp lệ:** Muse chỉ available ở Hoa Kỳ và một số khu vực. Dùng IP VPN Extension Datacenter (TouchVPN, SetupVPN...) bị phát hiện và bị kẹt ở màn hình Waitlist.

## 2. Luồng đăng ký tài khoản Meta mới bằng temp-email (đã kiểm chứng)

### Bước 1: Điền email, nhận OTP
- Mở `https://muse.ai/` trên trình duyệt đang kết nối IP US Residential.
- Điền email, bấm **Tiếp tục** → Meta gửi OTP về email dạng `Mã xác nhận XXXXXX`.
- Đọc OTP từ API TempMail.Plus:
  ```bash
  curl "https://tempmail.plus/api/mails?email=<user>@fextemp.com&limit=10"
  curl "https://tempmail.plus/api/mails/<mail_id>?email=<user>@fextemp.com"
  # Trích mã trong body: "Mã xác nhận 680556"
  ```
- **Lưu ý `fextemp.com`:** Domain trỏ về `tempmail.plus` backend; API TempMail.Plus nhận mail OK.

### Bước 2: Điền OTP, thiết lập profile
- Form đăng ký tiếp theo yêu cầu: **Tên + Họ** (bắt buộc) và **Ngày sinh** (dropdown Ngày/Tháng/Năm — year mặc định là 2026 nên nút Xác nhận bị disabled). Cần chọn năm sinh < 2008 để nút kích hoạt.
- Sau khi submit, Meta OIDC trả về callback `auth.meta.com/oidc/callback` → redirect vào `https://muse.ai/access`.

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
