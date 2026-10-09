# GPMLogin API Bypass & Batch Circuit Breaker Invariants

## 1. Bối cảnh & Hiện tượng sự cố (16/09/2026)
Khi Local API của GPMLogin (`http://127.0.0.1:19995/api/v3/profiles/start/{id}`) trả về thông báo lỗi hạ tầng (ví dụ: `Yêu cầu cập trình duyệt [Chromium] [142]`), agent đã tự ý "chữa cháy" bằng cách bypass API GPM và dùng Playwright `launch_persistent_context` mở trực tiếp thư mục profile Chrome.

### Hậu quả nghiêm trọng:
1. **Google OAuth phát hiện Automation (`v3/signin/rejected`):** Mặc dù profile GPM có sẵn session Google hợp lệ, việc mở trực tiếp bằng Playwright thô mà thiếu engine anti-detect / native DLL hooks của GPMLogin (`gpmdriver.exe`, WebGL/Canvas/Audio spoofing) khiến Google lập tức chặn truy cập tại trang SSO OpenAI với thông báo: *"Trình duyệt hoặc ứng dụng này có thể không an toàn"*.
2. **Thiếu Circuit Breaker càn quét hàng loạt:** Script batch chạy `ThreadPoolExecutor` không có bộ đếm lỗi cấu trúc (`consecutive_structural_fails`), dẫn đến việc nó liên tục mở 18 profile liên tiếp mà không tự dừng lại, đe dọa nghiêm trọng tới trust score của dàn tài khoản Google.

---

## 2. Quy tắc Bắt Buộc (Strict Invariants)

### INVARIANT 1: CẤM TUYỆT ĐỐI Bypass GPM Local API
- **CẤM** tự ý dùng `pw.chromium.launch_persistent_context` hoặc Selenium `webdriver.Chrome` mở trực tiếp `user_data_dir` của profile GPM khi thao tác với Google SSO / ChatGPT OAuth.
- Mọi thao tác OAuth Google / ChatGPT **BẮT BUỘC** phải đi qua GPM Local API:
  $$\text{GPM Local API (start\_profile)} \longrightarrow \text{Lấy remote\_debugging\_address} \longrightarrow \text{Playwright connect\_over\_cdp}$$
- **Nếu GPM API báo lỗi (Yêu cầu cập trình duyệt / Port sập / Crash):**
  - **DỪNG LẠI NGAY VÀ BÁO CÁO NGƯỜI DÙNG.**
  - **CẤM TỰ CHẾ CƠ CHẾ BYPASS DƯỚI MỌI HÌNH THỨC.**

### INVARIANT 2: Bắt buộc Circuit Breaker Phân Loại Lỗi & Global Shutdown Signal Trong Mọi Batch Runner
Mọi script chạy batch profile GPM bắt buộc phải cài đặt Circuit Breaker phân loại rõ ràng 2 tầng lỗi kèm tín hiệu ngắt toàn cục:

1. **Lỗi Cấu trúc / Hạ tầng (`fatal_structural = True`):**
   - Định nghĩa:
     - GPM API không phản hồi, sập port 19995, `Connection refused`, `ECONNREFUSED`.
     - Thông báo lỗi core trình duyệt (`Yêu cầu cập trình duyệt`, `Update browser`).
     - Lỗi kết nối CDP mang tính hạ tầng (`connect_over_cdp` với lỗi `connection refused`, `econnrefused`, `port closed`, `failed to establish a new connection`).
     - *Lưu ý*: Nếu `connect_over_cdp` chỉ bị timeout đơn lẻ (ví dụ mạng profile lag), coi là lỗi nghiệp vụ (`fatal_structural = False`) để tránh ngắt script oan.
     - Môi trường thực thi / thư mục profile bị thiếu hoặc sai lệch cấu trúc.
   - Hành vi:
     - Tăng biến đếm `consecutive_structural_fails += 1`.
     - Nếu `consecutive_structural_fails >= 3`:
       - **KÍCH HOẠT CIRCUIT BREAKER NGAY LẬP TỨC.**
       - Kích hoạt `SHUTDOWN_EVENT.set()`.
       - Hủy toàn bộ hàng đợi (`f.cancel() for f in futures if not f.done()`).
       - Dừng script và bắn cảnh báo khẩn cấp.

2. **Lỗi Nghiệp vụ Tài khoản (`fatal_structural = False`):**
   - Định nghĩa:
     - Gặp Google Captcha, Cloudflare Turnstile.
     - Yêu cầu mật khẩu (password challenge) do lâu ngày chưa login.
     - Timeout trang Google Consent / Account Chooser.
     - Timeout đơn lẻ khi kết nối CDP hoặc load trang do proxy của 1 acc bị lag.
   - Hành vi:
     - Bỏ qua tài khoản đó, ghi nhận vào file report.
     - **Reset bộ đếm lỗi cấu trúc về 0** (`consecutive_structural_fails = 0`).
     - Tiếp tục xử lý các profile tiếp theo trong batch bình thường.

### INVARIANT 3: Cơ chế Graceful Cancel với Global `SHUTDOWN_EVENT`
Khi sử dụng `ThreadPoolExecutor`, lệnh `future.cancel()` **chỉ hủy được các task chưa bắt đầu** trong hàng đợi, hoàn toàn không thể dừng các worker thread đang chạy dở:
- Bắt buộc khai báo một cờ toàn cục: `SHUTDOWN_EVENT = threading.Event()`.
- Trong hàm xử lý worker (`process_single_profile`):
  1. Kiểm tra ngay đầu hàm:
     ```python
     if SHUTDOWN_EVENT.is_set():
         logger.warning(f"[{email}] Bỏ qua vì hệ thống đã kích hoạt Circuit Breaker")
         return {"profile_id": p_id, "email": email, "success": False, "error": "Circuit Breaker Triggered", "fatal_structural": False}
     ```
  2. Đặt các chốt kiểm tra `if SHUTDOWN_EVENT.is_set():` trước các bước tốn thời gian:
     - Ngay sau khi start GPM profile (nếu đã kích hoạt event, lập tức gọi `stop_and_kill_gpm_profile` dọn dẹp rồi thoát).
     - Trước khi gọi `page.goto(...)`.
     - Trước các chu kỳ loop login Google / OAuth.
- Khi Circuit Breaker kích hoạt trong loop chính:
  ```python
  SHUTDOWN_EVENT.set()
  for f in futures:
      if not f.done():
          f.cancel()
  break
  ```
