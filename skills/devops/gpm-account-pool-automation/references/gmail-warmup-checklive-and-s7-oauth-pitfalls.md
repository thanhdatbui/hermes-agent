# Quy Chuẩn & Cạm Bẫy Vận Hành Warmup Gmail, Check Live & Google OAuth Trên Farm

## 1. Bản Chất Module Newsletter Warmup (Inbound Activity Trap)
- **Cạm bẫy False Positive (HTTP 200 Giả):**
  - Gửi request HTTP thuần (`urllib.request`, `requests`) bằng POST tới các endpoint Newsletter (Cooperpress, Node Weekly, Hacker Newsletter) thường nhận về HTTP `200 OK`.
  - Thực chất response `200` là trang HTML thử thách của **Cloudflare Turnstile** ("Just a moment..."), form đăng ký chưa hề submit vào backend. Không có bất kỳ email xác nhận nào được gửi về hộp thư.
  - Hậu quả: Script báo `✓ [WARMUP_INBOX] Đã kích hoạt 4 dịch vụ`, nhưng vào hộp thư Gmail thật trên thiết bị hoàn toàn trống trơn.
- **Đặc tính Double Opt-in & Delay:**
  - Ngay cả khi form Mailchimp/Substack submit thành công (nhận thông báo `Please confirm your email`), hệ thống mailer của họ phân phối thư theo hàng đợi (queue), có độ trễ từ 15-30 phút hoặc lâu hơn.
  - Các thư này thường bị Google xếp vào tab Quảng cáo (Promotions) hoặc Xã hội (Social), không rớt ngay vào tab Chính (Primary).
- **Quy tắc vàng:**
  - Không dựa vào HTTP POST thuần để warmup hòm thư nếu dịch vụ nằm sau Cloudflare/DataDome.
  - Không tự viết script SMTP bắn mail nội bộ chéo giữa các tài khoản farm (ví dụ dùng `thanhdatbui1995` gửi hàng loạt tới Gmail mới reg): Google Anti-Abuse AI nhận diện ngay cấu trúc mạng lưới farm (Cluster Inter-linking) và cờ liên đới làm chết cả chùm.
  - Chiến lược tối ưu nhất: **Ngâm tự nhiên 24h-48h trên máy S7** (chỉ cần 1 thư chào mừng mặc định của Google) để hoàn tất telemetry thiết bị trước khi đưa lên GPM hoặc bật 2FA.

## 2. Check Live Gmail Qua checkmail.live Bắt Buộc Có Session / API Key
- **Cơ chế hoạt động của checkmail.live:**
  - Nút `#btn-check` gọi hàm `CheckEmail()` trong mã nguồn trang.
  - Hàm này kiểm tra nghiêm ngặt:
    ```javascript
    const api_key = $('#api-key').val();
    if (!api_key) {
        alert('You are not logged in');
        return;
    }
    ```
  - Nếu mở trình duyệt sạch (không đăng nhập) và gọi `page.click('#btn-check')`, web hoàn toàn không chạy, các bộ đếm Live/Die/Verify đều đứng ở 0.
- **Giải pháp chuẩn:**
  - Sử dụng script chuẩn đã được tích hợp trong farm: `D:\Taadaa\GPM auto\scripts\run_checkmail_kibe_farm.py`.
  - Hàm `ensure_logged_in_page(context)` tự động kiểm tra `api-key`, nếu session hết hạn sẽ tự đăng ký tài khoản tạm / đăng nhập qua proxy Mobi 4G để lấy API key trước khi kiểm tra danh sách email.
  - Khi tài khoản Gmail bị Google yêu cầu xác minh số điện thoại (`challenge/iap`), checkmail.live sẽ phân loại chính xác là `DIE`. Cần lập tức dọn khỏi `gmail_clean_v2.xlsx`.

## 3. Rào Cản Google OAuth Trên Samsung S7 (Android 8.0)
- **Lỗi Bắt Chéo Intent (Account Chooser Crash / Loop):**
  - Khi mở Chrome trên Android 8.0 vào `chatgpt.com/auth/login` và bấm *"Tiếp tục với Google"*:
    - Google Play Services trên Android 8.0 gọi giao diện Account Chooser hệ thống.
    - Khi người dùng bấm vào tài khoản Google mong muốn, thay vì trả token OAuth về lại cho Chrome, hệ thống Android 8.0 lại đá văng người dùng về màn hình Cài đặt hệ thống: `com.android.settings/com.android.settings.Settings$UserAndAccountDashboardActivity`.
    - Trình duyệt Chrome bị kẹt ở URL ủy quyền `auth.openai.com/api/accounts/authorize?...` với màn hình trắng xóa (blank page) hoặc thông báo `client_id_not_found_in_session` do cookie phiên bị đứt gãy.
- **Thao Tác Gõ Mật Khẩu Bằng ADB:**
  - Khi mật khẩu chứa ký tự đặc biệt như dấu chấm than (`!`), tuyệt đối không bắn raw string qua `adb shell input text` vì bash host hoặc shell Android sẽ nuốt hoặc biến thành `\!`.
  - Luôn sử dụng hàm `human_type()` chuẩn của repo (gõ từng ký tự với delay và escape tập `\$&*();'\"<>|~^!?`).
- **Khuyến nghị vận hành:**
  - Không cố gắng tự động hóa luồng "Continue with Google" vào các bên thứ 3 phức tạp (ChatGPT, Claude...) trực tiếp trên thiết bị S7 cũ.
  - Chờ tài khoản ngâm đủ 24h-48h trên S7, sau đó đưa lên GPM Profile trên PC có proxy tương ứng để thực hiện Google OAuth một cách ổn định và an toàn.
