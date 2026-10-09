# GPM Hotmail Lifecycle Supervisor & Security Flow

## 1. Vòng đời Hotmail trên GPM Profile
`HOTMAIL_LOGIN -> CHATGPT_REG -> CODEX_OAUTH -> WAIT_7D -> CHANGE_INFO -> DONE`

## 2. Các điểm nghẽn thường gặp & Cách giải quyết
1. **Kẹt ngâm 7 ngày (`WAIT_7D`):**
   - Tài khoản đi thẳng từ token OAuth sẽ không có `hotmail_login_at`.
   - Supervisor bắt buộc fallback: `anchor = hotmail_login_at or codex_oauth_at or chatgpt_registered_at`.
2. **Tìm Profile GPM phân trang:**
   - Khi kho profile GPM lớn (>600 profile), bắt buộc duyệt `page=1..N` với `per_page=100`.
   - Tìm kiếm theo email chính xác thay vì chỉ prefix số máy (`{machine:02d} - `) để tránh nhầm sang profile Gmail của cùng máy.
3. **Quy trình Change Info 4 bước:**
   - Bước 1: Đổi mật khẩu mạnh 14 ký tự (revoke token cũ).
   - Bước 2: Quét & gỡ mail khôi phục rác của shop (Getnada, fvia, inboxes, smvmail) nếu không bị Microsoft ép.
   - Bước 3: Sign out everywhere (đá văng mọi phiên cũ).
   - Bước 4: Đăng nhập lại bằng mật khẩu mới trên GPM profile (`account.microsoft.com/profile`) + KMSI Yes để lưu session cookie sống.
