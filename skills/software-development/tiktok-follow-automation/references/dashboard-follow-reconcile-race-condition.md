# Dashboard Following Reconcile Race Condition & Telemetry Diagnostic

## Năm Hiện Tượng Lệch Pha Thường Gặp
1. **Lệch thấp:** `ĐÃ FOLLOW: +13` nhưng `🔗 Nội bộ: +0` (hoặc thấp hơn).
2. **Lệch cao (Nội bộ bị nhân bản gấp 2-3 lần):** `ĐÃ FOLLOW: +13` nhưng `🔗 Nội bộ: +42`; hoặc `ĐÃ FOLLOW: +4` nhưng `🔗 Nội bộ: +8`.
3. **Lệch tam giác giữa 3 bảng số liệu (Lịch sử ngày vs Đối soát KPI vs Web):** Ví dụ: Thống kê theo ngày báo `+22 lượt (6/7 nick)`, Thẻ KPI Header báo `Bot +18 lượt`, nhưng Web chỉ ghi nhận `+16 lượt`.
4. **Quy ước hiển thị Cột Nick (Thống Kê Ngày & Tuần) dạng `Thành công / Tổng chạy`:** Loại bỏ nghịch lý thị giác khi nick bị nhả/0 lượt vẫn tính trong tổng số nick chạy (ví dụ `1/2 nick`, `10/17 nick`).
5. **Lệch cửa sổ snapshot khi quét bù ca cũ (Backfill uncapped window):** Báo cáo ca cũ nhưng số liệu web bốc trúng snapshot hiện tại sau 7 ngày, tạo lệch ảo khủng (+62).
6. **Lệch âm độc lập do TikTok Shadow Unfollow / Silent Action Block trên nick non:** Script báo 2 lượt (do Optimistic UI trên danh sách), nhưng cả counter trên UI Profile thiết bị lẫn TikTok Web đều là 0.

## Các Nguyên Nhân Gốc Rễ

### Nguyên nhân 0: Phân Biệt Ba Nguồn Dữ Liệu Khi Đối Soát Follow (22 vs 18 vs 16)
Khi đọc Dashboard, cần phân biệt rõ 3 nguồn telemetry khác nhau cho cùng một ngày:
1. **Bảng "Thống Kê Theo Ngày" (`daily_account_actions` qua `follow_health_helper.py`):**
   - Query: 
     ```sql
     SELECT target_date, 
            SUM(internal_follows) as tot_fl, 
            COUNT(DISTINCT CASE WHEN internal_follows > 0 THEN username END) as succ_cnt,
            COUNT(DISTINCT username) as total_cnt 
     FROM daily_account_actions GROUP BY target_date
     ```
   - Bản chất: Gom **toàn bộ số lần bot tap Follow thành công trên UI app** của từng nick xuyên suốt cả ngày, bao gồm cả ca chính (follow chéo) lẫn các ca phụ (lướt feed phát sinh follow lẻ).
   - **Định nghĩa cột "Nick" (Quy chuẩn `Thành công / Tổng chạy`):**
     + Hiển thị dạng phân số `succ_cnt/total_cnt` (ví dụ `1/2 nick`, `10/17 nick`, `6/7 nick`).
     + Phản ánh rõ ràng: tử số là **số nick thực sự có đóng góp follow thành công**, mẫu số là **tổng số nick được điều phối chạy trong ngày** (bao gồm cả các nick bị TikTok nhả ngay từ đầu / `FOLLOW_FAILED` khiến `internal_follows = 0`).
     + Loại bỏ hoàn toàn nghịch lý thị giác (ví dụ ngày 13/10 thấy `+1 lượt` mà ghi `2 nick`, nay hiển thị `1/2 nick` giúp người vận hành hiểu ngay là 1 nick thành công trên 2 nick chạy, có 1 nick bị nhả nút).
   - Ví dụ (ngày 11/10): `14 (tienpham M28) + 4 (trn.m.m M26) + 1 (debidxbr M78) + 1 (v.th.tho M44) + 1 (florence M38) + 1 (tyrus M62) + 0 (cleor M76) = 22 lượt` trên `6/7 nick` (6 nick thành công, 1 nick bị nhả về 0).
