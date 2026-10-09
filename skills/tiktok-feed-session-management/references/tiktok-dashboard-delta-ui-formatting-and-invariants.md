# TikTok Dashboard Delta UI Formatting & Calculation Invariants

## 1. Delta Calculation Invariant vs Summary Total
- **Nguyên tắc:** 
  * Nick mới thêm trong ngày chưa có snapshot đối chiếu hôm trước (`prev_row is None`): `delta = 0`.
  * Do đó: `SUM(delta)` là biến động của riêng dàn nick cũ, trong khi `SUM(total)` là tổng tích luỹ toàn bộ nick (bao gồm nick mới).
  * Khi số lượng nick mới tăng nhưng nick cũ bị tụt follow nhẹ, `SUM(total)` vẫn tăng nhưng `SUM(delta)` sẽ âm (`delta < 0`). Cần giải thích rõ cho user hiểu hai góc nhìn này.

## 2. UI Formatting Pitfall: Tránh Ghép Chuỗi Thủ Công Dấu "+" với Giá Trị Âm
- Khi delta âm (`delta = -85`), việc ghép chuỗi cứng `+${delta}` hoặc `+str(delta)` sẽ sinh ra hiển thị dị tật: `+-85` hoặc `📈 Tổng tăng: +-85`.
- **Giải pháp chuẩn:**
  * Luôn kiểm tra dấu trước khi format:
    ```python
    if tot_delta < 0:
        label = "📉 Tổng giảm:"
        color = "#ef4444"
        val_str = str(tot_delta)  # Đã có sẵn dấu trừ
    else:
        label = "📈 Tổng tăng:"
        color = "#22c55e"
        val_str = f"+{tot_delta}"
    ```
  * Bắt buộc đồng bộ cả Python server initial render lẫn JavaScript client-side auto-refresh.

## 3. Monolith File Worker Dispatch Discipline (>1500 dòng)
- Coordinator bắt buộc tìm trước exact anchor và match count `1`.
- Yêu cầu worker: cấm chạy `search_files` / `read_file` trên monolith file, đi thẳng vào `patch(mode="replace")` và chạy focused unit test (`pytest -k`). Tránh cạn turn budget hoặc bị timeout 600s.

## 4. Midnight Partial-Scan Anomaly (Co cụm nick sau 0h đêm do lọc cứng `max_dt`)
- **Hiện tượng:** Sau 0h đêm (ví dụ 00:10), watchdog ca tối chạy đối soát nhanh cho 54 máy, lưu snapshot với ngày mới (`2026-09-25`). Sáng ra người dùng thấy dashboard tụt từ 1.042 nick xuống còn đúng 54 nick.
- **Root Cause:** Câu query SQL cũ dùng `WHERE substr(timestamp, 1, 10) = max_dt`. Khi `max_dt` chuyển sang ngày mới, 988 nick chưa tới ca quét 07:00 sáng bị query loại bỏ hoàn toàn.
- **Giải pháp chuẩn:**
  * Bỏ lọc cứng theo `max_dt`. Dùng rolling window 2 ngày gần nhất (`timestamp >= date(max_dt, '-2 days')`) lấy snapshot mới nhất (`rn = 1`) cho từng account.
  * Đối chiếu delta với snapshot gần nhất của ngày trước đó (`substr(s.timestamp, 1, 10) < substr(c.timestamp, 1, 10)`).
  * 54 nick chạy đối soát sau 0h đêm sẽ hiển thị số liệu mới; 988 nick còn lại vẫn giữ nguyên số liệu hôm trước, bảo toàn 1.042 nick 24/7.
  * `last_scan` tính bằng `max(it["timestamp"])` thay vì `items[0]["timestamp"]` (tránh lấy nhầm timestamp của nick top follower).

