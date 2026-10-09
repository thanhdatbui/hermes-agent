# Quy Trình Đối Soát Following Sau Phiên (Targeted Post-Session Following Reconciliation)

## 1. Bối cảnh & Vấn đề Cốt lõi
Trong hệ thống nuôi TikTok Phone Farm, tính năng Follow được chia làm hai lớp kiểm soát:
1. **In-Session UI Verification (Path B):** Kiểm tra ngay trên app Android sau khi bấm nút (kiểm tra nút đổi sang "Đã follow", reload profile để phát hiện nút tự bật lại màu đỏ).
2. **Post-Session Profile Scraping (Tầng Server):** Cào trang cá nhân công khai của tài khoản TikTok để kiểm tra số `followingCount` thực tế trên server TikTok.

### Tại sao bắt buộc phải có Đối Soát Tầng Server?
- TikTok có cơ chế **Silent Action Block / Shadow Drop**: Trên giao diện app (Optimistic UI), nút có thể hiển thị là "Đang theo dõi", nhưng request gửi lên server bị chặn ngầm (do IP, device trust, hoặc tần suất). Số `following` thực tế trên server ByteDance không hề tăng.
- Nếu chỉ dựa vào báo cáo của runner (`follow_result.json`), hệ thống sẽ ngộ nhận là follow thành công trong khi thực tế chỉ số không nhảy.

---

## 2. Phá Bỏ Ngụy Biện "Nặng Tải Proxy" (Anti-Excuse)
- **Sai lầm thường gặp của Coordinator/Agent:** Lo sợ việc cào sau mỗi phiên sẽ "quá tải pool proxy" vì nghĩ phải cào toàn bộ 627 tài khoản toàn farm.
- **Thực tế vận hành:**
  + Trong một phiên nuôi (Session), số máy chạy follow thực tế rất ít (chỉ khoảng **15 – 30 máy**) do các bộ lọc an toàn:
    * Nick phải $\ge 6$ video mới được follow (`under-6-videos-follow-disabled`).
    * Nick đang trong ngày dưỡng sinh 1/3 sẽ bỏ qua follow (`organic-rest-day-pure-feed`).
    * Nick dính cooldown nhả follow trong ngày sẽ bị khóa.
  + Dùng lệnh cào đích danh:
    `python D:/Taadaa/tools/tiktok_account_tracker.py --usernames <user_1> <user_2>... --workers 10`
  + Quá trình cào 15–30 nick này qua pool 67 proxy của farm chỉ tiêu tốn **15 đến 25 giây**, hoàn toàn nhẹ nhàng và an toàn 100%.

---

## 3. Kiến Trúc Chu Trình Đối Soát Tự Động (Watchdog ➔ Tracker ➔ DB ➔ Telegram)

### Bước 1: Thu thập Target Users từ Kết quả Runner
Khi phiên nuôi hoàn tất và watchdog (`feed_session_watchdog.py`) quét thấy có máy chạy follow thành công (`len(fl_success) > 0`):
- Trích xuất danh sách máy có `len(all_follows[m].get("followed", [])) > 0`.
- Tra cứu username tương ứng của máy tại slot `active_row` từ workbook an toàn (`taikhoan_run_safe.xlsx`).
- Lưu lại map: `reported_counts = {username: len(followed_list)}`.

### Bước 2: Kích hoạt Cào Targeted & Cơ Chế Pre-Session Scrape T0
- **BẮT BUỘC PRE-SESSION SCRAPE T0:** Trước khi spawn phiên, runner kích hoạt cào snapshot mốc $T_0$ cho toàn bộ nick hợp lệ của Row sắp chạy. Tránh việc watchdog đối soát sau phiên lấy nhầm baseline cũ từ 07:00 sáng gây lệch dương ảo.

Gọi subprocess ngầm không làm nghẽn watchdog:
```python
cmd = [
    python_exe,
    tracker_script,
    "--usernames", *target_users,
    "--workers", str(min(10, max(1, len(target_users))))
]
subprocess.run(cmd, timeout=90, capture_output=True, text=True)
```
- `tiktok_account_tracker.py` nạp proxy pool 67, gửi HTTP request lấy `__UNIVERSAL_DATA_FOR_REHYDRATION__` và ghi một snapshot mới vào bảng `snapshots` trong SQLite `D:/Taadaa/data/tiktok_tracker.db`.

### Bước 3: Tính Delta & So Khớp Số Liệu (Bẫy LIMIT 2 & Chuẩn Hóa Baseline)
- **BẪY CHẾT NGƯỜI CỦA `LIMIT 2` THUẦN TÚY:**
  + Nếu chỉ truy vấn `ORDER BY timestamp DESC LIMIT 2`, trong trường hợp có retry cào, worker cào đúp, hoặc chạy canary thủ công sau phiên, CSDL sẽ ghi nhận 2 snapshot đều nằm SAU phiên (ví dụ 08:46:23 và 08:47:46 đều có `following = 189`).
  + Khi đó: $\Delta Following = 189 - 189 = 0 \rightarrow$ Báo cáo hiểu nhầm là "Web tăng 0, lệch -1", gây báo động giả nhả follow ngầm!