2. **Chỉ số "Bot" ở Thẻ Đối Soát Header (`session_action_stats`):**
   - Query: `SELECT SUM(internal_follows) FROM session_action_stats WHERE target_date = ?`.
   - Bản chất: Chỉ tính tổng lượt follow từ **các phiên follow chéo trọng điểm có chốt sổ ca nuôi chính** (ví dụ Ca 1: Phiên 1 được 16, Phiên 2 được 2 => Tổng = 18 lượt). Các ca lướt feed thông thường (Ca 2, Ca 3) không đặt mục tiêu follow chéo nên `internal_follows` của ca ghi nhận 0.
3. **Chỉ số "Web Tổng tăng" (`snapshots` qua `get_farm_history`):**
   - Query: Delta trường `following` thực tế cào từ profile công khai của TikTok giữa 2 ngày liên tiếp.
   - Bản chất: Số follow thực tế TikTok ghi nhận công khai. Con số này thường **thấp hơn số lượt bot bấm** do:
     - **Silent un-follow / Shadow drop:** Bot bấm thành công trên app nhưng TikTok quét nhả ngầm hoặc không lưu vào counter (như `@tienpham7676` bot bấm 14 nhưng web chỉ nhận 13).
     - **Tụt tự nhiên trên nick rảnh:** Các nick rảnh không chạy hôm đó nhưng bị tụt `-1` do nick nó từng follow trước đây bị TikTok ban/xóa.
     - Kết quả: `13 + 4 - 1 = +16 lượt`.

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

### Nguyên nhân 2: Race Condition giữa Snapshot Crawler và Watchdog Chốt Ca (Bẫy Lệch Bù Trừ P1 Âm -> P2 Dương)
1. **Thời điểm cào Snapshot toàn Farm:**
   - Hệ thống crawler snapshot toàn farm (`snapshots` table) cào định kỳ (thường vào sáng sớm, ví dụ 07:04:09).
   - Snapshot đọc trực tiếp số `following` công khai từ profile web của TikTok, ghi nhận mức tăng ngay lập tức (`delta_following = +12`).
2. **Thời điểm Watchdog chốt sổ Ca Nuôi/Follow:**
   - Ca chạy nuôi nick / follow chéo (ví dụ: ca sáng 06:00 - 07:35:55) ghi nhận chi tiết follow từng máy vào `follow_result.json`.
   - Bảng `session_account_actions` và bảng tổng hợp ngày `daily_account_actions` trong SQLite (`tiktok_tracker.db`) **CHỈ ĐƯỢC WATCHDOG GHI NHẬN KHI CA CHẠY KẾT THÚC HOÀN TOÀN** (hàm `save_session_action_stats` và `reconcile_cluster_following` chạy lúc ~07:35:58).
