# ChatGPT-Web Pool Feeder: Hotmail Direct vs Gmail SSO Triage

## Bối cảnh & Hiện tượng
Khi cron hoặc watchdog nạp/cứu tài khoản ChatGPT-Web (`cron_auto_feed_chatgpt_pool.py`) báo lỗi diện rộng:
`Validate fail: EMPTY_SESSION_TOKEN`

## Nguyên nhân cốt lõi (Root Cause)
1. **Lệch luồng xác thực (Authentication Flow Mismatch):**
   - Script tự động hoá mặc định click `Continue with Google` (Google SSO) để lấy cookie `session-token`.
   - Tuy nhiên trong tập ứng viên lấy từ GPM Profiles (`profile_data.db`), có cả tài khoản **Hotmail** lẫn **Gmail**.
   - Đối với tài khoản **Hotmail**: Tài khoản vốn được đăng ký bằng phương thức Direct Email + Mật khẩu. Khi click `Continue with Google`, trình duyệt bị redirect về `accounts.google.com/v3/signin/identifier` yêu cầu nhập tài khoản Google. Quá trình này không thể auto-pick account và dẫn đến timeout 35-45s, không lấy được `session-token` (trả về rỗng).
   - Nếu danh sách ứng viên ưu tiên Hotmail trước (`cand_h + cand_g`), toàn bộ worker sẽ bị kẹt luân phiên trên màn hình Google Sign-in.

2. **Cơ chế nạp chuẩn theo từng loại tài khoản:**
   - **Tài khoản Gmail**: Sử dụng luồng Google SSO (`Continue with Google` -> chọn profile Google trên Google Chooser -> redirect callback về `chatgpt.com`).
   - **Tài khoản Hotmail**: Tuyệt đối KHÔNG click Google SSO. Phải sử dụng luồng Direct Login (nhập email Hotmail -> nhập mật khẩu -> nếu có OTP thì lấy qua Microsoft Graph API hoặc IMAP).

## Giải pháp & Kỷ luật vận hành
1. **Ưu tiên phân tách luồng trong Candidate Picker:**
   - Luôn tách riêng tập ứng viên `cand_g` (Gmail) và `cand_h` (Hotmail).
   - Với các script auto-feed dựa trên Google SSO, chỉ đưa `cand_g` vào xử lý hoặc sắp xếp `(cand_g + cand_h)` để không làm nghẽn toàn bộ worker pool bởi tài khoản Hotmail.
   - Tuyệt đối không dùng chung một hàm login Google SSO cho tài khoản Hotmail.
2. **Xác minh trực quan (Gate 6):**
   - Mở screenshot debug bằng `browser_vision` để phân biệt chính xác màn hình đang dừng là:
     * `accounts.google.com/v3/signin/identifier` (bị ép nhập Google Account -> sai luồng).
     * Cloudflare Turnstile / Sentinel (cần chờ hoặc giải captcha).
     * Màn hình chính đã đăng nhập (`data-testid="profile-button"`).