- **GIẢI PHÁP CHUẨN (SESSION START BASELINE):**
  + Truy vấn `latest_row` (snapshot mới nhất):
    ```sql
    SELECT following, timestamp FROM snapshots 
    WHERE LOWER(username) = LOWER(?) 
    ORDER BY timestamp DESC, id DESC LIMIT 1;
    ```
  + Truy vấn `baseline_row` neo theo mốc bắt đầu phiên (`session_start_iso` = `YYYY-MM-DD HH:MM:00`):
    ```sql
    SELECT following, timestamp FROM snapshots 
    WHERE LOWER(username) = LOWER(?) AND timestamp <= ? 
    ORDER BY timestamp DESC, id DESC LIMIT 1;
    ```
  + Nếu có `session_start_iso` và tìm thấy `baseline_row`, tính:
    $$\Delta Following_{\text{thật}} = Following_{\text{latest}} - Following_{\text{baseline}}$$
  + Chỉ fallback sang `LIMIT 2` (cặp snapshot liền kề) nếu không có mốc `session_start_iso` hoặc tài khoản hoàn toàn chưa có snapshot trước giờ mở phiên.
- So sánh $\Delta Following_{\text{thật}}$ với `reported_count`:
  + $\Delta Following_{\text{thật}} == reported\_count$: Khớp 100%.
  + $\Delta Following_{\text{thật}} < reported\_count$: Bị nhả/lệch ngầm (TikTok server drop).
  + $\Delta Following_{\text{thật}} > reported\_count$: Có follow tự nhiên/hồi phục.

### Bước 4: Định Dạng Báo Cáo Telegram & Nguyên Tắc Thống Kê Theo NICK (Bắt Buộc)
- **QUY TẮC BẢO VỆ (REPORT BY USERNAME/NICK, NOT MACHINE ALONE):**
  + Khi báo cáo đối soát và thống kê Follow, BẮT BUỘC phải quy về **SỐ NICK và TÊN NICK CỤ THỂ (@username)** (kèm số máy/Row phụ trợ), TUYỆT ĐỐI KHÔNG chỉ báo cáo mỗi "số máy" chung chung.
  + Mỗi máy có thể chạy nhiều nick qua các Row khác nhau (chủ yếu Row 1 & Row 2). Người vận hành cần biết chính xác từng nick có tăng Following trên TikTok Web không, script báo nhả follow có khớp với data cào từng nick không.
- **BẪY GOM NHÓM `fl_success` KHI DỪNG Ở `MANUAL_REVIEW`:**
  + Với Mode 2 (Anchor Follow), nick follow Anchor thành công (+1 lượt) nhưng khi bấm mở tab following của Anchor bị lag mạng dẫn đến dừng `MANUAL_REVIEW`.
  + Watchdog BẮT BUỘC phải gom vào `fl_success` theo điều kiện `len(flist) > 0` (thay vì chỉ lọc cứng `status in {"OK", "SUCCESS"}`), để đảm bảo các nick này vẫn được tự động cào snapshot và đối soát trên TikTok Web.

Hiển thị dòng đối soát ngay dưới block Follow chéo:
```text
• Follow chéo (30 lượt follow) [Module 2 (Anchor): 20 | Module 1 (Bù): 10]:
  + Success (2 nick): ...
  + Đối soát TikTok Web (+28 Following thật | Lệch -2 so với script báo 30):
    - @anhtruong840 (Row 1 - M10): script báo 15 | web tăng +15 (Khớp 100%)
    - @ngocninh37 (Row 2 - M45): script báo 15 | web tăng +13 (Nhả/Lệch ngầm: -2)
```

---

## 4. Phân Biệt Baseline: Web Dashboard (:1905) vs Đối Soát Tác Vụ (Watchdog)
- **Bẫy sập Delta khi dùng chung `rn = 2`:** Nếu Web Dashboard dùng `r1.rn = 1` vs `r2.rn = 2` (2 snapshot liền kề), mọi lần cào lẻ (quét targeted đối soát sau phiên, rescan avatar, hoặc quét bù trong ngày) sẽ đẩy snapshot mới nhất của ngày thành `r2`. Kết quả: Toàn bộ delta Follower/Tim của 1.000+ nick bị co về 0 hoặc +1 (so với 30 phút trước thay vì 24h trước).
- **Chuẩn hóa 2 cơ chế độc lập:**
  1. **Web Dashboard hàng ngày (`:1905`):** Baseline BẮT BUỘC neo theo mốc chốt cố định của ngày hôm trước (`substr(timestamp, 1, 10) < max_dt` do cron quét 07:00 sáng thiết lập). Đảm bảo giữ nguyên số liệu tăng trưởng cả ngày dù farm có quét lẻ bao nhiêu lần.
  2. **Watchdog đối soát tác vụ (`feed_session_watchdog.py`, `post_evening_avatar_watchdog.py`):** Baseline neo theo mốc mở phiên (`session_start_iso`) hoặc snapshot ngay trước khi chạy của đúng danh sách nick tham gia tác vụ (~15-30 máy). Nhằm phát hiện chính xác số lượt thực tế thành công trên server TikTok vs báo cáo script.

---

