# TikTok Tracker Zero-Scrape Preservation and Dashboard Guard

## 1. Bối cảnh & Nguyên nhân lỗi Zero-Scrape
Khi crawler / scraper TikTok (`tiktok_account_tracker.py` hoặc các công cụ quét profile) gửi request qua proxy xoay vòng đến `https://www.tiktok.com/@username`:
- Thỉnh thoảng do mạng chập chờn, proxy bị chậm, hoặc TikTok WAF/Slardar bóp dữ liệu HTML, thẻ `__UNIVERSAL_DATA_FOR_REHYDRATION__` trả về thiếu các trường `stats.followerCount` hoặc `stats.followingCount`.
- Parser fallback gán giá trị mặc định là `0` (`followerCount=0`, `followingCount=0`), trong khi các chỉ số khác như `heartCount` và `videoCount` vẫn bóc tách được bình thường.

## 2. Nguy cơ dữ liệu (Data Corruption & False Anomaly Alerts)
Nếu code tracker ghi đè số `0` này vào bảng `snapshots` của cơ sở dữ liệu (`tiktok_tracker.db`):
- Toàn bộ lịch sử follower của tài khoản bị sập về 0.
- Dashboard (`tiktok_dashboard.py` / `dashboard.queries`) tính delta: `delta_f = 0 - prev_f = -prev_f` (-100%).
- Hệ thống bị kích hoạt báo động giả cờ đỏ nghiêm trọng: `⚠️ TỤT BẤT THƯỜNG (-X / 100%)`.
- Làm sai lệch toàn bộ biểu đồ tăng trưởng toàn farm và các chỉ số thống kê.

## 3. Quy tắc cốt lõi: Anti-Zero-Scrape Invariant (Chống Ghi Bậy 0)
Trong mọi script tracker / scraper tài khoản:
1. **Tách độc lập từng trường:** Kiểm tra `follower` và `following` hoàn toàn độc lập. Việc `following` bị 0 không được làm ảnh hưởng `follower` và ngược lại.
2. **Bảo tồn giá trị lịch sử (Preserve Historical Counts):**
   - Nếu dữ liệu cào về `curr_count == 0` nhưng trong snapshot gần nhất `prev_count > 0`:
     - BẮT BUỘC gán lại: `curr_count = prev_count`.
     - Đặt delta tương ứng: `delta_count = 0`.
     - Ghi log cảnh báo telemetry:
       `logging.warning("zero-scrape telemetry: follower preserved for %s", username)`
       `logging.warning("zero-scrape telemetry: following preserved for %s", username)`
3. **Bảo toàn số 0 tự nhiên của nick mới (Genuine Zeros):**
   - Tài khoản mới tạo / chưa từng có snapshot lịch sử (`prev_row is None` hoặc `prev_count == 0`) thì giữ nguyên `0` tự nhiên, không ghi log cảnh báo sai lệch.
4. **Dashboard Guard (`get_farm_data`):**
   - Khi tính toán `is_anomaly_drop`: nếu `follower == 0` mà `heart > 0` và `prev_follower > 0`, tuyệt đối không tính là anomaly drop để phòng vệ tầng 2 chống glitch cào thiếu data.

## 4. Quy trình khắc phục khi phát hiện snapshot bị lỗi 0
Khi phát hiện đợt quét bị lỗi zero-scrape hàng loạt:
1. Xác định timestamp của đợt quét lỗi: `SELECT id, username, follower, following FROM snapshots WHERE timestamp >= '<date> 07:00:00' AND follower = 0;`
2. Đối soát với snapshot ngày hôm trước (`prev_follower > 0`).
3. Chạy câu lệnh UPDATE khôi phục đúng số follower/following thực tế từ snapshot trước đó.
4. Kiểm tra lại API Dashboard (`/api/data`) để xác nhận danh sách `is_anomaly_drop` đã sạch hoàn toàn (0 nick bị cờ đỏ).
