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
1. **Bảo tồn toàn vẹn BỘ 4 CHỈ SỐ (Follower, Following, Heart, Video):**
   - Khi cào dính SlardarWAF / `RATE_LIMITED` hoặc lỗi mạng, scraper trả về `0` cho toàn bộ các trường.
   - **CẤM TUYỆT ĐỐI** chỉ giữ lại `follower`/`following` mà bỏ quên `heart` và `video`. Nếu bỏ quên, `heart_delta = 0 - prev_heart` sẽ làm sụt âm hàng nghìn tim toàn farm và tràn ngập tab "Giảm Tim (-)".
   - Kiểm tra độc lập từng trường trong bộ 4 chỉ số: Nếu `curr_val == 0` mà `prev_val > 0`:
     + `curr_val = prev_val`, `delta = 0`.
     + Ghi log telemetry tương ứng:
       `logging.warning("zero-scrape telemetry: follower preserved for %s", username)`
       `logging.warning("zero-scrape telemetry: following preserved for %s", username)`
       `logging.warning("zero-scrape telemetry: heart preserved for %s", username)`
       `logging.warning("zero-scrape telemetry: video preserved for %s", username)`
     + Đồng bộ cập nhật vào `item_copy['followerCount']`, `item_copy['followingCount']`, `item_copy['heartCount']`, `item_copy['videoCount']` trước khi `INSERT INTO snapshots`.
2. **Cơ chế Proxy Fallback & Tốc độ cào:**
   - Trong `fetch_profile()`, khi dính `RATE_LIMITED`, hệ thống tự động bốc proxy khác từ pool 69 proxy để retry (`max_retries=2`).
   - Pass 2 (quét bổ sung) tự động gom các nick lỗi để cào bù.
   - Trên dàn >1.200 nick, 1-2% nick dính WAF/Captcha ngẫu nhiên của TikTok là điều bình thường; cơ chế bảo tồn số cũ (delta = 0) đảm bảo dashboard không bao giờ báo động giả.
3. **Bảo toàn số 0 tự nhiên của nick mới (Genuine Zeros):**
   - Tài khoản mới tạo / chưa từng có snapshot lịch sử (`prev_row is None` hoặc `prev_count == 0`) thì giữ nguyên `0` tự nhiên, không ghi log cảnh báo sai lệch.
4. **Dashboard Guard (`get_farm_data`):**
   - Khi tính toán `is_anomaly_drop`: nếu `follower == 0` mà `heart > 0` và `prev_follower > 0`, tuyệt đối không tính là anomaly drop để phòng vệ tầng 2 chống glitch cào thiếu data.

## 4. Quy trình khắc phục khi phát hiện snapshot bị lỗi 0
Khi phát hiện đợt quét bị lỗi zero-scrape hàng loạt:
1. Xác định snapshot lỗi: `SELECT id, username, heart FROM snapshots WHERE status = 'RATE_LIMITED' AND heart = 0;`
2. Khôi phục số liệu chuẩn từ snapshot `LIVE` gần nhất:
   ```sql
   UPDATE snapshots 
   SET heart = (
       SELECT s2.heart FROM snapshots s2 
       WHERE s2.username = snapshots.username 
         AND s2.id < snapshots.id 
         AND s2.status = 'LIVE' 
         AND s2.heart > 0 
       ORDER BY s2.id DESC LIMIT 1
   )
   WHERE status = 'RATE_LIMITED' 
     AND heart = 0 
     AND EXISTS (
       SELECT 1 FROM snapshots s2 
       WHERE s2.username = snapshots.username 
         AND s2.id < snapshots.id 
         AND s2.status = 'LIVE' 
         AND s2.heart > 0
     );
   ```
3. Kiểm tra lại Dashboard `port 1905` để xác nhận Tổng Tim và tab "Giảm Tim (-)" đã sạch số âm ảo.