## 5. Liên Kết với TikTok Web Dashboard (`port 1905`) & Chuyên Biệt Tab "🔗 Tăng Follow"
- Dữ liệu snapshot này tự động đồng bộ vào bảng `snapshots` của SQLite `D:/Taadaa/data/tiktok_tracker.db`.
- **Thiết Kế Tab Giám Sát Chuyên Biệt `🔗 Tăng Follow` (Thay Thế BXH Following Thô):**
  + Khi người dùng bấm vào thẻ KPI `👥 Tổng Đã Follow (Following)` hoặc nút toolbar `🔗 Tăng Follow`, view `bxh_following` phải **mặc định kích hoạt bộ lọc `deltaFilter = 'up'`** (thay vì `'all'`) để hiển thị ngay lập tức danh sách các nick có tăng follow trong ngày (`delta_following > 0`), sắp xếp từ cao xuống thấp.
  + **Giám Sát Độ Ổn Định Của Nick:**
    * Bộ lọc `🟢 Chỉ Tăng (+)`: Cho phép kiểm tra nhanh danh sách nick đang follow đều đặn, số máy (tag `M<may>`), trạng thái `LIVE`, số video và follower.
    * Bộ lọc `🔴 Giảm Following (-)`: Phát hiện ngay lập tức các nick bị tụt/nhả follow bất thường để đưa vào diện can thiệp hoặc dưỡng sinh.
  + **Auto-Refresh Realtime 30s:**
    * Script phía client tự động fetch `/api/data` mỗi 30s, cập nhật lại DOM cho thẻ KPI `#kpi-following-breakdown` và re-render bảng dữ liệu mà không làm mất trạng thái lọc của người dùng.

---

## 6. Phân Tách Follow Nội Bộ vs Follow Tự Nhiên Lướt Feed & Dashboard Breakdown
- **Bản chất số liệu TikTok:** API/Web scraping chỉ trả về `followingCount` tổng gộp. Server TikTok không tự phân loại đâu là follow chéo nội bộ, đâu là follow kênh người ngoài khi lướt feed.
- **Nguồn dữ liệu đối soát chuẩn:**
  + **Follow chéo nội bộ (Internal Follow):** Bắt buộc đọc từ `follow_result.json` của runner (`mode2_followed_count` cho Anchor + `mode1_followed_count` cho Search bù). Đây là số lượt nick farm chủ động tìm và follow nhau.
  + **Follow tự nhiên (Organic Feed Follow):** Bắt buộc đọc từ `run_manifest.json` (`tot_nat_follows`) do watchdog tổng hợp khi lướt FYP / Bạn bè.
- **Lưu trữ & SQLite Concurrency Invariant:**
  + Lưu vào bảng `session_action_stats (session_key, cluster, target_date, internal_follows, natural_follows, likes, swipes, created_at, PRIMARY KEY (session_key, cluster))`.
  + **BẪY DATABASE IS LOCKED:** Trên Windows, service dashboard (:1905) và runner liên tục đọc DB. Nếu để mặc định `journal_mode=DELETE`, câu lệnh ghi/upsert stats sẽ bị văng lỗi `sqlite3.OperationalError: database is locked`.
  + **Giải pháp bắt buộc:** Kích hoạt `PRAGMA journal_mode=WAL;` và luôn mở kết nối với `sqlite3.connect(db_path, timeout=10.0)`.
- **Quy tắc hiển thị Dashboard & Báo cáo (User Preference Invariant):** 
  + **Hiện đầy đủ song song Follow Nội Bộ & Follow Tổng:** Người dùng yêu cầu hiển thị trực diện cả 2 con số `Follow Nội Bộ` và `Follow Tổng` (để tự đối trừ ra lượt tự nhiên), không chỉ hiển thị mỗi số tự nhiên hoặc gộp chung.
    * Thẻ KPI `👥 Tổng Đã Follow (Following)`: Hiển thị dòng subdetail `🔗 Nội bộ: +X | 📈 Tổng tăng: +Y`.
    * Trên từng dòng tài khoản trong bảng: Cột "Đã Follow" hiển thị cả tổng following hiện tại kèm delta tổng `+Y`, và badge dòng phụ `🔗 Nội bộ: +X` để theo dõi rõ từng nick.
  + **Tab chuyên biệt `🔗 Tăng Follow`:** Mặc định kích hoạt bộ lọc `deltaFilter = 'up'` khi người dùng chuyển sang tab này, giúp người vận hành xem ngay danh sách các nick đang tăng follow để kiểm tra xem nick follow có ổn định không hay đang bị nhả/tụt follow (`🔴 Giảm Following (-)`).
  + **Bảng lưu vết tài khoản:** `daily_account_actions (target_date, username, may, internal_follows, updated_at, PRIMARY KEY (target_date, username))` ghi nhận số lượt follow nội bộ từng nick được thực hiện trong ngày từ `feed_session_watchdog.py`.

---