## 5. Single-Account Glitch Zero-Drop Distortion (Lỗi mạng 1 nick làm méo mó Delta toàn Farm)
- **Hiện tượng:** Farm đang nuôi tương tác tốt, 30 nick tăng +38 follower và 21 nick tăng +24 following, nhưng thẻ KPI lại báo tụt âm `-17` Follower và `-85` Following.
- **Root Cause:** Script tracker khi gặp proxy timeout / lỗi mạng sẽ gán `status = 'ERROR'` và mặc định `follower = 0`, `following = 0`. Chỉ cần 1 nick duy nhất bị lỗi (như `@m.ngc4624` từ 54 fl / 109 fl tụt về 0) là sinh ra biến động âm `-54` follower và `-109` following, nuốt trọn mức tăng trưởng của toàn farm.
- **Kỷ luật điều tra O(1):**
  1. Kiểm tra ngay danh sách nick có delta âm lớn:
     ```sql
     SELECT c.username, c.follower, p.follower, (c.follower - p.follower) as delta_f, c.status
     FROM LatestCurr c JOIN RankedPrev p ON c.username = p.username
     WHERE (c.follower - p.follower) < -10;
     ```
  2. Tra soát `status`: nếu là `ERROR` hoặc `NOT_FOUND` mới xuất hiện, kiểm tra xem có phải do cào mạng bị lỗi thời điểm quét hay không.
  3. Dùng `fetch_profile(username)` trực tiếp không qua proxy lag để re-check trạng thái live và cập nhật lại số liệu.
  4. **Chốt chặn SQL bắt buộc trên Dashboard**: Trong câu truy vấn `snapshots` của Dashboard (`RankedAll` và `RankedPrev`), BẮT BUỘC thêm điều kiện `WHERE status != 'ERROR'`. Khi một nick gặp timeout proxy, Dashboard sẽ tự động bỏ qua snapshot lỗi đó và lấy snapshot `LIVE` hợp lệ gần nhất, triệt tiêu 100% hiện tượng tụt số ảo toàn farm.

## 6. Biểu Đồ Tăng Trưởng Toàn Farm (Farm Growth Chart & History Aggregation)
- **Yêu cầu nghiệp vụ**: Ngoài biểu đồ tăng trưởng từng nick trong modal cá nhân, Dashboard hỗ trợ xem biểu đồ tăng trưởng của toàn bộ Farm dựa trên số tổng Follower, Following, Tim tích lũy qua từng ngày.
- **Tránh nhân đôi số liệu (Double-counting trap)**:
  * Trong 1 ngày, một số nick có thể được quét 2-3 lần (chạy sáng, đối soát trưa, nuôi tối).
  * Lệnh SQL BẮT BUỘC phải gom nhóm theo `(substr(timestamp, 1, 10), username)` với `rn = 1` trước khi thực hiện `SUM()`:
    ```sql
    WITH DayUser AS (
        SELECT substr(timestamp, 1, 10) as dt, username, follower, following, heart, video, status,
               ROW_NUMBER() OVER (PARTITION BY substr(timestamp, 1, 10), username ORDER BY timestamp DESC) as rn
        FROM snapshots
        WHERE status != 'ERROR'
    )
    SELECT dt, count(username) as total_users, sum(follower) as total_follower,
           sum(following) as total_following, sum(heart) as total_heart, sum(video) as total_video
    FROM DayUser WHERE rn = 1 GROUP BY dt ORDER BY dt ASC
    ```
- **Làm mịn dữ liệu ngày hiện tại (Day Smoothing)**:
  * Sau 0h đêm (trước ca quét chính 07:00), ngày mới chỉ có một số lượng nhỏ nick chạy đối soát (< 50% số nick hôm trước).
  * Nếu vẽ thẳng dữ liệu thô, đường biểu đồ ngày hôm nay sẽ cắm đầu dốc đứng xuống đáy.
  * Thuật toán `get_farm_history()` phải kiểm tra: nếu ngày cuối có `total_users < 0.5 * previous_day_users`, tự động ghi đè bằng `summary` từ `get_farm_data()` (kết hợp các nick mới quét + nick hợp lệ ngày hôm trước) để đồ thị luôn mượt mà, liên tục và chính xác.
- **Giao diện Modal Toàn Farm (`farmHistoryModal`)**:
  * Tích hợp nút `📈 Biểu Đồ Farm` trên Header và `📊 Biểu Đồ Toàn Farm` trên Toolbar.
  * Hỗ trợ 4 tab: `[⭐ Tổng Quan]` (4 mini sparkline cards + bảng chi tiết), `[📈 Follower]`, `[💖 Tim]`, `[👥 Đã Follow]` (đồ thị SVG bo góc, gradient fill, tooltip hiển thị tổng số và delta theo ngày).

## 7. Phân Loại Tài Khoản: Đề Xuất (Trending) vs Tiềm Năng (Potential) & Tương Hỗ Độc Quyền
- **Quy tắc phân loại kỹ thuật & Bản chất vận hành:**
  * `🔥 ĐỀ XUẤT` (`is_trending`): `(delta_f >= 20) or (delta_h >= 50) or (f_val >= 1000 and is_live)`.
    - *Bản chất:* Nick đã thực sự cắn sóng FYP lớn hoặc kênh đã đạt mốc lớn (>= 1k follow). Phễu phân phối đã mở rộng, kéo follow/tim nhảy vọt trong ngày.
  * `🚀 TIỀM NĂNG` (`is_potential`): `not is_trending and ((h_val >= 50 and f_val <= 30) or (delta_h >= 30))`.
    - *Bản chất:* Nick mầm non (follower <= 30) nhưng tương tác cao (tim >= 50) hoặc đang có đà tăng tim tốt (+30). Video có sức hút giữ chân người xem tốt, chớm viral, có tiềm năng bùng nổ thành `ĐỀ XUẤT` ở các video tiếp theo.
