# Mandatory GPM Login Before WAIT_7D & False-Positive Challenge Pitfalls (2026-10-15)

## 1. Cấm Tuyệt Đối Ngâm 7D Ảo Khi Chưa Login Hotmail Trên GPM Profile
- **User Frustration Signal:** *"Admin đéo đăng nhập đc dám đem đi ngâm 7d đkm"*.
- **Bản chất lỗi kiến trúc:**
  - Trong quá khứ, khi tài khoản có sẵn OAuth Refresh Token (Graph API) trong file mua, script tự động nhảy cóc bỏ qua `HOTMAIL_LOGIN` để gọi script reg ChatGPT trực tiếp qua Graph API, sau đó đẩy tài khoản vào `WAIT_7D`.
  - **Hậu quả tai hại:** Profile GPM hoàn toàn chưa từng mở trình duyệt để đăng nhập bằng mật khẩu, không hề có cookie, session hay storage của Microsoft. Đến hạn 7 ngày sau khi chuyển sang `CHANGE_INFO` (đổi pass & thêm mail khôi phục trên web), luồng bảo mật bắt buộc phải có session trình duyệt -> toàn bộ sẽ sập và hỏng 100%.
- **Quy tắc bất biến:**
  1. Mọi tài khoản Hotmail (kể cả đã có token Graph API hay đã từng reg ChatGPT) **BẮT BUỘC phải chạy qua `HOTMAIL_LOGIN` trên GPMLogin** để lưu cookie/session thật sự.
  2. Tuyệt đối không đưa nick vào `WAIT_7D` nếu chưa có `hotmail_login_at` thực tế trên GPM.
  3. Khi phát hiện nick bị ngâm ảo: BẮT BUỘC hạ về `HOTMAIL_LOGIN`/`PENDING`, giữ lại `chatgpt_registered_at` để khi login GPM thành công thì tự động nhảy thẳng vào `WAIT_7D` thực tế.

## 2. Bẫy False-Positive Nhận Diện Nhầm "Bảo Vệ Tài Khoản" Trên Trang Chủ Microsoft
- **Hiện tượng:** Tài khoản Hotmail đã đăng nhập thành công vào đến `https://account.microsoft.com` (hiển thị Avatar, tên tài khoản, nút quản lý), nhưng script đăng nhập vẫn báo `status: BLOCKED` với lỗi `Standard challenge requested: PROTECT_ACCOUNT_VERIFICATION`. Profile bị đưa vào Cooldown 48h, đồng thời port proxy bị khóa 24h làm nghẽn toàn bộ máy đó.
- **Root Cause:**
  - Script quét toàn bộ body text sau login:
    ```python
    page_text = page.inner_text("body").lower()
    if "help us protect your account" in page_text or "bảo vệ tài khoản" in page_text:
        is_challenge = True
        challenge_reason = "PROTECT_ACCOUNT_VERIFICATION"
    ```
  - Trang chủ `account.microsoft.com` tiếng Việt luôn có card bảo mật tiêu chuẩn: *"Bảo mật: Cập nhật thông tin để giúp bảo vệ tài khoản của bạn"* kèm modal Cookie Consent.
  - Chuỗi `"bảo vệ tài khoản"` khớp với card giới thiệu của trang chủ, script tưởng lầm là trang checkpoint OTP/challenge nên tự đánh trượt và return `BLOCKED`.
- **Quy tắc phòng ngừa:**
  1. **Tách biệt kiểm tra URL:** Một khi URL đã là `account.microsoft.com` hoặc `outlook.live.com` (không phải form login), tài khoản đã login thành công 100%. CẤM quét chuỗi `"bảo vệ tài khoản"` trên body trang này.
  2. Substring challenge chỉ được kiểm tra khi URL còn ở `login.live.com` hoặc các path checkpoint thực sự (`/proofs/`, `/identity/`, `/Abuse`).

## 3. Đối Soát Phân Bổ Proxy Port: Kibe vs Admin
- **Farm Kibe (Máy 1–80):** 39 port proxy (`5101`–`5180` trong `PROXYgandienthoai.xlsx`).
- **Farm Admin (Máy 201–280):** 28 port proxy (`10008`–`10035`).
- **CẤM TUYỆT ĐỐI** ngộ nhận Admin nhiều port hơn Kibe. Năng suất cao trước đây của Admin là do nhảy cóc qua Graph API chứ không phải do hạ tầng mạng.
