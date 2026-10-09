# GPM vs Android Native Hotmail Workflow Boundary & OAuth Preflight

## Bối cảnh và Phân định ranh giới (Domain Boundary)
Trong hệ thống Taadaa Farm, tự động hóa tài khoản Hotmail/Outlook được phân tách rạch ròi giữa 2 môi trường:

1. **Android Farm (`flows/hotmail_login.py`, `scripts/hotmail_list_runner.py`)**:
   - Chạy trên thiết bị thật (Samsung S7 qua ADB / ATX agent).
   - Đăng nhập bằng ứng dụng native `com.microsoft.office.outlook`.
   - Sử dụng OAuth Token (refresh token / client ID) để đọc mail OTP trực tiếp qua Graph API (`scripts/test_graph_token.py`).

2. **GPM Browser / PC (`scripts/gpm_change_hotmail_security.py`)**:
   - Chạy trên GPMLogin profile (Chromium qua Playwright CDP).
   - Đăng nhập bằng form truyền thống (email + mật khẩu) trên `https://login.live.com` để đổi mật khẩu và thu hồi phiên đăng nhập (`account.live.com/proofs/manage/additional`).
   - **LƯU Ý QUAN TRỌNG**: Hiện tại **CHƯA CÓ** luồng canonical để dùng OAuth token (refresh_token/access_token) inject trực tiếp thành web session cookie trên GPM browser cho Hotmail/Microsoft.

## Quy tắc Kiểm tra Canonical Flow (Preflight Guardrail)
Khi nhận task yêu cầu chạy batch GPM Hotmail OAuth:
- Luôn kiểm tra xem luồng canonical Microsoft OAuth token injection vào browser session có tồn tại thực sự hay không.
- Nếu không có script chính thức trong repo (không tự chế script ad-hoc khi task yêu cầu tuân thủ canonical flow), phải **FAIL-CLOSED** và báo `BLOCKED` kèm bằng chứng đối soát chính xác.
- Tuyệt đối không tạo profile rác trên GPM trước khi kiểm chứng sự tồn tại của luồng thực thi đích.

## Danh bạ nguồn dữ liệu chuẩn (Source of Truth)
- Danh sách tài khoản: `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (Sheet `'Tài Khoản'`).
- Mapping Proxy thiết bị/máy: `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (Sheet `'Proxy'`).
- Local GPM API v3: `http://127.0.0.1:19995/api/v3` (`/server/status`, `/browser-profiles`, `/profiles/start/{id}`, `/profiles/stop/{id}`).