3. **Cửa sổ lệch pha (Race Window) & Bẫy Lệch Bù Trừ Giữa 2 Phiên Liên Tiếp (P1 Âm -> P2 Dương):**
   - **Hiện tượng:** Ở Phiên 1, watchdog báo lệch âm lớn (-20 lượt, ví dụ M4 báo script 4 web 0, M26 script 8 web 0). Người vận hành nghi ngờ bot "ăn nhả rồi vẫn cố chạy". Nhưng ngay sang Phiên 2, watchdog lại báo ngược lại: Web tăng vượt Script (M4 script 1 web 4 lệch +3, M26 script 0 web 8 lệch +8)!
   - **Cơ chế gốc rễ (Snapshot Timestamp Lag vài chục giây):**
     * Khi Phiên 1 chốt lúc `08:00:00`, câu lệnh SQL của watchdog lọc `WHERE timestamp <= '08:00:00'`.
     * Tuy nhiên tiến trình cào profile web sau ca thực tế ghi nhận vào database lúc `08:00:38` (chậm hơn mốc chặn trần đúng 38 giây).
     * Watchdog Phiên 1 bị hụt snapshot này, fallback về snapshot đầu ca lúc `07:04:26` (lúc bot chưa cày xong). Cũ trừ cũ ra `0 lượt` -> Báo lệch âm ảo!
     * Sang Phiên 2 (chốt lúc 09:25): Watchdog Phiên 2 bốc trúng snapshot `08:00:38` (hoặc `09:25:56`), khiến Phiên 2 "ăn đền" toàn bộ số follow tích lũy từ Phiên 1 -> Báo lệch dương ảo!
   - **Kỷ luật đối soát bất biến:**
     * Khi thấy P1 âm và P2 dương trên cùng dàn nick có `status=success`: Tuyệt đối KHÔNG vội vàng quy chụp là bot ăn nhả cố chạy hay TikTok shadow-drop.
     * BẮT BUỘC đối soát **Tổng tích lũy 2 phiên**: Lấy snapshot sau P2 (`09:25:56`) trừ thẳng snapshot trước P1 (đầu ngày) và so với `Tổng bot bấm (P1 + P2)`. Nếu tổng khớp hoặc chỉ lệch 1-2 lượt (M4: 5/5, M26: 8/9, M36: 8/7, M37: 13/11) thì khẳng định 100% nick đã ăn follow thật vào profile, độ lệch từng phiên chỉ là lệch pha thời điểm cào snapshot.
   - **Giải pháp kiến trúc dứt điểm (Đã vá 2026-10-15, commit `ccec6b9`):**
     * Trong `feed_session_watchdog.py` (`reconcile_cluster_following`), bổ sung **Grace Buffer 10 phút** (`_buffer_iso(iso_val, minutes=10)`) cho cả `session_end_iso` và `session_start_iso`:
       - `query_end_iso = _buffer_iso(session_end_iso, 10)` (ví dụ: `08:00:00` -> `08:10:00`).
       - `query_start_iso = _buffer_iso(session_start_iso, 10)`.
     * **Nguyên lý bảo đảm (Continuous Balance Invariant):**
       - Snapshot chốt ca ghi lúc `08:00:38` nằm gọn trong `query_end_iso` của P1 (`<= 08:10:00`), được P1 thu nạp trọn vẹn làm `latest_row`.
       - Đồng thời snapshot `08:00:38` cũng nằm trong `query_start_iso` của P2 (`<= 08:10:00`), được P2 chọn làm `baseline_row`.
       - `latest_row(P1) == baseline_row(P2)` được khóa cứng trong SQL, triệt tiêu 100% hiện tượng P1 thiếu 20 và P2 thừa 20 lượt.
   - **Các cạm bẫy triển khai thực tế & Tiêu chuẩn Closeout (Production Hardening 15/10/2026):**
     * **Bẫy regex phiên (Phiên 10+ bị nhầm là Phiên 1):** Nếu dùng `phien1 in session_key` hoặc `\b` đơn giản, `phien10` sẽ bị dính `1` và coi là Phiên 1, khiến baseline không được buffer. Phải dùng regex negative lookahead:
       `has_p1 = bool(re.search(r"[_.-]?(?:phien|session|p)[\s_.-]*1(?![0-9])", s_lower))`
       `has_later_phien = bool(re.search(r"[_.-]?(?:phien|session|p)[\s_.-]*([2-9]|\d{2,})", s_lower))`
       Fail-safe default: Nếu `session_key` rỗng hoặc không xác định được phiên, mặc định là P1 (giữ nguyên start_iso, cấm buffer tiến về tương lai).
     * **Bẫy so sánh chuỗi ISO:** So sánh `query_start_iso >= session_end_iso` bằng string comparison rất dễ văng lỗi do lệch format (T vs space, microsecond, timezone). Bắt buộc parse ra `datetime` trước khi so sánh guard.
     * **Telemetry đo đạc (`RECONCILE_METRICS`):** Thay vì chỉ log debug vô định hình, bổ sung module dict đếm số lần: `buffer_applied`, `buffer_capped` (vượt 23:59:59 EOD), `guard_triggered` (start >= end fallback), và `parse_fallback`. Cung cấp hàm `reset_reconcile_metrics()` để cô lập test.
     * **Đồng bộ song hành `scripts/` và `hermes_cron/`:** Khi watchdog được triển khai ở 2 vị trí, bắt buộc duy trì 100% source code identity và có test kiểm tra `inspect.getsource()`.
     * **Kỷ luật ngân sách dòng (Line Budget Gate):** `feed_session_watchdog.py` bị khóa ngân sách cứng `<= 1450` dòng (`test_feed_session_watchdog_line_budget`). Mọi hàm thêm vào phải tinh gọn.

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

