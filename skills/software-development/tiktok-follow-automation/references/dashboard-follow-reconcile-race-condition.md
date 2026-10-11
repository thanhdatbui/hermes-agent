# Dashboard Following Reconcile Race Condition & Telemetry Diagnostic

## Ba Hiện Tượng Lệch Pha Thường Gặp
1. **Lệch thấp:** `ĐÃ FOLLOW: +13` nhưng `🔗 Nội bộ: +0` (hoặc thấp hơn).
2. **Lệch cao (Nội bộ bị nhân bản gấp 2-3 lần):** `ĐÃ FOLLOW: +13` nhưng `🔗 Nội bộ: +42`; hoặc `ĐÃ FOLLOW: +4` nhưng `🔗 Nội bộ: +8`.
3. **Lệch nhẹ ở Thẻ Tổng KPI:** `Bot +18 lượt` vs `Web Tổng tăng: +16`.

## Bốn Nguyên Nhân Gốc Rễ

### Nguyên nhân 1: Leak Follow từ Popup Gợi Ý Bạn Bè / Danh Bạ trong Feed Session (`benign_popup.py`)
Khi tài khoản **nghỉ follow hoặc chưa đủ video** (`organic-rest-day-pure-feed`, `under-6-videos-follow-disabled`), runner không hề phát lệnh follow chéo nội bộ nào (`followed_count = 0`), bảng `daily_account_actions` ghi nhận `+0`. Tuy nhiên số `following` trên TikTok vẫn tăng (+1, +2):
- **Cơ chế gây leak:** Trong `automation-core/src/automation_core/tiktok/benign_popup.py`, bộ xử lý popup `detect_contact_follow_suggestion` (gợi ý kết bạn/danh bạ, thường xuất hiện khi lướt tab Bạn bè/Friends) có policy:
  `pre_action="tap_follow_button"` (hoặc trả về `follow_target` nếu không có nút X đóng).
- **Hiện trường kiểm chứng:**
  + So sánh file `profile_identity/ui.xml` ở đầu ca (ví dụ: `Đã follow = 0`) với `verify_profile/ui.xml` ở cuối ca (ví dụ: `Đã follow = 1`).
  + Kiểm tra `log.jsonl` của máy: tìm step `contact_follow_suggestion` hoặc `dismiss_not_interested_button`, tọa độ tap rơi vào nút Follow của card gợi ý bạn bè.
- **Xử lý (Đã chuẩn hóa 2026-10-10, commit `590a831` & `bae428f`):**
  + Trong `benign_popup.py`: Gỡ bỏ hoàn toàn `pre_action="tap_follow_button"` và nhánh trả về `follow_target` trong `detect_contact_follow_suggestion`. Handler chỉ được phép đóng / bỏ qua (`dismiss_not_interested_button` hoặc icon Close X `dismiss_close_x`).
  + Trong `tiktok_popup.py`: Gỡ bỏ vòng lặp `while followed_count < 2` trong `_dismiss_follow_friends_popup`, chỉ tìm nút đóng X để đóng trực tiếp, không tap follow bất kỳ tài khoản nào.
  + **Tách bạch Feed vs Follow chéo:** Khóa popup hoàn toàn KHÔNG ảnh hưởng đến follow chéo nội bộ, vì `follow_runner` chỉ chạy qua Mode 1 (Search username → Profile → Follow) và Mode 2 (Follow từ danh sách Followers), không bao giờ phụ thuộc vào popup.
  + **Bảo vệ Trust & Persona người thật:** Người dùng thật luôn có phản xạ bấm đóng/bỏ qua các popup gợi ý danh bạ/bạn bè phiền phức. Việc đóng popup là hành vi tự nhiên 100%, bảo vệ nick yếu không bị TikTok gắn nhãn clicker bot, không bị loãng niche, và chặn đứng nguy cơ bị thuật toán silent un-follow.

### Nguyên nhân 2: Race Condition giữa Snapshot Crawler và Watchdog Chốt Ca
1. **Thời điểm cào Snapshot toàn Farm:**
   - Hệ thống crawler snapshot toàn farm (`snapshots` table) cào định kỳ (thường vào sáng sớm, ví dụ 07:04:09).
   - Snapshot đọc trực tiếp số `following` công khai từ profile web của TikTok, ghi nhận mức tăng ngay lập tức (`delta_following = +12`).
2. **Thời điểm Watchdog chốt sổ Ca Nuôi/Follow:**
   - Ca chạy nuôi nick / follow chéo (ví dụ: ca sáng 06:00 - 07:35:55) ghi nhận chi tiết follow từng máy vào `follow_result.json`.
   - Bảng `session_account_actions` và bảng tổng hợp ngày `daily_account_actions` trong SQLite (`tiktok_tracker.db`) **CHỈ ĐƯỢC WATCHDOG GHI NHẬN KHI CA CHẠY KẾT THÚC HOÀN TOÀN** (hàm `save_session_action_stats` và `reconcile_cluster_following` chạy lúc ~07:35:58).
3. **Cửa sổ lệch pha (Race Window):**
   - Trong khoảng thời gian ca đang chạy (06:00 - 07:35), snapshot đã quét thấy following tăng (+12), nhưng bảng `daily_account_actions` của ngày đó chưa có bản ghi (hoặc chưa cập nhật máy này).
   - Dashboard truy vấn:
     `SELECT username, internal_follows FROM daily_account_actions WHERE target_date = ?`
     Do chưa có dữ liệu trong ngày, Dashboard fallback về `0` (`🔗 Nội bộ: +0`).

