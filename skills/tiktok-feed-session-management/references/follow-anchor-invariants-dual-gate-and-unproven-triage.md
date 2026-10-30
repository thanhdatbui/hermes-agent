# Invariant & Triage: Follow Anchor Availability, Dual Gate Budget, & UNPROVEN Reconcile

## 1. INVARIANT BẤT DI BẤT DỊCH VỀ ANCHOR (CHỐNG ẢO GIÁC SUY DIỄN)
- **CẤM TUYỆT ĐỐI** đưa ra giả thuyết hoặc đổ lỗi: "Hết nick nội bộ làm anchor", "anchor không đủ nick", "không tìm thấy nick nội bộ".
- **Lý do kiến trúc & thực tế:**
  1. Toàn bộ kho nick nội bộ farm luôn luôn đầy đủ trong hệ thống safe workbook.
  2. Kiến trúc follow engine (`follow_engine.py`): Mode 2 chạy chính trước; nếu Mode 2 hết anchor hoặc chưa đạt session budget, hệ thống luôn có cơ chế **Auto-Fallback chuyển sang Mode 1 (`mode2_fallback_mode1`)** để search & follow bù chỉ tiêu. Không bao giờ có chuyện kẹt hay dừng do "hết anchor".

## 2. NGUYÊN NHÂN THỰC TẾ KHI MÁY BÁO 0 FOLLOW (STATUS: OK)
Khi máy chạy xong follow với `followed_count = 0` và `status: OK`:
- **Dual Gate Video & Age (`Dual Gate 2026-10-06` trong `follow_state.py`):**
  - Điều kiện cấp budget follow: `account_age_days >= 30` VÀ `video_count >= 10`.
  - Nếu `video_count < 10` (ví dụ tài khoản chỉ mới có 7, 8, 9 video): hàm `state.session_budget()` trả về **`budget = 0`**.
  - Khi `budget = 0`, tool vào luồng follow nhưng không được cấp quota -> ghi nhận 0 lượt follow và kết thúc an toàn mà không đụng device.
  - Phân tích số video: Đối chiếu trực tiếp giữa số ngày tuổi, chu kỳ đăng 1 video/ngày, và snapshot SQLite `snapshots` để xác định chính xác số video hiện tại thay vì suy đoán bừa.

## 3. TRIAGE LỖI "UNPROVEN" TRONG ĐỐI SOÁT TIKTOK WEB
- **Nguyên nhân cốt lõi:**
  - Watchdog so sánh snapshot T0 (trước phiên) và T1 (sau phiên). Nếu T0 cũ quá 4 giờ hoặc khác ngày so với T1 (`(s_dt - b_dt).total_seconds() > 4 * 3600 or b_dt.date() != s_dt.date()`), watchdog đánh dấu `stale_baseline` -> in nhãn `UNPROVEN`.
  - Nguyên nhân T0 bị cũ: Thường do wrapper thực thi cron (`tiktok_runner.py` trên runtime `%LOCALAPPDATA%`) bị trôi mã hash, lệch phiên bản với git repo nên chưa gọi hàm cào T0 trước phiên (`_scrape_pre_session_following`).
  - Ngoài ra, trên Windows, lệnh gọi subprocess `tiktok_account_tracker.py` cào T0 trong `tiktok_runner.py` bắt buộc phải kèm cờ `creationflags = 0x08000000` (DETACHED / NO_WINDOW) để chạy ngầm an toàn, không bị nghẽn console.
  - Chú ý bug hiển thị `total_reported` của watchdog: khi snapshot bị đánh dấu `UNPROVEN`, nhánh `else` trong `feed_session_watchdog.py` không cộng dồn `expected_delta` vào `total_reported` dẫn đến tiêu đề in ra `(Script báo 0 lượt follow)` dù chi tiết bên dưới báo đúng 5 lượt (3 lượt M5, 2 lượt M17).
- **Khắc phục & Duy trì:**
  - Bắt buộc kiểm tra 4 tầng đồng bộ hash (Repo git, LocalAppData, Deploy, OneDrive Sync).
  - Hậu kiểm dữ liệu snapshot trong `D:/Taadaa/data/tiktok_tracker.db` để xác nhận số following thực tế tăng trên web có khớp với số liệu script báo hay không.
