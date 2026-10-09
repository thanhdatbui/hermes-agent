# Fresh Auth Elevation & Worker Dispatch Discipline in GPM Automation

## 1. Cơ Chế "Recent Fresh Auth" vs "Stale Auth" Khi Bật 2FA Google Authenticator
Trong quá trình tự động hóa kích hoạt 2FA TOTP trên Google qua GPMLogin:
- **Fresh Auth (Elevated Trust - Khuyến nghị):**
  - Khi tài khoản vừa hoàn tất đăng nhập bằng mật khẩu trong vòng 1-2 phút và chuyển hướng trực tiếp sang `https://myaccount.google.com/two-step-verification/authenticator` trong cùng một browser context.
  - Google coi đây là phiên vừa xác thực gần nhất (Recent Fresh Auth), cấp quyền truy cập bảo mật cao mà **hoàn toàn không kích hoạt lại các thử thách xác thực danh tính** (`challenge/dp` Google Prompt, `challenge/ootp` Security Code hay Recovery Email).
  - Giao diện mở thẳng màn hình Authenticator với nút *"Thiết lập ứng dụng xác thực"* / *"Set up authenticator"*, cho phép trích xuất Base32 Secret Key và kích hoạt thành công 100% chỉ trong 10-15 giây (minh chứng thực tế trên các máy M55, M58, M59, M64, M68).
- **Stale Auth (Auth Session Cũ / Đã Nguội):**
  - Profile đã đăng nhập thành công từ trước (vài giờ hoặc vài ngày trước).
  - Khi mở lại profile và truy cập vào đường dẫn nhạy cảm như 2SV Authenticator, Google coi session đã cũ và bắt buộc kích hoạt Re-Authentication qua `challenge/dp` (gửi thông báo về máy Samsung S7) hoặc `challenge/ootp`.
  - Lúc này, nếu S7 đang bận chạy cron nuôi TikTok hoặc lag ADB socket, luồng bật 2FA rất dễ bị kẹt hoặc rơi vào vòng lặp menu `challenge/selection`.
- **Bài học vận hành:** Đối với các tài khoản chưa có 2FA, quy trình tối ưu nhất là **tạo profile mới -> gán proxy 1:1 -> đăng nhập mật khẩu -> chuyển thẳng sang bật 2FA ngay trong cùng 1 chu trình**.

## 2. Kỷ Luật Điều Phối Worker Subagent Chạy Batch (Chống Kẹt Budget 35 Turns)
Khi Coordinator giao việc cho Worker Subagent thực hiện chạy batch tự động hóa:
- **Cạm bẫy:** Giao nhiệm vụ mở với các từ khóa thăm dò như *"kiểm tra hàm...", "nghiên cứu selector...", "chuẩn bị tài khoản..."*. Subagent sẽ sa đà vào việc gọi 20-30 tool calls đọc code, curl kiểm tra proxy, chạy adb devices kiểm tra điện thoại... và cạn kiệt ngân sách `max_iterations = 35` trước khi thực sự chạy lệnh batch (như trường hợp `deleg_da46494c` tiêu tốn 1464 giây nhưng không chạy được script).
- **Quy tắc điều phối chuẩn (Enforced Pattern):**
  Coordinator đã kiểm tra hạ tầng O(1) thì trong prompt dispatch BẮT BUỘC:
  1. Khẳng định hạ tầng đã 100% OK (Proxy LIVE, ADB Online, IMAP sẵn sàng) và ra lệnh: **CẤM kiểm tra lại hạ tầng**.
  2. Cung cấp sẵn mã nguồn Python ngắn gọn để patch file mục tiêu.
  3. Yêu cầu làm đúng 3 bước tuần tự:
     - Bước 1: `write_file` tạo file patcher.
     - Bước 2: Chạy `python patcher.py && python -m py_compile target_script.py`.
     - Bước 3: Chạy `python target_script.py` và đọc kết quả đối soát trong Excel.
  - Kết quả áp dụng chuẩn: Worker `deleg_c488a91a` hoàn tất batch 3 máy chỉ trong **5 tool calls** và **270 giây**.
