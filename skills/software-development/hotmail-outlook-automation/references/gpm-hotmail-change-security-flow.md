# Quy trình Đổi bảo mật Hotmail qua GPM CDP & Re-login Session (GPM Hotmail Security Pipeline)

## 1. Bản chất & Rủi ro Temp Mail của Bên Bán (Getnada, fvia, inboxes, smvmail)
- **Rủi ro lớn nhất (Bên bán back nick):** Temp mail của shop là hộp thư công cộng không có mật khẩu. Bất kỳ ai biết tên hộp thư đều có thể bấm quên mật khẩu và đọc OTP trên web tempmail để lấy lại tài khoản.
- **Rủi ro domain die:** Các domain tempmail thường xuyên bị Microsoft đưa vào blacklist hoặc nhà cung cấp xóa sổ. Khi Microsoft yêu cầu OTP gửi về mail đó mà domain đã chết thì tài khoản bị khóa vĩnh viễn.
- **Nguyên tắc xử lý:**
  - Nếu Microsoft cho gỡ không đòi hỏi OTP phức tạp: Gỡ sạch bóng các mail khôi phục domain lạ (`getnada`, `fvia`, `inboxes`, `smvmail`...).
  - Tuyệt đối không add mail cá nhân của Operator (để sau này bán kèm nick TikTok cho khách không bị dính info chủ cũ).
  - Nếu Microsoft chặn không cho gỡ hoặc bắt thêm mail mới: Bỏ qua bước gỡ, chỉ đổi pass mạnh + Sign out everywhere để revoke toàn bộ OAuth token và session của shop.

## 2. Chuỗi 4 bước chuẩn thực thi trên GPM CDP (`gpm_change_hotmail_security.py`)
1. **Bước 1 — Đổi mật khẩu mạnh mới (`https://account.live.com/password/change`):**
   - Đăng nhập bằng pass cũ (nếu chưa có session).
   - Điền mật khẩu mới 14 ký tự (`gen_strong_password()`), submit lưu mật khẩu.
   - Ngay lập tức vô hiệu hóa (revoke) toàn bộ Refresh Token cũ của shop.
2. **Bước 2 — Quản lý bảo mật & Gỡ mail khôi phục rác (`https://account.live.com/proofs/manage/additional`):**
   - Rà soát các mục xác minh danh tính. Nếu phát hiện keyword untrusted (`getnada`, `fvia`, `inboxes`...), thử click Xóa (Remove) an toàn.
   - Nếu không có mail khôi phục rác (tài khoản trắng thông tin): ghi nhận log an toàn và tiếp tục.
3. **Bước 3 — Sign out everywhere (Đăng xuất khỏi mọi nơi):**
   - Cuộn cuối trang `account.live.com/proofs/manage/additional`.
   - Tìm selector `a:has-text('Đăng xuất khỏi mọi nơi')` / `#sign-out-everywhere-button`.
   - Bấm xác nhận đăng xuất để đá sạch toàn bộ session trình duyệt cũ của shop trên mọi thiết bị.
4. **Bước 4 — Đăng nhập lại bằng Mật khẩu mới trên GPM Profile (`https://account.microsoft.com/profile`):**
   - Điều hướng tới trang Profile để kích hoạt form đăng nhập lại sau khi toàn bộ session cũ bị revoke.
   - Điền email + mật khẩu mới, xử lý Cookie Consent banner ("Chấp nhận").
   - Bấm Có/Yes tại màn hình KMSI ("Duy trì đăng nhập?") để lưu cookie session sống lâu dài vào profile GPM.
   - Chờ `networkidle` và chụp ảnh xác nhận trang Profile hiển thị tên/thông tin tài khoản đầy đủ.
5. **Bước 5 — Đồng bộ Excel & State file:**
   - Cập nhật pass mới vào Cột G (`PASS MAIL`) trong `taikhoan_dat_v2_updated .xlsx`.
   - Ghi nhận `changed_at` vào `hotmail_changed_tracker.json`.

## 3. Pitfalls kỹ thuật trong Supervisor điều phối GPM (`batch_gpm_5profiles_supervisor.py`)
- **Fallback tính tuổi ngâm $\ge 7$ ngày (`WAIT_7D`):**
  - Tài khoản import từ OAuth token không có trường `hotmail_login_at` (giá trị `None`).
  - Supervisor bắt buộc phải fallback: `anchor = hotmail_login_at or codex_oauth_at or chatgpt_registered_at`. Nếu không có fallback này, toàn bộ nick đủ tuổi sẽ bị kẹt vô tận ở `WAIT_7D`.
- **Phân trang GPM profiles khi tìm kiếm (`find_gpm_profile_for_account`):**
  - GPM Local API phân trang 100 profiles/page. Khi hệ thống có >600 profiles, gọi 1 page đơn lẻ sẽ bỏ sót profiles nằm ở page 2+.
  - Bắt buộc lặp qua `page=1, 2, ...` với `per_page=100` cho đến khi hết danh sách.
  - Luôn ưu tiên match chính xác email nằm trong tên profile (`f"{machine:02d} - {email} - {port}"`) trước khi fallback match theo prefix số máy.