### Nguyên nhân 4: Chênh Lệch Giữa Click Bot và Tăng Thật Web (Bot +18 vs Web +17) & Quy Tắc Khoanh Vùng Cohort Đối Soát
1. **Bản chất đo lường:**
   - **Bot follow (Tiến độ hôm nay):** Đếm số lần bot tap nút Follow thành công trên UI app (`followed_count`).
   - **Web tăng thật (Tổng Đã Follow):** Lấy tổng số lượt biến động following thực tế trên profile công khai giữa snapshot hôm nay và snapshot hôm qua của **CHÍNH CÁC NICK CÓ THAM GIA ĐI FOLLOW HÔM NAY**.
2. **Quy tắc bất biến (Business Invariant) khi đối soát Tiến độ / Tổng tăng:**
   - **Khoanh vùng đúng Cohort tham gia follow:** CHỈ đối soát các nick hôm nay có phát sinh hành động đi follow (`internal_followed > 0`). Các nick rảnh/nghỉ không chạy follow hôm nay (như nick M60 `@iyoqytawkzq` bị tụt `-1` do tài khoản nó từng follow trước đây bị TikTok ban/xóa) TUYỆT ĐỐI KHÔNG ĐƯỢC gộp vào cohort đối soát hôm nay. Việc gộp nick ngoài luồng làm sai lệch hoàn toàn hiệu quả của ca bot chạy.
   - **CẤM dùng `max(0, ...)` để che giấu lỗi nhả follow:** Đối với chính các nick có tham gia chạy follow hôm nay, nếu bị TikTok quét nhả follow (delta âm hoặc thấp hơn số bot bấm):
     **BẮT BUỘC PHẢI TRỪ THẲNG VÀO TỔNG DELTA ĐỐI SOÁT** (`total_delta_following += delta_following`).
     - Ví dụ: Nick A đi follow tăng +13 (bot bấm 14, nhả 1 -> tính 13); Nick B đi follow tăng +4 (bot bấm 4 -> tính 4); Nick D đi follow bị nhả -2 (bot bấm 5, TikTok quét nhả 7 -> delta = -2) -> Tổng đối soát Web = `13 + 4 + (-2) = 15`. Lượt nhả trên nick chạy follow là hao hụt thật, phải phản ánh trung thực để phát hiện nick bị shadow drop / rate limit.
   - **Khi không có nick nào chạy follow trong ngày (`has_active_follow == False`):** Hệ thống fallback về tính tổng delta của toàn bộ dàn nick để duy trì telemetry tổng thể của farm.
3. **Lý do có khoảng lệch 1-2 lượt giữa Bot và Web (ví dụ: Bot +18 vs Web +17):**
   - **Nhả follow (Silent un-follow / Shadow drop):** TikTok có cơ chế rate limit hoặc anti-spam ngầm: khi tài khoản bấm follow quá nhanh hoặc IP bị soi, nút Follow trên UI máy hiển thị thành công nhưng sau 30s - vài phút server TikTok tự động hủy kết nối follow mà không thông báo lỗi (như `@tienpham7676` bot bấm 14 nhưng Web chỉ ghi nhận 13).
   - **Độ trễ CDN Cache của TikTok:** Counter `following` trên trang công khai của TikTok đôi khi có độ trễ cập nhật vài phút đến 1 tiếng so với hành động thực tế trên app.

### Nguyên nhân 5: Lệch Cửa Sổ Snapshot Khi Watchdog Quét Bù Ca Cũ (Backfill Uncapped Snapshot Window)
1. **Hiện tượng nhận biết:**
   - Watchdog gửi báo cáo một ca (ví dụ `Ca 1 - Phiên 1/2 (Sáng) hoàn tất (Row 1)`), số liệu đối soát Web tăng vọt đột biến (`+129 Following thật | Lệch +62 so với script báo 67`).
   - Hàng loạt máy có độ lệch lớn: M4 script 14 -> web 32 (lệch +18), M37 script 8 -> web 26 (lệch +18), M41 script 7 -> web 17 (lệch +10), các máy nghỉ không chạy (script 0) vẫn thấy web tăng (+5, +2).
   - Thoạt nhìn rất dễ lầm tưởng bot bị "chạy loạn follow tự nhiên", nhưng thực tế là do lỗi đối soát snapshot.
