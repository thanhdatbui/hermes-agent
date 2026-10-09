# Quy trình săn link Google Flash Offer / Service Activation qua GPM CDP

## 1. Bản chất sự cố
Khi shop xả danh sách link kích hoạt Google (Google One / AI Premium dạng `serviceactivation.google.com`), thời gian link bốc hơi cực nhanh (2-4 phút).
Nếu script:
- Bốc bừa profile theo tên `@gmail.com` trong pool tổng -> gặp phải acc chưa login, acc lỗi proxy hoặc cookie hết hạn -> chuyển hướng về `Sign in - Google Accounts` -> lãng phí lượt link và thất bại.
- Ngồi preflight test từng profile lúc sự kiện diễn ra -> tốn thời gian, người khác húp hết trước.

## 2. Kỷ luật phân nhóm trên GPM (Invariant)
BẮT BUỘC phân chia profile GPM thành 2 Group rõ rệt từ trước:
1. **Group `Google_Live_Ready`**:
   - Chỉ chứa các profile ĐÃ ĐĂNG NHẬP THÀNH CÔNG Google/Gmail, session live 100%.
   - Đây là kho đạn duy nhất được dùng khi kích hoạt batch bắn link.
2. **Group `Google_Pending_Cooldown` (hoặc `Error`)**:
   - Chứa profile chưa login, lỗi login, proxy chết, hoặc đang trong thời gian ngâm cooldown (>=4 ngày).
   - Tuyệt đối cấm bốc profile từ nhóm này hoặc group `All` khi có sự kiện săn link.

## 3. Kiến trúc Claim siêu tốc (Async Playwright CDP)
- **Truy vấn Profile:** Query trực tiếp theo `group_id` của nhóm `Live_Ready`:
  `GET /api/v3/profiles?group_id=<READY_GROUP_ID>` (Mất 0.05s, không cần preflight).
- **Kết nối CDP trực tiếp:**
  - `GET /api/v3/profiles/start/{id}?win_scale=0.5` -> lấy `remote_debugging_address`.
  - Dùng `playwright.chromium.connect_over_cdp(f"http://{addr}")`.
  - `page.goto(url, wait_until="domcontentloaded", timeout=15000)`.
  - Inject click ngay khi nút `Tham gia / Accept / Bắt đầu` xuất hiện.
  - Khối `finally`: đóng browser và gọi `GET /api/v3/profiles/stop/{id}` để giải phóng tài nguyên.
- **Benchmark đạt được:** Concurrency 5 luồng xử lý 10 link chỉ mất **~10.4 giây** (trung bình ~4.5s/link).