- **Luật tương hỗ độc quyền (Mutual Exclusivity Invariant):**
  * `is_potential` BẮT BUỘC có điều kiện `not is_trending`. Tuyệt đối không để 1 nick dính đồng thời cả 2 nhãn `🔥 ĐỀ XUẤT` và `🚀 TIỀM NĂNG` gây nhiễu giao diện.
  * Test hồi quy: Bắt buộc có assertion `assert not (item["is_trending"] and item["is_potential"])` trên toàn bộ danh sách kết quả `get_farm_data`.
- **UI Toolbar Discovery Pitfall:**
  * Khi tách logic backend, nếu thanh Toolbar chỉ có nút lọc `🔥 Cắn Đề Xuất` (`setView('trend')`), người vận hành sẽ không tìm thấy chỗ xem riêng nick Tiềm Năng.
  * Hiện trường: Xem tại `Toàn Bộ Farm` / `Chỉ LIVE` theo badge màu xanh `🚀 TIỀM NĂNG`, hoặc bấm `💖 BXH Tim`.
  * Chuẩn mở rộng UI: Khi bổ sung phân loại tài khoản mới, phải đồng bộ trọn bộ: (1) Logic backend loại trừ tương hỗ, (2) Badge định danh màu sắc riêng, (3) Nút lọc nhanh Toolbar / thẻ đếm KPI.

## 8. Tách Bạch Chu Kỳ Quét Web vs Tiến Độ Ca Nuôi Bot Trên Dashboard (Following Reconciliation Time-Window Decoupling)
- **Bản chất kiến trúc cào Web & ca nuôi trên Phone Farm:**
  * **Cào tổng toàn Farm (Daily Full-Farm Scrape):** Chạy duy nhất 1 lần/ngày vào rạng sáng (04:00 hoặc 07:00) qua kho proxy 4G xoay vòng để tiết kiệm băng thông proxy và chống checkpoint tài khoản trên quy mô 1.000+ nick. Mốc delta `+N Following (hoặc Follower/Tim)` cào về chính là **kết quả tích lũy sau tất cả các ca nuôi của ngày hôm trước**.
  * **Cào cục bộ theo ca ($T_0$ Pre-Session Scrape):** Chạy ngay trước mỗi ca nuôi cho riêng các nick tham gia ca đó, phục vụ đối soát $T_1 - T_0$ chống TikTok silent drop (nhả follow ngầm) của chính ca đó.
  * **Các ca nuôi trong ngày:** Chạy rải rác từ sáng đến tối (Ca sáng, Ca chiều, Ca tối) và ghi nhận nhật ký vào `session_action_stats` / `daily_account_actions` với `target_date = ngày_hôm_nay`.
- **Cạm bẫy ghép chung mốc ngày (Time-Window Mismatch Trap):**
  * Ghép chung một dòng `🔗 Nội bộ: +0 | 📈 Tổng tăng: +126` trên cùng thẻ KPI Following gây hiểu lầm nghiêm trọng và phi logic:
    1. **Nghịch lý sáng sớm:** `Tổng tăng +126` (thành quả các ca hôm qua) đặt cạnh `Nội bộ +0` (ngày mới hôm nay chưa chạy ca nào) khiến người dùng tưởng 126 follow đó toàn là follow dạo, bot không chạy nick nội bộ nào.
    2. **Nghịch lý chiều tối:** Khi bot chạy xong hôm nay được +150 lượt nội bộ, nhưng Web cào chưa quét lại vẫn giữ +126, thẻ hiện `Nội bộ: +150 | Tổng tăng: +126` (số con lớn hơn số tổng, gây lú lẫn).
- **Quy chuẩn hiển thị 2 tầng bắt buộc trên thẻ KPI Following:**
  * Tách bạch rõ ràng 2 tầng độc lập:
    - **Tầng 1 (📊 Đối soát hôm qua / chu kỳ trước):** So sánh số lượt Bot đã bấm hôm qua với số Web ghi nhận tăng:
      `📊 Đối soát hôm qua: Bot +{total_internal_yesterday} ➔ Web +{total_delta_following}`
    - **Tầng 2 (⚡ Tiến độ hôm nay):** Phản ánh số lượt bot đã bấm trong các ca của ngày hôm nay (nhảy số realtime theo từng ca nuôi hoàn tất):
      `⚡ Tiến độ hôm nay: Bot +{total_internal_follows} lượt`
  * Đồng bộ trọn gói: Backend `get_farm_data()` (truy vấn `row_prev[0]` cho yesterday và `max_dt` cho today), template HTML render ban đầu, và JS auto-refresh 30s client-side.

