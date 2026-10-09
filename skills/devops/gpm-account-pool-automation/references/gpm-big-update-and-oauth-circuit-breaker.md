# GPMLogin Big Update Modal & Google OAuth Safety Rules

## 1. Sự Cố Modal "Big Update" Trên GPMLogin
- **Hiện tượng:** Khi GPMLogin có modal thông báo cập nhật ("Big Update" / "What's New"), giao diện chính bị làm mờ (modal dialog block).
- **Hậu quả trên API:** API v3 (`http://127.0.0.1:19995/api/v3/profiles/start/{id}`) trả về mã lỗi giả: `Yêu cầu cập trình duyệt [Chromium] [142]` (hoặc `[127]`).
- **Khắc phục:**
  1. Click nút "Đóng thông báo" (nút đỏ ở chân modal) qua Win32 click tọa độ hoặc giao diện.
  2. Để ngăn modal hiện lại mỗi khi mở app, cập nhật file `do_not_show_what_news` tại thư mục GPM:
     ```python
     with open(r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\do_not_show_what_news', 'w') as f:
         f.write('4.3.6-stable')
     ```

## 2. Quy Tắc Bất Biến Về Google OAuth Trình Duyệt GPM (Strict Invariants)
- **CẤM TUYỆT ĐỐI** tự ý dùng `pw.chromium.launch_persistent_context` hoặc `webdriver.Chrome` mở trực tiếp thư mục profile GPM khi chạy OAuth Google / ChatGPT.
  - *Lý do:* Khởi chạy Playwright thô thiếu native DLL hooks (`gpmdriver.exe`, WebGL/Canvas/Navigator spoofing) của GPM. Google sẽ phát hiện cờ tự động hóa tầng C++ và kích hoạt rào chắn `v3/signin/rejected` ("Trình duyệt hoặc ứng dụng này có thể không an toàn").
- **BẮT BUỘC** luôn luôn khởi động qua GPM Local API (`start_gpm_profile` -> lấy port CDP -> `connect_over_cdp`).

## 3. Circuit Breaker Bắt Buộc Trong Mọi Batch Runner
- Phải phân biệt rõ ràng:
  - **Lỗi cấu trúc / Hạ tầng (`fatal_structural = True`):** Lỗi API GPM, lỗi proxy toàn cục, mất kết nối CDP, app GPM bị chặn.
  - **Lỗi nghiệp vụ tài khoản (`fatal_structural = False`):** Captcha, password challenge, timeout 1 acc.
- Ngưỡng dừng: Nếu gặp **>= 3 lỗi cấu trúc liên tiếp**, script BẮT BUỘC:
  1. Kích hoạt `SHUTDOWN_EVENT.set()`.
  2. Cưỡng chế đóng toàn bộ profile đang chạy (`force_emergency_cleanup()`).
  3. `cancel()` các future còn lại trong queue.
  4. Thoát ngay lập tức (`os._exit(1)`), tuyệt đối không để script tiếp tục càn quét profile.