## 7. Fail-Safe Invariant
- Toàn bộ bước cào đối soát phải được bọc trong block `try...except`.
- Nếu cào web gặp lỗi mạng/proxy timeout, watchdog chỉ in ra dòng cảnh báo đối soát `[+ Đối soát TikTok Web: Timeout/Lỗi cào]` và **VẪN TIẾP TỤC gửi báo cáo ca nuôi của farm**. Tuyệt đối không để lỗi cào làm chết tiến trình báo cáo của watchdog.

---

## 8. Lưu ý triển khai & Dual-Watchdog Pitfall
- **Vị trí file Watchdog:** Hệ thống có 2 vị trí file `feed_session_watchdog.py`:
  + `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`: Phiên bản chạy cron chính của Hermes hỗ trợ multi-cluster (kibe M1-80 & admin M201-280).
  + `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`: Phiên bản nằm trong repo tiêu chuẩn và được target bởi test runner `python_runner/tests/test_feed_session_watchdog.py`.
  -> Khi tích hợp hàm `reconcile_cluster_following`, cần đồng bộ cả 2 nơi để đảm bảo vừa pass test suite vừa hoạt động chính xác trên live cron.
- **Handling `--usernames` trong `tiktok_account_tracker.py`:**
  + `load_farm_accounts` cần hỗ trợ danh sách `usernames`: lọc case-insensitive.
  + Nếu username được chỉ định qua CLI không tồn tại trong Excel farm, vẫn tự động append vào danh sách quét với giá trị mặc định (`may='', device_id='', username=u, video_posted=0`), tránh tình trạng drop tài khoản cần cào.

---

## 9. Hiện Tượng Máy Dừng Ở 1 Lượt Follow (Anchor Follow Success vs Following Tab Fail)
- **Cơ chế 2 bước của Mode 2:**
  + Bước 1: Tìm và follow Anchor nick (Máy 32 follow `@thu.trangg584`) $\rightarrow$ Thành công +1 follow.
  + Bước 2: Bấm vào tab "Đang follow" của Anchor để follow tiếp các nick farm khác trong danh sách $\rightarrow$ Nếu mạng/proxy lag tải tab quá 10s dẫn tới timeout sau ladder retry $\rightarrow$ Script dừng với trạng thái `MANUAL_REVIEW` để bảo vệ nick.
- **Xác thực đối soát & Bẫy Gom Nhóm `fl_success`:**
  + Tại thời điểm dừng, 1 lượt follow Anchor ở Bước 1 **đã ghi nhận thành công trên server TikTok**, không hề bị nhả.
  + Số liệu cào web xác nhận tăng đúng +1 (`188 -> 189`), khớp 100% với script báo cáo. Không được nhầm lẫn giữa lỗi kẹt mở tab danh sách và việc bị TikTok nhả follow.
  + **BẪY GOM NHÓM `fl_success` CỦA WATCHDOG:** Trong `feed_session_watchdog.py`, nếu gom cứng `elif status in {"OK", "SUCCESS"} and len(flist) > 0: fl_success.append(m)`, máy dừng ở Bước 2 có `status == "MANUAL_REVIEW"` sẽ bị đẩy nhầm vào `fl_error`. Khi đó `fl_success` rỗng $\rightarrow$ `reconcile_cluster_following` không được kích hoạt, bỏ sót việc cào đối soát cho nick Anchor thành công này!
  + **Quy chuẩn sửa guard:** Gom thành công cho đối soát phải chấp nhận cả `status == "MANUAL_REVIEW"` khi có lượt follow thực tế:
    ```python
    elif (status in {"OK", "SUCCESS"} or status == "MANUAL_REVIEW") and len(flist) > 0 and fd.get("follow_failed") is not True:
        fl_success.append(m)
    ```

- **Anti-Burnout Patch Dispatch:** Khi thay đổi code trên nhiều repo (`D:/Taadaa/tools` và `D:/Taadaa/tiktok-luot nuoi acc`), cấm dispatch worker với prompt mô tả mở để worker tự đọc và tự viết lại từ đầu vì sẽ dính Circuit Breaker cạn 15 calls (`0 files modified`). Coordinator phải chuẩn bị sẵn **executable patch script nguyên khối** qua terminal python script để worker chỉ cần 1 call chạy lệnh và 1 call verify.
- **Bảo Vệ Invariant `can_report_session`:** Khi sync giữa bản runtime cron và repo Git, BẮT BUỘC giữ vững guard `if is_today and runner_busy: return False` ngay đầu hàm `can_report_session` để tránh chốt báo cáo sớm khi ca nuôi vẫn đang chạy và bảo đảm 10/10 test case trong `test_feed_session_watchdog.py` PASS 100%.

---