2. **Cơ chế gây lỗi (Backfill Snapshot Window Bug):**
   - Khi watchdog khởi động lại hoặc có ca cũ trong cửa sổ retention (7 ngày) chưa nằm trong `follow_session_reported.json`, nó sẽ kích hoạt backfill chạy lại các phiên cũ (ví dụ `2026-10-05_ca1_phien1`).
   - Trong `feed_session_watchdog.py` (`reconcile_cluster_following`):
     + Mốc bắt đầu (`baseline_row`): Lấy snapshot với điều kiện `timestamp <= session_start_iso` (ví dụ `2026-10-05 06:00:00`, trả về snapshot ngày 04/10).
     + Mốc kết thúc (`latest_row`): Truy vấn `SELECT following, timestamp FROM snapshots WHERE LOWER(username) = ? ORDER BY timestamp DESC LIMIT 2` **HOÀN TOÀN KHÔNG CÓ ĐIỀU KIỆN CHẶN TRẦN** `timestamp <= session_end_iso`.
     + Kết quả: `latest_row` luôn bốc trúng snapshot mới nhất của ngày hiện tại (12/10), khiến `web_delta = latest_fl - prev_fl` đo lường mức tăng trưởng tích lũy của **suốt 7 ngày (04/10 đến 12/10)**, rồi đem so với số lượt follow của **duy nhất 1 phiên cũ (05/10)**.
   - Thêm vào đó, tiêu đề báo cáo Telegram không in `target_date` (`Ca 1 - Phiên 1/2 (Sáng)` thay vì `[2026-10-05] Ca 1...`), khiến người vận hành nhầm lẫn là ca của ngày hôm nay.
3. **Quy tắc xử lý & phòng ngừa:**
   - **Bắt buộc chặn trần snapshot:** Mốc kết thúc `latest_row` trong mọi hàm reconcile đối soát phiên bắt buộc phải có điều kiện `AND timestamp <= session_end_iso` (hoặc chặn trần ở cuối khung giờ phiên của ngày đang xét).
   - **Gắn date tag trên tiêu đề watchdog:** Mọi thông báo Telegram của session watchdog bắt buộc phải chứa `[target_date]` để phân biệt rành mạch ca realtime hôm nay với ca backfill lịch sử.

### Nguyên nhân 6: Lệch Phạm Vi Báo Cáo Phiên Độc Lập vs Tổng Ngày Database (Session Watchdog Report vs Daily DB Aggregate)
1. **Hiện tượng nhận biết:**
   - Người dùng thấy trên Database (`daily_account_actions` hoặc Dashboard KPI "Tiến độ hôm nay: Bot +1 lượt") báo có **1 lượt follow**, nhưng tin nhắn báo cáo Telegram vừa nhận lại báo **0 lượt follow** (`Follow chéo (0 lượt follow)`).
2. **Cơ chế lệch phạm vi (Session Scope vs Daily Aggregate):**
   - Farm chia 1 ca thành nhiều phiên chạy độc lập (ví dụ Ca 1 gồm Phiên 1 lúc 06:00 và Phiên 2 lúc 08:00).
   - Watchdog (`feed_session_watchdog.py` / `follow_session_watchdog.py`) gửi báo cáo **THEO TỪNG PHIÊN RIÊNG BIỆT (Session-based)**: mỗi khi một phiên kết thúc sẽ gửi đúng 1 thông báo cho phiên đó.
   - Lượt follow thành công đã diễn ra ở **Phiên 1** (ví dụ Máy 29 follow thành công 1 nick `@thanh.h.dng00` lúc 06:02) và đã được chốt sổ gửi báo cáo ở Phiên 1.
   - Ở **Phiên 2**, Máy 29 gặp anchor bị nhả nút sau vuốt (`FOLLOW_FAILED`) $\rightarrow$ dừng an toàn session với `followed_count = 0`. Watchdog gửi báo cáo Phiên 2: `Follow chéo (0 lượt follow)` và xếp Máy 29 vào nhóm `Nhả liền (0 lượt)`.
   - Trong khi đó, bảng `daily_account_actions` và Dashboard là **tổng hợp tích lũy cả ngày** (`GROUP BY target_date, username` lấy `SUM(internal_follows)`), vẫn ghi nhận 1 lượt của Phiên 1.
