# GPM OAuth & Batch Safety Invariants

## 1. TUYỆT ĐỐI CẤM BYPASS GPM API ĐỂ LAUNCH PLAYWRIGHT TRỰC TIẾP
- **Hiện tượng:** Khi GPM API báo lỗi chặn start profile (ví dụ: `Yêu cầu cập trình duyệt [Chromium] [142]`), agent nảy sinh ý định tự bypass API bằng `launch_persistent_context` trỏ thẳng vào folder profile với binary `chrome.exe`.
- **HẬU QUẢ NGHIÊM TRỌNG:** Playwright khởi chạy trực tiếp thiếu hoàn toàn anti-detect driver/DLL hooking (fingerprint injection) độc quyền của GPMLogin. Khi thực hiện liên kết Google SSO (OAuth Consent), Google phát hiện ngay trình duyệt tự động hóa và ném màn hình `v3/signin/rejected`: *"Trình duyệt hoặc ứng dụng này có thể không an toàn"*.
- **QUY TẮC BẤT DI BẤT DỊCH:** 
  - BẮT BUỘC khởi chạy profile qua GPM API v3 (`GET /api/v3/profiles/start/{id}`) để GPM tiêm anti-detect environment.
  - Playwright CHỈ ĐƯỢC kết nối qua CDP: `connect_over_cdp("http://" + remote_debugging_address)`.
  - Nếu API GPM báo lỗi cập nhật core hoặc không start được: DỪNG LẠI NGAY LẬP TỨC và báo User, CẤM TỰ Ý MỞ PROFILE TRỰC TIẾP.

## 2. BẮT BUỘC CIRCUIT BREAKER CHO TOÀN BỘ BATCH RUNNER
- **Nguyên tắc Fail-Fast:**
  - Bất kỳ script chạy batch nào (`ThreadPoolExecutor`, `asyncio`, vòng lặp) BẮT BUỘC phải có biến đếm `consecutive_failures`.
  - **Ngưỡng ngắt khẩn cấp:** Nếu có **>= 3 lỗi liên tiếp** (hoặc tỷ lệ fail > 30% sau 5 profiles đầu tiên), script PHẢI:
    1. Dừng ngay lập tức việc submit thêm task mới (`executor.shutdown(wait=False, cancel_futures=True)`).
    2. Đóng và dọn sạch các profile/browser đang mở dở dang.
    3. Ghi log cảnh báo `CRITICAL: Circuit breaker triggered!` và thoát chương trình.
    4. Báo cáo hiện trường và hỏi ý kiến User.
- **CẤM:** Quét càn qua danh sách profile khi đã có dấu hiệu lỗi hàng loạt (hỏng proxy, Google challenge, app chặn API).