## 10. Kỹ Thuật Truy Vấn Runtime Artifact O(1) & Cơ Chế Early-Exit Cào Đối Soát
- **Bẫy Timeout 180s khi quét thư mục Runtime:**
  + Thư mục runtime lồng sâu 2 cấp timestamp: `D:/Taadaa/runtime/<cluster>/live/<date>/row-X-<hhmmss>/<run_ts>/machines/machine_<m>/<run_ts>/follow_result.json`.
  + Tuyệt đối CẤM dùng `os.walk` hoặc quét đệ quy qua các thư mục `live/<date>` vì chứa hàng chục ngàn file artifacts (log, screencap, video chunks) sẽ làm tê liệt terminal và timeout 180s.
  + **Quy chuẩn truy vấn O(1):** Đọc trực tiếp `run_manifest.json` nằm tại thư mục run gốc (`.../row-X-<hhmmss>/<run_ts>/run_manifest.json`), duyệt danh sách `multi_machine_summary`. Mỗi item chứa sẵn trường `artifact_root`, chỉ cần trỏ thẳng tới `os.path.join(item['artifact_root'], 'follow_result.json')`.
  + **Tăng tốc I/O đa luồng (ThreadPoolExecutor):** Trên Windows NTFS / mạng nội bộ, đọc tuần tự 600+ file json có thể mất tới ~176s. BẮT BUỘC dùng `concurrent.futures.ThreadPoolExecutor(max_workers=32)` để gom danh sách `(machine, artifact_root)` từ `run_manifest.json` rồi đọc song song, rút ngắn tổng thời gian đọc toàn farm xuống chỉ còn **4 đến 25 giây**.
- **Hiện tượng Bảng `daily_account_actions` Trống (Early-Exit 0 Follow):**
  + Trong `reconcile_cluster_following()`: Nếu phiên không có máy nào follow thành công (`len(fl_success) == 0`), hàm kích hoạt early exit `if not fl_success: return []`.
  + Quá trình cào targeted web và ghi vào `daily_account_actions` sẽ được bỏ qua an toàn để tiết kiệm tài nguyên proxy.
  + Điều này giải thích tại sao trong các ngày toàn bộ nick rơi vào diện Dưỡng sinh (`organic-rest-day-pure-feed`), Cooldown nhả follow (`follow-released-daily-cooldown`), hoặc Chưa đủ 6 video (`under-6-videos-follow-disabled`), bảng `daily_account_actions` không có dữ liệu mới trong khi bảng `session_action_stats` vẫn ghi nhận đầy đủ thống kê lướt feed & thả tim.
- **Rà soát Dual-Watchdog Drift:**
  + `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`: Bản live cron đầy đủ tính năng đa cụm (Kibe M1-80 & Admin M201-280) cùng module đối soát cào web.
  + `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`: Bản repo Git. Khi đồng bộ từ bản live sang repo Git, cần bọc guard tương thích ngược cho test runner.

---

## 11. Giải Thích Hiện Tượng Dashboard (:1905) Chỉ Tăng +1 Đến +2 Mỗi Ngày & Bẫy Snapshot Nửa Đêm
- **Phân biệt Tăng Luỹ Kế Đa Ngày vs $\Delta$ 24h Trên Dashboard:**
  + Khi xem báo cáo theo khoảng thời gian (ví dụ 5 ngày từ 19/09 đến 24/09), một số nick có mức tăng lớn như `+18` (@thy.dung1828), `+16` (@nhuphuong458934), `+13` (@ng.kim.ngn469).
  + Tuy nhiên trên Dashboard TikTok Web (`:1905`), số liệu $\Delta$ hiển thị theo **chu kỳ 24h** (so sánh snapshot lúc 07:00 sáng hôm nay với mốc chốt 07:00 sáng hôm trước `substr(timestamp, 1, 10) < max_dt`).
  + Chia đều theo ngày, mỗi nick chỉ tăng trung bình từ **+1 đến +3 Following/ngày**.
- **Ba Nguyên Nhân Kỹ Thuật Khiến Số Tăng Hàng Ngày Thường Chỉ Đạt +1 đến +2:**
  1. **Mode 2 Chỉ Kịp Follow Anchor (+1):** Cơ chế follow Mode 2 follow nick Anchor thành công (+1), sau đó mở tab "Đang follow" của Anchor bị timeout/lag proxy $\rightarrow$ runner dừng an toàn `MANUAL_REVIEW` để bảo vệ nick. Do đó hầu hết các phiên chỉ ăn được 1 lượt Anchor (+1 lượt tự nhiên nếu có khi lướt feed).
  2. **Bộ Lọc An Toàn Khóa ~80% Nick Mỗi Ngày:**
     * Nhiều nick toàn farm chưa đủ 6 video đã đăng (`under-6-videos-follow-disabled`).
     * ~33% nick rơi vào ngày Dưỡng Sinh 1/3 xoay tua (`organic-rest-day-pure-feed`, 0 follow, 0 up).
     * 15–30 nick bị cooldown 24h do nhả follow.
     $\rightarrow$ Mỗi ngày chỉ khoảng **20 – 45 nick** trên toàn farm thực sự phát sinh follow.
- **Bẫy Snapshot Nửa Đêm & Khoảng Trống Preflight Snapshot Khiến Báo Lệch Dương:**
     * Khi ca nuôi bắt đầu mà không có lệnh cào snapshot preflight ngay trước giờ chạy (`session_start_iso`), DB phải lùi về dùng snapshot cũ (ví dụ quét toàn farm lúc 07:00 sáng).
     * Mọi lượt follow tăng tự nhiên hoặc sync trễ trong khoảng thời gian từ 07:00 đến khi ca chạy (ví dụ 3 tiếng sau) đều bị gộp vào $\Delta \text{Web}$ của ca đó, dẫn tới việc script báo 1 nhưng web tăng +4 (lệch dương ảo +3).
     * **Quy chuẩn khắc phục:** Luôn kích hoạt cào snapshot preflight sát giờ chạy ca nuôi hoặc neo chặt `session_start_iso` để loại bỏ độ trễ tích lũy từ các ca trước.