3. **Quy trình chẩn đoán O(1):**
   - Query nhanh bảng `session_action_stats` theo `target_date` để xem chi tiết từng phiên:
     ```sql
     SELECT session_key, cluster, internal_follows, created_at FROM session_action_stats WHERE target_date = ?;
     ```
   - Kiểm tra thư mục run thực tế của từng phiên trong `runtime/kibe/live/<YYYY-MM-DD>/` (file `follow_result.json` của máy liên quan) để xác định chính xác phiên nào sinh ra lượt follow và phiên nào bị dừng do `FOLLOW_FAILED`.

### Nguyên nhân 7: Lệch Âm Độc Lập Do TikTok Silent Unfollow / Shadow Action Block Trên Nick Non (Client Optimistic UI vs Server Drop)
1. **Hiện tượng nhận biết:**
   - Watchdog báo lệch âm trên 1 máy cụ thể (ví dụ: `M23 (@tranngan8642) : script 2 lượt - web 0 lượt - lệch (-2)`).
   - Nick này không bị `FOLLOW_FAILED` hay ngắt phiên ngay tại bước follow (script vẫn báo `status: OK, followed: 2`), nhưng web cào trước và sau ca đều ghi nhận 0 lượt tăng (`delta = 0`).
   - Khác với Nguyên nhân 2 (Race condition P1 âm -> P2 bù dương): Ở trường hợp này, **không hề có độ trễ cào hay bù trừ dương ở P2**.
2. **Bản chất kỹ thuật (Client Optimistic UI vs Server-Side Action Block):**
   - **Optimistic UI trên client:** Khi bot tap nút Follow trên danh sách (Mode 2) hoặc trên profile, app TikTok đổi ngay giao diện sang trạng thái `Đang follow` (Following) trên client trước khi server xác nhận. Runner kiểm tra nút sau tap thấy nút đã đổi màu nên ghi nhận thành công (`followed_count = 2`).
   - **Server TikTok âm thầm loại bỏ (Silent Drop / Shadow Unfollow):** Đối với các nick non (Rookie / Row 7-8 chưa graduate, đang probation) hoặc tài khoản bị chấm điểm trust thấp / IP bị soi:
     * Server TikTok tiếp nhận request nhưng không tăng trường `following` trên database máy chủ.
     * Khi nick quay về màn hình Profile cá nhân (`verify_profile`), counter **"Đang follow"** trên giao diện vẫn là **0**!
     * Web scraper cào dữ liệu từ server TikTok cũng trả về **0**.
3. **Quy trình kiểm chứng hiện trường O(1) để phân định Race Condition vs Shadow Drop:**
   - **Bước 1: Đọc XML Profile của nick ở cuối ca chạy:**
     Kiểm tra `runtime/kibe/live/<YYYY-MM-DD>/<run_id>/machines/machine_<N>/<run_id>/artifacts/.../verify_profile/ui.xml`.
     Tìm node `resource-id` có nhãn `Đã follow` (hoặc `id/t93`) và node số lượng ngay phía trên (`id/t94`):
     ```xml
     <node resource-id="...:id/t94" text="0" bounds="[88,675][388,741]" />
     <node resource-id="...:id/t93" text="Đã follow" bounds="[88,735][388,783]" />
     ```
   - **Bước 2: Đối soát:**
     * Nếu node `text="0"` ngay trên màn hình thiết bị của máy: **Chứng minh 100% tài khoản bị TikTok server shadow-drop** (server không chấp nhận lượt follow), không phải do scraper cào chậm hay lỗi watchdog.
     * Nếu node `text="2"` trên thiết bị nhưng Web cào `0`: Là độ trễ cache CDN của TikTok Web hoặc scraper cào trước khi sync server (xem Nguyên nhân 2 & 4).
   - **Bước 3: Ứng xử vận hành:**
     * Không can thiệp ADB bấm tay.
     * Giữ nguyên nick ở chế độ dưỡng sinh / thuần lướt feed để phục hồi trust score, tránh nhồi follow liên tục dẫn tới bị action ban vĩnh viễn.

### Nguyên nhân 8: Bẫy Báo Cáo Ca Lịch Sử Chạy Trước Thời Điểm Commit Bản Vá (Historical Stale-Run Watchdog Trap)
1. **Hiện tượng nhận biết:**
   - Người vận hành nhận được báo cáo watchdog báo lỗi (ví dụ: máy dính nhả follow lọt lưới, lệch âm -2, không bắt được `FOLLOW_FAILED`), thắc mắc: *"Ủa script đã có bước check nhả/vuốt reload rồi mà sao vẫn bị?"* hoặc *"Ủa lỗi này tưởng hôm qua fix rồi?"*.
