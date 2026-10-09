# GPM Modal Update Dialog, Anti-Detect Bypass & Batch Circuit Breaker Safety

## 1. Hiện tượng sự cố & Phân tích cội rễ

### A. Modal "Big Update" / Popups chặn ngầm GPM Local API
- **Hiện tượng**: Khi ứng dụng GPMLogin được mở lên, nếu có bản cập nhật mới (ví dụ "Big Update" giới thiệu Chromium v142, Firefox 145, Fingerprint v411), GPMLogin sẽ hiển thị một Modal Dialog dạng pop-up phủ mờ toàn màn hình.
- **Tác động API**: Khi modal này đang mở, GPM Local API (`/api/v3/profiles/start/{id}`) sẽ bị chặn nội bộ và trả về mã lỗi gây hiểu lầm:
  ```json
  {"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}
  ```
- **Sai lầm tai hại (Anti-Pattern)**: Agent vội vàng kết luận thiếu binary trình duyệt hoặc API hỏng rồi **tự ý dùng Playwright thô mở trực tiếp `user_data_dir`** (`pw.chromium.launch_persistent_context`).
- **Hậu quả**: Khi mở bằng Playwright thô, trình duyệt **mất 100% lớp chống phát hiện (anti-detect, gpmdriver spoofing, WebGL/Canvas masking)**. Khi người dùng bấm "Continue with Google" để OAuth OpenAI, Google kích hoạt ngay cơ chế phòng vệ tự động hóa `accounts.google.com/v3/signin/rejected` ("Trình duyệt hoặc ứng dụng này có thể không an toàn"), đe dọa trực tiếp đến độ tin cậy (trust score) của toàn bộ dàn tài khoản.
- **Giải pháp dứt điểm**:
  1. **Click đóng Modal Update bằng Win32 API**: Gửi click vào nút "Đóng thông báo" trên giao diện GPM (`x=960, y=755` trên màn hình 1920x1080).
  2. **Ghi đè cờ chặn pop-up vĩnh viễn**: Cập nhật file `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\do_not_show_what_news` thành phiên bản hiện tại (ví dụ `4.3.6-stable`) để GPM không bao giờ hiện lại bảng này khi khởi động.
  3. Sau khi đóng modal, endpoint `/api/v3/profiles/start/` lập tức hoạt động bình thường trở lại (`success: True`).

---

### B. Invariant: CẤM TUYỆT ĐỐI Bypass GPM Local API Mở Trực Tiếp Profile
- Mọi thao tác tự động hóa với Profile GPM BẮT BUỘC phải đi qua GPM Local API v3:
  1. `GET /api/v3/profiles/start/{id}?win_scale=0.8` -> Lấy `remote_debugging_address`.
  2. `pw.chromium.connect_over_cdp(f"http://{addr}")`.
  3. `GET /api/v3/profiles/stop/{id}` kết hợp Process Reaper dọn Chrome mồ côi.
- **CẤM TUYỆT ĐỐI**: Không bao giờ được dùng `pw.chromium.launch_persistent_context` hay `webdriver.Chrome` trỏ trực tiếp vào thư mục profile của GPM khi thực hiện đăng nhập hoặc xác thực Google SSO / OAuth. Nếu API GPM lỗi: DỪNG LẠI, KIỂM TRA HIỆN TRƯỜNG UI APP GPM VÀ BÁO CÁO NGƯỜI DÙNG, CẤM TỰ CHẾ.

---

### C. Bắt buộc Circuit Breaker Phân tầng & Emergency Process Tracking cho Batch Runner
Khi chạy batch xử lý hàng chục / hàng trăm profile, script BẮT BUỘC phải tuân thủ các quy tắc an toàn sau:

1. **Phân biệt Lỗi Cấu Trúc/Hạ Tầng vs Lỗi Nghiệp Vụ Tài Khoản**:
   - `is_structural_error()`:
     - **Lỗi cấu trúc (`fatal_structural = True`)**: GPM API lỗi, app GPM bị tắt, lỗi kết nối mạng nội bộ (`ECONNREFUSED`, `Connection refused`), lỗi core browser.
     - **Lỗi tài khoản (`fatal_structural = False`)**: Captcha (Recaptcha/Cloudflare), yêu cầu mật khẩu, timeout trang chọn tài khoản, OpenAI token exchange failed.
   - **Quy tắc đếm**: Chỉ tăng `consecutive_structural_fails` khi gặp lỗi cấu trúc. Nếu gặp lỗi tài khoản hoặc thành công -> RESET bộ đếm về 0.

2. **Cơ chế Ngắt mạch (Circuit Breaker) & Emergency Cleanup**:
   - Ngưỡng kích hoạt: `MAX_CONSECUTIVE_STRUCTURAL_FAILS = 3`.
   - **Điểm yếu của ThreadPoolExecutor**: Gọi `f.cancel()` chỉ hủy các task còn nằm trong hàng đợi; các worker đang chạy dở (`already-running workers`) vẫn tiếp tục hoạt động, và context manager `with ThreadPoolExecutor` sẽ bị block chờ các worker này hoàn tất.
   - **Giải pháp chuẩn**:
     - Duy trì `ACTIVE_RUNNING_PROFILES = {}` với `threading.Lock()`.
     - Viết hàm `force_emergency_cleanup()`: Khi breaker kích hoạt, lập tức set `SHUTDOWN_EVENT`, duyệt registry gọi `browser.close()` và kill dứt điểm toàn bộ tiến trình Chrome/profile đang chạy dở.
     - Sử dụng `os._exit(1)` để thoát tiến trình khẩn cấp ngay lập tức, ngăn ngừa hoàn toàn nguy cơ quét lố tài khoản.

---

### D. Cookie Chunking trong ChatGPT Web NextAuth
- ChatGPT Web sử dụng NextAuth, đối với các session có payload lớn, cookie được chia nhỏ thành các chunk:
  `__Secure-next-auth.session-token.0`, `__Secure-next-auth.session-token.1`, ...
- **Quy tắc trích xuất**:
  - Quét toàn bộ cookie có chứa `session-token`.
  - Sắp xếp key theo thứ tự alphabet/index (`.0`, `.1`).
  - Ghép thành chuỗi header cookie hợp lệ: `__Secure-next-auth.session-token.0=val0; __Secure-next-auth.session-token.1=val1`.
  - Nạp chuỗi này vào OmniRoute `:20129` để upstream gửi request xác thực thành công.