---

## 12. Giải Quyết Triệt Để Bệnh Kẹt Mở Tab Anchor (Mode 2) & Phục Hồi Lưu Lượng Follow 10-20 Nick/Ca
- **Bối Cảnh Lỗi "Kẹt Mở Tab Anchor" & Farm Bị Ép Về 1 Follow/Ca:**
  + Từ ngày 21/09 đến 24/09, toàn bộ farm gần như chỉ đạt tối đa +1 hoặc +2 follow/ca nuôi.
  + Runner ghi nhận log: `MANUAL_REVIEW: mở tab Đã follow fail cho ... sau ladder (lần 2)` ngay sau khi follow xong nick Anchor đầu tiên.
- **3 Lỗ Hổng Kỹ Thuật Được Định Vị:**
  1. **Bẫy Fatal Break Chặn Đứng Hybrid Mode (Lỗi Nghiêm Trọng Nhất):**
     * Trong `mode2_follow_followers.py` (dòng ~1935), khi mở tab following của anchor thất bại sau 2 lần thử, runner gán `res.status = "MANUAL_REVIEW"` và thực thi lệnh `break` thoát vòng lặp.
     * Hậu quả: Không những bỏ qua các Anchor tiếp theo trong `seeds`, mà còn khiến `follow_engine.py` (vốn kiểm tra `if mode in ("1", "both") and res.status == STATE_OK`) **hủy bỏ hoàn toàn Mode 1 (Search Bù Sau)**! Toàn bộ 9–19 lượt follow còn lại trong session budget bị vứt bỏ.
     * **Giải Pháp Bắt Buộc:** Thay thế `res.status = "MANUAL_REVIEW"` + `break` bằng `logger.warning(...)` và `continue`. Cho phép safe-skip anchor bị lỗi mở tab để thử anchor kế tiếp; nếu hết anchor, Mode 2 kết thúc an toàn với `res.status = "OK"` để Mode 1 lập tức tiếp quản và tìm kiếm follow bù đủ ngân sách 10–20 lượt.
  2. **Bẫy Nhận Diện RecyclerView (`_classify_follower_surface`):**
     * Hàm chỉ so khớp cứng tuple ID tĩnh (`u5r`, `uo1`, `uvz`...). Khi TikTok cập nhật bản mới đổi tên ID resource, hàm trả về `invalid` dù RecyclerView đã hiển thị trên màn hình.
     * **Giải Pháp Bắt Buộc:** Bổ sung Fast-Path kiểm tra:
       ```python
       has_follower_items = any((node.get("resource_id") or "").endswith((":id/txt_user_name", ":id/txt_desc", "id/txt_user_name", "id/txt_desc")) for node in nodes)
       has_recycler = any(node.get("resource_id") in FOLLOWER_LIST_RECYCLER_IDS or "RecyclerView" in (node.get("class") or "") for node in nodes)
       if has_follower_items and has_recycler:
           return "populated"
       ```
  3. **Bẫy Giới Hạn Tọa Độ Dòng Tab Profile (`_following_tab_node`):**
     * Giới hạn `bounds[1] < 550` quá hẹp khiến các máy S7 có dòng chữ "Đang follow" nằm ở y=560 bị bỏ qua, dẫn tới bấm hụt tab. Đồng thời thiếu các selector ID mới (`id/t1i`, `id/t1h`).
     * **Giải Pháp Bắt Buộc:** Mở rộng bounds lên `bounds[1] < 600` và bổ sung `id/t1i`, `id/t1h` vào `tab_id_matches`.
- **Đồng Bộ Test Suite:**
  + Khi video gate được chuẩn hóa về `>= 6` video trong `follow_state.py`, test mock cần bảo đảm video_count hợp lệ để test suite pass 100%.

---

## 13. Bẫy Nuốt Lỗi (False Normal) Watchdog Khi Follow Về 0 Lượt & Cổng Farm Alert (2026-09-28)
- **Hiện Tượng:** Khi Mode 2 mở tab following thất bại (do lag UI S7) và Mode 1 gặp target đã follow sẵn, runner trả về `exit_code: 0, status: "OK", followed: []`. Watchdog gom máy vào `fl_other_skipped` (Bỏ qua: Khác) thay vì `fl_error`. Hậu quả: Không có lỗi nào được báo lên Telegram và không kích hoạt Farm Alert (`tot_fl_err >= 3`).
- **Quy Chuẩn Bắt Buộc Phân Loại `fl_error` Trong Watchdog:**
  + Trong `feed_session_watchdog.py`:
    ```python
    elif status == "SKIPPED" or (status in {"OK", "SUCCESS"} and len(flist) == 0):
        if "organic-rest-day" in f_reason or "rest-day" in f_reason:
            fl_rest.append(m)
        elif "under-10-videos" in f_reason or "under-6-videos" in f_reason:
            fl_under10.append(m)
        elif "đã follow sẵn" in f_reason or "follow-released" in f_reason:
            fl_other_skipped.append(m)
        elif fd.get("details", {}).get("mode2_degraded") or "fail" in f_reason or "lỗi" in f_reason:
            fl_error.append(m)  # BẮT BUỘC gom vào lỗi script khi xịt Mode 2 dẫn tới 0 follow!
        else:
            fl_other_skipped.append(m)
    ```
  + Khi `tot_fl_err >= 3`: Tự động kích hoạt `🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT HÀNG LOẠT (X máy lỗi script Follow)` gửi Telegram ngay.