2. **Cơ chế gốc rễ:**
   - Watchdog quét trong cửa sổ retention 7 ngày theo danh sách `reported_sessions` trong `follow_session_reported.json`.
   - Một số ca chạy cũ của các ngày/phiên trước (ví dụ ca `2026-10-17_ca1_phien1` chạy lúc 06:25 sáng 17/10) hoàn tất hoặc được watchdog kích hoạt backfill báo cáo sau.
   - Tại thời điểm ca đó thực sự chạy trên điện thoại (06:25 ngày 17/10), **bản vá sửa lỗi (ví dụ commit `d328458` chốt lúc 19:01 tối 17/10) HOÀN TOÀN CHƯA RA ĐỜI**. Máy đang chạy trên commit cũ hơn nên dĩ nhiên vẫn dính lỗi chưa có vuốt reload Path B.
3. **Kỷ luật điều phối & Kiểm chứng O(1) trước khi vội vàng sửa code:**
   - **Bước 1: So sánh Timestamp ca chạy vs Git Log:**
     * Đọc `start_time` trong `run_manifest.json` hoặc timestamp trong `log.jsonl` của ca bị báo cáo.
     * Chạy `git log -1 --format="%ci %h %s" <commit_hash>` của commit đã vá lỗi liên quan.
     * **Quy tắc phán đoán:** Nếu `run_timestamp < commit_timestamp` $\rightarrow$ Khẳng định ngay với người vận hành: **Ca này chạy trên code cũ trước thời điểm commit bản vá**, không phải bản vá bị lỗi hay bị hỏng, tuyệt đối CẤM sửa đè code đang chạy ổn định.
   - **Bước 2: Kiểm tra Working Tree hiện tại (`git diff` / `git status`):**
     * Trước khi sửa thêm bất kỳ tính năng nào mới (như nâng cấp WinRT OCR Primary), phải kiểm tra xem code sửa mới có kế thừa hay vô tình ghi đè lên các chốt chặn của commit trước hay không (ví dụ: `pull_to_refresh_profile` trong `_path_b_verify` và Follow Dominance trong `classify_button`).

### Nguyên nhân 7: Lệch Âm Độc Lập Do TikTok Silent Unfollow / Shadow Action Block Trên Nick Non (Client Optimistic UI vs Server Drop)
1. **Hiện tượng nhận biết:**
   - Watchdog báo lệch âm trên 1 máy cụ thể (ví dụ: `M23 (@tranngan8642) : script 2 lượt - web 0 lượt - lệch (-2)`).
   - Nick này không bị `FOLLOW_FAILED` hay ngắt phiên ngay tại bước follow (script vẫn báo `status: OK, followed: 2`), nhưng web cào trước và sau ca đều ghi nhận 0 lượt tăng (`delta = 0`).
   - Khác với Nguyên nhân 2 (Race condition P1 âm -> P2 bù dương): Ở trường hợp này, **không hề có độ trễ cào hay bù trừ dương ở P2**.
2. **Bản chất kỹ thuật (Client Optimistic UI vs Server-Side Action Block):**
   - **Optimistic UI trên client:** Khi bot tap nút Follow trên danh sách (Mode 2) hoặc trên profile, app TikTok đổi ngay giao diện sang trạng thái `Đang follow` (Following) trên client trước khi server xác nhận. Runner kiểm tra nút sau tap thấy nút đã đổi màu nên ghi nhận thành công (`followed_count = 2`).
   - **Server TikTok âm thầm loại bỏ (Silent Drop / Shadow Unfollow):** Đối với các nick non (Rookie / Row 7-8 chưa graduate, đang probation) hoặc tài khoản bị chấm điểm trust thấp / IP bị soi:
     * Server TikTok tiếp nhận request nhưng không tăng trường `following` trên database máy chủ.
     * Khi nick quay về màn hình Profile cá nhân (`verify_profile`), counter **"Đang follow"** trên giao diện vẫn là **0**!
     * Web scraper cào dữ liệu từ server TikTok cũng trả về **0**.