### Nguyên nhân 3: Duplicate Session Telemetry / Test Session Keys trong Database (Nhân bản số liệu từng nick)
1. **Cơ chế khóa chính và hàm tổng hợp ngày:**
   - Bảng chi tiết `session_account_actions` có khóa chính là `PRIMARY KEY (session_key, cluster, username)`.
   - Script `feed_session_watchdog.py` chốt sổ và tổng hợp ra bảng ngày `daily_account_actions` bằng câu lệnh SQL:
     ```sql
     INSERT INTO daily_account_actions (target_date, username, may, internal_follows, updated_at)
     SELECT target_date, username, MAX(may), SUM(internal_follows), MAX(updated_at)
     FROM session_account_actions
     WHERE target_date = ?
     GROUP BY target_date, username
     ON CONFLICT(target_date, username) DO UPDATE SET
         internal_follows = excluded.internal_follows,
         may = excluded.may,
         updated_at = excluded.updated_at
     ```
2. **Hiện tượng nhân bản số liệu (Multiplying Bug):**
   - Khi có kỹ sư hoặc worker chạy thử nghiệm test runner, debug probe, hoặc script nháp với các `session_key` không đúng quy chuẩn ca (ví dụ `test_check`, `2026-10-11_ca1_p1` thay vì chuẩn `YYYY-MM-DD_caX_phienY`), các bản ghi này sẽ được chèn độc lập (không bị conflict do khác `session_key`).
   - Đến khi Watchdog chạy tổng hợp `SUM(internal_follows)` theo `target_date`, các lượt follow trong phiên test và phiên thật bị cộng dồn lại với nhau:
     - `@tienpham7676`: 14 (thật) + 14 (nháp p1) + 14 (test) = **42**! (Thực tế bot chạy chỉ 14).
     - `@trn.m.m620`: 2 (p1) + 2 (p2) + 2 (nháp) + 2 (test) = **8**! (Thực tế bot chạy chỉ 4).
   - Trong khi đó, thẻ tổng KPI trên Header đọc từ `session_action_stats` (chỉ ghi nhận 2 phiên thật là 16 + 2 = 18), dẫn đến nghịch lý: Toàn farm bot chạy 18 lượt nhưng 1 nick riêng lẻ hiển thị đã follow 42 lượt!
3. **Cách khắc phục:**
   - **Tự động bằng script:** Chạy `python scripts/reconcile_and_clean_test_telemetry.py --fix` (tự động sao lưu DB, phát hiện các session key bất thường và recalculate `daily_account_actions`).
   - **Thao tác thủ công:** Xóa các bản ghi rác có `session_key` không hợp lệ (`test_check`, `..._p1`) trong `session_account_actions`:
     ```sql
     DELETE FROM session_account_actions WHERE session_key IN ('test_check', '2026-10-11_ca1_p1');
     ```
   - Chạy lại lệnh tổng hợp `daily_account_actions` từ `session_account_actions` cho ngày hiện tại để số liệu trên Dashboard tự động hồi phục về đúng giá trị thực tế.

### Nguyên nhân 4: Chênh Lệch Giữa Click Bot và Tăng Thật Web (Bot +18 vs Web +16)
1. **Bản chất đo lường:**
   - **Bot follow (Tiến độ hôm nay):** Đếm số lần bot tap nút Follow thành công trên UI app (`followed_count`).
   - **Web tăng thật (Tổng Đã Follow):** Lấy hiệu số `delta_following` của trường `following` cào trực tiếp từ profile TikTok công khai giữa snapshot hôm nay và snapshot hôm qua.
2. **Lý do có khoảng lệch 1-3 lượt:**
   - **Nhả follow (Silent un-follow / Shadow drop):** TikTok có cơ chế rate limit hoặc anti-spam ngầm: khi tài khoản bấm follow quá nhanh hoặc IP bị soi, nút Follow trên UI máy hiển thị thành công nhưng sau 30s - vài phút server TikTok tự động hủy kết nối follow mà không thông báo lỗi.
   - **Độ trễ CDN Cache của TikTok:** Counter `following` trên trang công khai của TikTok đôi khi có độ trễ cập nhật vài phút đến 1 tiếng so với hành động thực tế trên app.

## Quy trình chẩn đoán (CẤM đoán mò "follow tự nhiên")
1. **CẤM TUYỆT ĐỐI phán đoán ẩu "đây là follow tự nhiên / kênh ngoài"** khi user đã cấu hình tắt follow tự nhiên trong feed runner.
2. **Kiểm tra thời điểm:**
   - So sánh `snapshots.timestamp` mới nhất với mtime của ca chạy (`runtime/kibe/live/<YYYY-MM-DD>/<run>/...`).
   - Kiểm tra ca chạy của máy/nick đó đã kết thúc (có `summary.txt`, `follow_result.json`) và Watchdog đã hoàn tất gửi báo cáo Telegram chưa.
3. **Kiểm tra nguồn tin cậy (Source of Truth):**
   - Đọc trực tiếp `follow_result.json` của máy trong thư mục run:
     Kiểm tra `followed_count`, danh sách `followed`, `mode2_followed_count` để xác nhận số lượt follow chéo thực tế do script thực hiện.
   - Kiểm tra SQLite `daily_account_actions` và `session_account_actions`:
     Nếu ca đã chốt nhưng Dashboard chưa cập nhật, kiểm tra cache TTL (15s) hoặc reload web.