---

## 14. Bắt Buộc Cột `Ngày Tạo` Trong Safe Workbook Gộp (`taikhoan_run_safe_combined.xlsx`)
- **Lỗ Hổng Trước Đây:** `sync_combined_safe_workbook.py` chỉ xuất 4 cột (`May, Device ID, ID, Video Đã Đăng`), làm rơi mất Cột 5 `Ngày Tạo`. Khi runner đọc file gộp, `account_age_days = None` khiến toàn bộ nick dù đủ tuổi (>50 ngày) vẫn bị bóp hạn mức về Warmup (3 follow) thay vì Full Budget (10–20 follow).
- **Quy Chuẩn Bắt Buộc:**
  + `sync_combined_safe_workbook.py` luôn trích xuất đủ 5 cột: `["May", "Device ID", "ID", "Video Đã Đăng", "Ngày Tạo"]`.
  + Runner đọc đủ `created_date` -> tính chính xác `account_age_days >= 21` để mở Full Budget.

---

## 15. Bẫy Ghi Nhầm `r_cnt` Vào `daily_account_actions.internal_follows` Khiến Dashboard Dán Nhãn Nhầm "🔗 Nội bộ: +X" Cho Nick Chỉ Follow Tự Nhiên (Bug Fix 28/09/2026)
- **Hiện tượng thực tế:**
  + Người dùng kiểm tra trang cá nhân nick M25 (`@reginzudm9l`) trên app TikTok: Nick đang follow 6 tài khoản, nhưng cả 6 tài khoản đều là nick bên ngoài (chủ đề Capybara, shop thời trang), hoàn toàn **0 có bất kỳ nick farm nội bộ nào**.
  + Tuy nhiên trên Web Dashboard (`:1905`), nick lại hiển thị badge `🔗 Nội bộ: +2` khiến người vận hành nghi ngờ số liệu follow chéo bị ma ảo.
- **Nguyên nhân cốt lõi trong code:**
  + Trong `feed_session_watchdog.py` (hàm `reconcile_cluster_following`), biến `r_cnt = m_to_reported.get(m_num, 0)` là tổng số lượt follow do script báo cáo:
    `m_to_reported[str(m)] = 0 if failed else cnt + natural_cnt` (bao gồm cả follow chéo `cnt` lẫn follow tự nhiên `natural_cnt`).
  + Khi ghi nhận hành động từng nick vào SQLite, code cũ lại nhét thẳng `r_cnt` vào cột `internal_follows` của bảng `daily_account_actions`.
  + Dashboard (`tiktok_dashboard.py`) đọc trường `internal_follows` từ `daily_account_actions` và gán cứng template hiển thị: `🔗 Nội bộ: +${item.internal_followed}`.
  + Do đó, 2 lượt follow tự nhiên trên feed của M25 bị dán nhãn nhầm thành 2 lượt follow nội bộ.
- **Bản Vá Chuẩn Hóa:**
  + Trong `feed_session_watchdog.py`: Thay thế `r_cnt` bằng số lượt follow chéo thực tế `c_cnt = 0 if is_failed else m_to_cross.get(str(m_num), 0)`. Chỉ khi `c_cnt > 0` mới ghi nhận vào cột `internal_follows`.
  + Dọn dẹp dữ liệu cũ bị ghi đè nhầm trong bảng `daily_account_actions` (`D:/Taadaa/data/tiktok_tracker.db`) để Dashboard phản ánh chính xác số liệu thực tế trên máy thật.

---

## 16. Ràng Buộc Đồng Bộ Follow Tự Nhiên Theo Cổng Follow Chéo & Chẩn Đoán Hiện Trường `follow_result.json` (User Invariant 28/09/2026)
- **Quy Tắc Ràng Buộc Tương Quan (Follow Coupler Policy):**
  1. **Khi nào Follow Chéo được mở thì Follow Tự Nhiên MỚI ĐƯỢC PHÉP BẬT:**
     - Điều kiện mở cổng Follow Chéo là **Dual Gate**: `account_age_days >= 21 AND video_count >= 6` (Commit `752ea57`).
     - Nick non / chưa trưởng thành (chưa đủ 21 ngày tuổi hoặc chưa đủ 6 video): **CẤM TUYỆT ĐỐI follow tự nhiên ngoài feed (`follow_rate = 0`)**. Nick non chỉ làm 3 việc: lướt FYP + like nhẹ + ngâm tuổi.
     - Cả `multi_machine_feed_session.py` và `feed_swipe_smoke.py` đều phải đồng bộ gate `video_count < 6` (không giữ mốc 10 cũ).
  2. **Khi Follow Chéo Bị Nhả $\rightarrow$ Follow Tự Nhiên BẮT BUỘC TẮT THEO:**
     - Khi nick dính cờ nhả follow (`follow_failed: true`, `is_account_in_follow_cooldown`), backend TikTok đang trong trạng thái Action Restriction.
     - Hệ thống BẮT BUỘC ngắt 100% cả follow chéo lẫn follow tự nhiên ngoài feed, đưa nick về chế độ **Dưỡng Sinh Thuần Túy (Organic Rest)**: 0 follow, 0 upload. Tuyệt đối không tiếp tục bấm follow tự nhiên ngoài feed vì sẽ làm tụt Persistence Ratio và dính án phạt nặng hơn (shadowban/checkpoint).