3. **Quy trình kiểm chứng hiện trường O(1) để phân định Race Condition vs Shadow Drop:**
   - **Bước 1: Đọc XML Profile của nick ở cuối ca chạy:**
     Kiểm tra `runtime/kibe/live/<YYYY-MM-DD>/<run_id>/machines/machine_<N>/<run_id>/artifacts/.../verify_profile/ui.xml`.
     Tìm node `resource-id` có nhãn `Đã follow` (hoặc `id/t93`) và node số lượng ngay phía trên (`id/t94`):
     ```xml
     <node resource-id="...:id/t94" text="0" bounds="[88,675][388,741]" />
     <node resource-id="...:id/t93" text="Đã follow" bounds="[88,735][388,783]" />
     ```
   - **Bước 2: Đối soát:**
     * Nếu node `text="0"` ngay trên màn hình thiết bị của máy: **Chứng minh 100% tài khoản bị TikTok server shadow-drop** (server không chấp nhận lượt follow), không phải do scraper cào chậm hay lỗi watchdog.
     * Nếu node `text="2"` trên thiết bị nhưng Web cào `0`: Là độ trễ cache CDN của TikTok Web hoặc scraper cào trước khi sync server (xem Nguyên nhân 2 & 4).
   - **Bước 3: Ứng xử vận hành:**
     * Không can thiệp ADB bấm tay.
     * Giữ nguyên nick ở chế độ dưỡng sinh / thuần lướt feed để phục hồi trust score, tránh nhồi follow liên tục dẫn tới bị action ban vĩnh viễn.

### Nguyên nhân 8: Bẫy Báo Cáo Ca Lịch Sử Chạy Trước Thời Điểm Commit Bản Vá (Historical Stale-Run Watchdog Trap)
1. **Hiện tượng nhận biết:**
   - Người vận hành nhận được báo cáo watchdog báo lỗi (ví dụ: máy dính nhả follow lọt lưới, lệch âm -2, không bắt được `FOLLOW_FAILED`), thắc mắc: *"Ủa script đã có bước check nhả/vuốt reload rồi mà sao vẫn bị?"* hoặc *"Ủa lỗi này tưởng hôm qua fix rồi?"*.
2. **Cơ chế gốc rễ:**
   - Watchdog quét trong cửa sổ retention 7 ngày theo danh sách `reported_sessions` trong `follow_session_reported.json`.
   - Một số ca chạy cũ của các ngày/phiên trước (ví dụ ca `2026-10-17_ca1_phien1` chạy lúc 06:25 sáng 17/10) hoàn tất hoặc được watchdog kích hoạt backfill báo cáo sau.
   - Tại thời điểm ca đó thực sự chạy trên điện thoại (06:25 ngày 17/10), **bản vá sửa lỗi (ví dụ commit `d328458` chốt lúc 19:01 tối 17/10) HOÀN TOÀN CHƯA RA ĐỜI**. Máy đang chạy trên commit cũ hơn nên dĩ nhiên vẫn dính lỗi chưa có vuốt reload Path B.
3. **Kỷ luật điều phối & Kiểm chứng O(1) trước khi vội vàng sửa code:**
   - **Bước 1: So sánh Timestamp ca chạy vs Git Log:**
     * Đọc `start_time` trong `run_manifest.json` hoặc timestamp trong `log.jsonl` của ca bị báo cáo.
     * Chạy `git log -1 --format="%ci %h %s" <commit_hash>` của commit đã vá lỗi liên quan.
     * **Quy tắc phán đoán:** Nếu `run_timestamp < commit_timestamp` $\rightarrow$ Khẳng định ngay với người vận hành: **Ca này chạy trên code cũ trước thời điểm commit bản vá**, không phải bản vá bị lỗi hay bị hỏng, tuyệt đối CẤM sửa đè code đang chạy ổn định.
   - **Bước 2: Kiểm tra Working Tree hiện tại (`git diff` / `git status`):**
     * Trước khi sửa thêm bất kỳ tính năng nào mới (như nâng cấp WinRT OCR Primary), phải kiểm tra xem code sửa mới có kế thừa hay vô tình ghi đè lên các chốt chặn của commit trước hay không (ví dụ: `pull_to_refresh_profile` trong `_path_b_verify` và Follow Dominance trong `classify_button`).

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
