# GPM OAuth Anti-Pattern & Circuit Breaker Rule (Case GPM-OAUTH-DIRECT-PLAYWRIGHT-BREAKER-01)

## 1. CẤM Tuyệt Đối Bypass GPM Local API
- **Nguyên nhân sự cố:** Khi GPM Local API chặn khởi động profile với lỗi hạ tầng (`Yêu cầu cập trình duyệt [Chromium] [142]`), tuyệt đối **KHÔNG ĐƯỢC** tự ý "chữa cháy" bằng cách dùng `playwright.chromium.launch_persistent_context` hoặc `webdriver.Chrome` mở trực tiếp thư mục `user_data_dir` của profile.
- **Hậu quả:** Trình duyệt thô thiếu toàn bộ native anti-detect hooks/DLL của GPMLogin (`gpmdriver.exe`, WebGL/Canvas/Audio/Navigator spoofing). Khi thực hiện Google SSO / OAuth cho bên thứ ba (OpenAI ChatGPT), Google nhận diện ngay cờ automation (`navigator.webdriver` tầng V8 engine) và kích hoạt rào chắn `v3/signin/rejected` (*"Trình duyệt hoặc ứng dụng này có thể không an toàn"*).
- **Quy tắc:** Mọi tác vụ OAuth Google / ChatGPT **BẮT BUỘC** phải gọi qua GPM Local API (`start_gpm_profile` -> lấy port CDP -> `connect_over_cdp`). Nếu API GPM lỗi: **DỪNG LẠI VÀ BÁO CÁO NGƯỜI DÙNG, CẤM TỰ CHẾ BẰNG MỌI GIÁ.**

## 2. Bắt Buộc Circuit Breaker Phân Tầng Lỗi (Fail-Fast)
Mọi runner batch tự động hóa mở profile GPM bắt buộc phải có cơ chế ngắt mạch khẩn cấp:

### A. Phân loại 2 nhóm lỗi:
1. **Lỗi cấu trúc / Hạ tầng (`fatal_structural = True`):**
   - API GPM không chạy / từ chối kết nối (`Connection refused`, `GPMLogin not running`).
   - Lỗi core browser bị chặn (`Yêu cầu cập trình duyệt`).
   - Lỗi kết nối CDP do hạ tầng cổng (`econnrefused`, `port closed`).
2. **Lỗi nghiệp vụ tài khoản (`fatal_structural = False`):**
   - Gặp Captcha, Cloudflare, yêu cầu nhập mật khẩu, timeout trang Google Account Chooser, proxy 1 acc bị chậm.

### B. Logic ngắt mạch chuẩn (Standard Implementation Pattern):
- Sử dụng biến đếm lỗi cấu trúc liên tiếp: `consecutive_structural_fails`.
- Ngưỡng tối đa: `MAX_CONSECUTIVE_STRUCTURAL_FAILS = 3`.
- Khi gặp lỗi cấu trúc: `consecutive_structural_fails += 1`. Nếu chạm ngưỡng:
  1. Kích hoạt `SHUTDOWN_EVENT.set()`.
  2. Thực hiện `force_emergency_cleanup()`: Duyệt qua registry các active profiles đang chạy để đóng browser và gọi kill profile ngay lập tức.
  3. Duyệt danh sách futures và `f.cancel()` các tác vụ đang chờ trong queue.
  4. Thoát khỏi vòng lặp batch, dừng script và phát cảnh báo.
- Khi một profile thành công hoặc chỉ dính lỗi nghiệp vụ (`fatal_structural = False`): Reset `consecutive_structural_fails = 0` và tiếp tục xử lý các profile tiếp theo.