- **Kỷ Luật Chẩn Đoán Hiện Trường Khi Nick Đủ Điều Kiện Nhưng Có 0 Follow Nội Bộ:**
  - CẤM phán đoán mò là "nick chưa đủ điều kiện follow chéo".
  - BẮT BUỘC trích xuất file `follow_result.json` tại thư mục runtime của máy:
    `D:/Taadaa/runtime/<cluster>/live/<date>/<session_run>/machines/machine_<N>/<run_ts>/follow_result.json`.
  - Kiểm tra trường `status`, `reason`, `skipped`, `details`:
    * Nếu details.mode2_degraded = True: Mode 2 mở tab Following của Anchor bị lỗi UI sau ladder $\rightarrow$ an toàn chuyển Mode 1.
    * Nếu Mode 1 trả về reason: "đã follow sẵn (skip)" và skipped: [...]: Nick đã follow các nick mục tiêu ở các ca trước nên script bỏ qua hợp lệ, không phải lỗi hệ thống.

---

## 17. Giải Mã Hiện Tượng "Lệch Follow Âm" Do Follow Tự Nhiên & Dải Phân Loại "1 - 4 Lượt" (User Q&A 29/09/2026)

### 1. Vì Sao Đối Soát Báo Lệch Âm Lớn (Ví dụ: Web tăng +6 | Lệch -14 so với script báo 20)?
- **Cơ chế tính của Watchdog:** `expected_delta = follow chéo (cnt) + follow tự nhiên (natural_cnt)`.
- **Lỗ hổng không có Path B trên Follow Tự Nhiên:**
  + Trong lúc lướt feed (`feed_swipe_smoke.py`), bot bấm nút follow (+) trên video khi trúng tỷ lệ ngẫu nhiên (~5%). Thao tác chỉ là `adb shell input tap x y` mù, không có cơ chế reload profile để xác minh lại như Path B của Follow Chéo.
  + Nếu nick bị TikTok hạn chế nhẹ (soft action block) hoặc video animation nuốt lệnh, server TikTok sẽ **Silent Drop** (bỏ qua không ghi nhận).
  + Script feed vẫn đếm `result: success` $\rightarrow$ Watchdog cộng vào "script báo". Nhưng khi cào TikTok Web thật, `following` không tăng (+0) $\rightarrow$ Sinh ra hàng loạt dòng lệch âm: `script báo 2 (chéo 0, tự nhiên 2) | web tăng +0 (Lệch -2)`.
- **Quy tắc chẩn đoán:** Khi thấy lệch âm hàng loạt nhưng `chéo = 0, tự nhiên = X`, đó 100% là do Follow Tự Nhiên ngoài feed bị TikTok server drop, không phải lỗi của cơ chế Follow Chéo hay nhả follow thật.

### 2. Ý Nghĩa Dải Phân Loại "1 - 4 Lượt" & Vì Sao Cả Farm Chỉ Có 1 Nick Follow Thành Công 1 Lượt?
- **"1 - 4 lượt" là tên nhóm thống kê (Bucket Tier):** Watchdog chia các nick follow thành công thành các dải: `1 - 4 lượt`, `5 - 9 lượt`, `10 - 14 lượt`, `15+ lượt`. Nếu chỉ có 1 nick làm được 1 lượt, nó sẽ nằm trong nhóm `1 - 4 lượt (1 máy): M16 (1 lượt)`.
- **Vì sao đa số máy không follow trong ca?**
  + Lớp 1 (Chốt bảo vệ nick): ~33% máy nghỉ Dưỡng sinh (`organic-rest-day`), ~30-40% máy dính `follow-released-daily-cooldown` (nghỉ 24-48h bảo vệ nick), các nick chưa đủ 6 video bị chặn `under-6-videos`.
  + Lớp 2 (Hạn chế Target / Anchor):
    * Mode 1: Các nick mục tiêu trong danh sách đều "đã follow sẵn" từ các ca trước $\rightarrow$ Skip, 0 follow.
    * Mode 2: Nick Anchor để profile riêng tư / có 0 following (`zero-following-skip-v2`) hoặc kẹt UI khi mở tab "Đang follow" của Anchor $\rightarrow$ Dừng an toàn `MANUAL_REVIEW` để bảo vệ nick.
  + Hậu quả: Chỉ những nick mở được Anchor và tìm thấy mục tiêu mới chưa từng follow mới phát sinh lượt follow thành công.
