# Chẩn Đoán Phân Biệt: OAuth Revocation vs Session Die vs Tài Sản Gmail Trên GPM Pool

## 1. Bản chất phân tầng lỗi "Revoke vĩnh viễn" (unrecoverable_refresh_error)
Khi OmniRoute báo lỗi:
`Refresh token rejected (unrecoverable_refresh_error). Please re-authenticate this account.` (Google OAuth `invalid_grant`)

BẮT BUỘC phân biệt rõ 3 tầng độc lập, KHÔNG ĐƯỢC đánh đồng:
1. **Tầng Ủy quyền Ứng dụng (App OAuth Token):** Chỉ có liên kết giữa OmniRoute/Antigravity App và tài khoản Google bị thu hồi (do quá hạn, đổi pass, đăng xuất phiên trên web, hoặc Google security policy).
2. **Tầng Phiên Trình duyệt (GPM Chrome Profile Session):** Profile GPM có thể còn lưu cookies đăng nhập Google hoặc đã bị văng ra trang đăng nhập trắng (`/signin/v2/identifier`).
3. **Tầng Tài sản Gốc (Gmail Asset):** Email, mật khẩu và mã 2FA TOTP trong file dữ liệu gốc (`gmail_clean_v2.xlsx`) vẫn còn sống và hợp lệ. Tài khoản KHÔNG bị chết/vô hiệu hóa trừ khi đã được xác nhận DIE qua checklive chính thức.

## 2. Tại sao Watchdog Auto-Healer Báo "Timeout bắt OAuth code"?
Script hồi sinh tự động (`cron_chatgpt_web_pool_watchdog.py`) chỉ thực hiện **Silent OAuth**:
- Giả định: Profile GPM mở lên đã có sẵn session Google đăng nhập trong Chrome. Script chỉ cần điều hướng tới `authUrl`, chọn tài khoản ở Account Chooser và bấm "Cho phép" / "Tiếp tục".
- Thực tế khi lỗi xảy ra:
  - Nếu profile GPM bị văng cookies: Trình duyệt mở ra trang đăng nhập trắng đòi Email / Password / 2FA.
  - Proxy di động 4G / Mikrotik farm có độ trễ lớn (30s - 60s load trang).
  - Timeout cứng 35s trong watchdog khiến script không kịp load hoặc bị kẹt ở form đăng nhập $\rightarrow$ Ghi nhận lỗi sai lệch thành "Timeout bắt OAuth code".

## 3. Quy Trình Vận Hành & Khôi Phục Đúng Chuẩn (Standard Recovery Workflow)
1. **Xác thực trước khi xóa connection:**
   - Kiểm tra `POST /api/providers/:id/test` trên OmniRoute để lấy chẩn đoán chính xác từ upstream.
   - Nếu upstream trả về HTTP 401 / Revoked: Kiểm tra xem tài khoản có nằm trong danh sách `purge-die` hay file live chính thức.
   - Nếu là tài khoản DIE đã purge: Dùng `DELETE /api/providers/:id` để dọn sạch connection rác, tránh làm bẩn báo cáo watchdog.
2. **Đối với tài khoản LIVE nhưng mất session trên GPM:**
   - CẦN đăng nhập lại Google trên profile GPM (nhập pass + giải TOTP 2FA từ `gmail_clean_v2.xlsx`).
   - Sau khi profile GPM có session live, chạy luồng OAuth Antigravity (`/api/oauth/antigravity/authorize` $\rightarrow$ capture code $\rightarrow$ `/api/oauth/antigravity/exchange`) để tái cấp token mới.
3. **Khai thác kho tài khoản dự phòng:**
   - Thường xuyên đối soát giữa `gmail_clean_v2.xlsx` (kho live) và `provider_connections` (OmniRoute) để nạp thêm các tài khoản Gmail đã có profile GPM vào pool Antigravity, tăng redundancy cho farm.
