# Google Recovery Email Challenge, Unavailable Options & Form-First Automation Invariant

## 1. Triệu chứng & Bối cảnh
Khi tự động hóa đăng nhập Google OAuth (Antigravity, Codex, ChatGPT) qua GPMLogin CDP:
- Màn hình hiển thị: *"Verify it’s you" / "Xác minh danh tính"* kèm danh sách lựa chọn:
  1. `Get a verification code at...` (Nhận mã xác minh tại email...): Bị khóa với chú thích *"Unavailable because of too many attempts. Please try again later."*
  2. `Use another phone or computer to finish signing in`
  3. `Confirm your recovery email` (Xác nhận email khôi phục): Còn khả dụng (có thể được focus/hover sẵn).
  4. `Try another way` (Thử cách khác)

## 2. Các cạm bẫy kỹ thuật (Pitfalls)

### Bẫy 1: Playwright Pointer Intercept trên Option bị khóa
- Khi script tìm kiếm locator theo text candidate `"Get a verification code at"` và gọi `.click(timeout=4000)`:
  Playwright phát hiện element bị container `<li class="...">` che khuất hoặc `aria-disabled="true"`.
  Playwright sẽ retry liên tục và nổ lỗi: `<li ...> intercepts pointer events. Timeout 4000ms exceeded`.
- **Khắc phục**: Trước khi click bất kỳ option nhận mã nào, BẮT BUỘC kiểm tra DOM xem có chứa nhãn `Unavailable because of too many attempts` hoặc `Please try again later` không. Nếu có, lập tức bỏ qua nhánh xin OTP email để không bị nuốt pointer events.

### Bẫy 2: Nghịch đảo thứ tự Form Input vs Option Item (Order-Inversion Trap)
- **Hiện tượng**: Khi trang đã mở form nhập email khôi phục (hoặc tiêu đề trang chứa chuỗi `"Confirm your recovery email"`):
  Nếu script kiểm tra click option (`clicked_opt`) TRƯỚC khi kiểm tra ô nhập (`filled`), câu lệnh `document.querySelectorAll(...)` sẽ match trúng tiêu đề hoặc thẻ bao ngoài, gọi `target.click()` rồi `continue`.
  Hậu quả: Vòng lặp `while` chạy liên tục cho đến khi timeout 120s mà **không bao giờ chạy xuống nhánh điền `recovery_email`**!
- **Kỷ luật "Form-First Invariant"**:
  Luôn luôn kiểm tra và điền ô input (`input[name="knowledgePreregisteredEmailResponse"]`, `input[type="email"]`) **TRƯỚC**.
  Chỉ khi trong DOM không tìm thấy ô nhập email khôi phục thì mới tìm kiếm và click vào container lựa chọn phương thức (`[data-challengeindex]`, `li`, `[role="link"]`).

### Bẫy 3: Nuốt Phone Checkpoint thành "Timeout bắt OAuth code"
- Khi Google yêu cầu nhập số điện thoại (`Enter a phone number to get a text message with a verification code`):
  Nếu code chỉ log rồi `break` ra khỏi vòng lặp bắt `captured_code`, sau vòng lặp script lại gán nhãn chung là `Timeout bắt OAuth code`.
  Điều này khiến người vận hành tưởng nhầm lỗi mạng/OAuth và tiếp tục bấm retry mù, làm tài khoản bị checkpoint nặng hơn.
- **Khắc phục**: Lưu trạng thái lỗi cục bộ `PHONE_CHECKPOINT` khi phát hiện form yêu cầu SĐT và return chính xác mã lỗi này.

## 3. Quy tắc cấu hình Recovery Email Fallback
- Nếu tài khoản trong workbook Excel chưa có email khôi phục (cột recovery_email rỗng), BẮT BUỘC có hằng số fallback:
  ```python
  RECOVERY_EMAIL_FALLBACK = "thanhdatbui1995@gmail.com"
  recovery_email = acc_info.get("recovery_email") or RECOVERY_EMAIL_FALLBACK
  ```
- Không ghi đè nếu tài khoản đã có email khôi phục riêng trong Master Excel.

## 4. Deduplication trong Báo cáo Sức khỏe Pool
- Một tài khoản Gmail có thể đồng thời nằm trong nhiều provider (`chatgpt-web`, `antigravity`, `codex`).
- Khi quét lỗi tổng thể, BẮT BUỘC dedupe danh sách `all_failed` theo email (giữ bản ghi lỗi đầu tiên) trước khi tính toán `total_failures`, phân loại `failure_categories` và gửi cảnh báo Farm Alert, tránh tạo số liệu ảo (ví dụ 8 tài khoản thực tế nhưng báo 9 acc).
