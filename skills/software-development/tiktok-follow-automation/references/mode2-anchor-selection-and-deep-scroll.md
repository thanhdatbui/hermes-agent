# Cơ chế chọn Anchor và Cuộn sâu danh sách Following trong Mode 2

## 1. Bản chất & Quy tắc chọn Anchor
- **Không phân biệt trạng thái follow của Anchor:** Anchor đã follow hay chưa follow đều hợp lệ để mở danh sách Following. Tránh tình trạng loại bỏ anchor đã follow khiến cạn kiệt nguồn anchor xịn. Cơ chế lọc `is_followed` CHỈ áp dụng cho các tài khoản con bên trong danh sách, không áp dụng cho anchor mẹ.
- **Ngưỡng lọc sàn Anchor dày:** Chỉ bốc các Anchor có `following >= 150` (`MIN_ANCHOR_FOLLOWING = int(os.environ.get("MIN_ANCHOR_FOLLOWING", "150"))` dựa trên snapshot mới nhất trong `tiktok_tracker.db`), tránh bốc nhầm các anchor mỏng mới nuôi chưa có nhiều nick nội bộ.
- **Telemetry & Test Contract khi đổi ngưỡng sàn:** Khi thay đổi `MIN_ANCHOR_FOLLOWING`, bắt buộc xuất telemetry `"min_anchor_following": MIN_ANCHOR_FOLLOWING` trong `_last_anchor_telemetry` và format log. Bộ test `test_follow_engine.py` bắt buộc kiểm thử 2 nhánh: nhánh chạy với default 150 (`monkeypatch.delenv("MIN_ANCHOR_FOLLOWING")`) và nhánh override qua env var (`monkeypatch.setenv("MIN_ANCHOR_FOLLOWING", "30")`) để pass Closeout Gate.

## 2. Kỹ thuật cuộn sâu và chống dừng sớm (Deep Scroll Safeguards)
- **Rủi ro bẫy `idle_scrolls` thấp (Cũ: 5 -> Đã nâng: 25):** Khi một tài khoản đã follow 20-30 nick của anchor từ các phiên trước, các nick này sẽ nằm ở đầu danh sách (hoặc dải nick ngoài farm). Nếu để `idle_scrolls >= 5` thì chỉ sau ~25 nick đã follow, bot sẽ tưởng nhầm là hết nick và ngắt sớm, bỏ lỡ hàng trăm nick bên dưới. Cần duy trì ngưỡng `idle_scrolls >= 25` để vét sâu.
- **Rủi ro trần `max_scrolls` thấp (Cũ: 40 -> Đã nâng: 90):** Anchor 300-400 following cần 60-80 lần vuốt. Giới hạn `max_scrolls = 40` sẽ cắt cụt nửa sau danh sách. Nâng trần lên 90 lần vuốt đảm bảo bao phủ tới 450 following.
- **Cơ chế chuẩn hóa:**
  1. Duy trì trần `max_scrolls = 90` và `idle_scrolls >= 25`.
  2. Bắt buộc dùng cơ chế phát hiện chạm đáy thật (True Bottom Detection) qua `seen_handles`: chừng nào sau mỗi lượt vuốt vẫn xuất hiện handle mới trên RecyclerView thì bot vẫn tiếp tục cuộn tìm nick farm nội bộ.
  3. Chỉ dừng khi thỏa mãn 1 trong các điều kiện:
     - Đã đạt đủ session budget (`used >= budget`).
     - Chạm đáy thật của danh sách (không phát hiện thêm handle mới sau 3 lần vuốt liên tiếp).
     - Chạm trần an toàn `max_scrolls`.
     - Hết thời gian phiên (`has_time_for_next_action() == False`).

## 3. Phân biệt các trường hợp "0 lượt an toàn" (status: OK) vs "Nhả Anchor" (FOLLOW_FAILED):
   - **TRƯỜNG HỢP 1: Bị chặn bởi Dual Gate (`budget = 0`):**
     * Log: `status: OK, followed: [], skipped: []`, thời gian chạy 0s (thoát ngay sau feed swipe).
     * Nguyên nhân: Nick chưa đủ điều kiện Dual Gate (`account_age_days < 30` HOẶC `video_count < 10`). Hệ thống tự động cấp `budget = 0` để bảo vệ nick non khỏi bị TikTok silent-drop / nhả follow.
     * Khi điều tra máy báo 0 lượt, BẮT BUỘC kiểm tra `video_count` và `account_age_days` trong safe workbook trước tiên.
   - **TRƯỜNG HỢP 2: Cuộn rỗng danh sách (`idle_scrolls >= 25`):**
     * Log: `status: OK, followed: [], skipped: []`, thời gian chạy ~70-95s (tương ứng 25 lần cuộn x ~3.8s/cuộn).
     * **SỰ THẬT VỀ LIST ANCHOR (CHỐNG SUY DIỄN MÒ):**
       + Danh sách Following của Anchor Tik1/Tik2 có **99.5% là nick nội bộ farm** (thực tế đối soát database: anchor follow 180-250 người thì 180+ nick là trong farm; nick anchor follow tự nhiên bên ngoài cực kỳ ít).
       + Nick ca tối (Row 4, Row 5...) là nick non mới nuôi, chỉ mới follow 0-5 người trong toàn bộ vòng đời (còn hơn 170+ nick farm trong list anchor chưa hề follow).
       + **CẤM TUYỆT ĐỐI suy diễn và giải thích nhảm nhí rằng: "Anchor follow người ngoài nhiều" hoặc "Nick non đã follow hết danh sách của anchor"**. Đây là ngụy biện vô căn cứ khiến User phản ứng gay gắt.
     * **NGUYÊN NHÂN GỐC RỄ THỰC TẾ KHI GẶP `idle_scrolls >= 25` TRÊN NICK NON:**
       + **Bẫy `missing_button_rows` khiến Mode 2 văng & Degrade sang Mode 1 báo "Đã follow sẵn":**
         - *Triệu chứng hiện trường:* Watchdog báo `Bỏ qua: Đã follow sẵn (11)` trên các nick non mới nuôi (M33, M59, M62, M65...).
         - *Bản chất sự cố:* Trong `follow_result.json`, `mode2_degraded: true` kèm lý do: `MANUAL_REVIEW: follower row không có nút follow semantic`.
         - *Cơ chế gây lỗi:* 
           1. Hàm `_cluster_follower_rows` và `_follow_button_for_row` trước đây phụ thuộc vào tuple cứng `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` (`id/u68`, `id/u2f`, `id/tcj`...).
           2. Khi TikTok đổi layout hoặc obfuscate resource-id của nút bấm, bot không gán được nút vào hàng (`r["follow_button"] = None`).
           3. `missing_button_rows` phát hiện row của nick farm hiển thị bình thường nhưng không thấy nút semantic nên fail-closed, ngắt Mode 2.
           4. `follow_engine.py` tự động chuyển sang Mode 1 search bù. Mode 1 tìm các nick farm an toàn, nhưng vì các nick này đã được follow từ các ca trước nên trả về `đã follow sẵn (skip)`. Operator nhìn vào báo cáo Watchdog chỉ thấy "Đã follow sẵn" mà không biết nguyên nhân gốc rễ là Mode 2 bị mù nút follow!
         - *Bản vá chuẩn hóa (Multi-tier Button Binding Fallback - Commit 8af3bc7):*
           Xây dựng hàm `_is_follow_button_node(n)` đa tầng:
           1. **Tầng 1 (Resource-ID):** Kiểm tra `(n.get("resource_id") or "").rstrip("/").endswith(FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS)`.
           2. **Tầng 2 (Bounds + Semantic Text Fallback):** Nếu resource-id bị đổi, kiểm tra nút bấm clickable nằm ở nửa phải màn hình (`bounds[0] >= 450`) và `text` hoặc `content_desc` thuộc tập từ khóa quan hệ `_RELATION_BUTTON_TEXTS` (`follow`, `follow lại`, `theo dõi`, `bạn bè`, `đang theo dõi`, `đã follow`, `following`, `friends`, `nhắn tin`...).
           3. Nhờ đó, mọi nút quan hệ dù mang resource-id mới lạ (`new_unknown_btn`) đều được bind chính xác vào hàng, triệt tiêu 100% lỗi `follower row không có nút follow semantic`.
       + **Bẫy `_classify_row_button` nhận nhầm trạng thái "đã follow sẵn":**
         - Tại `follow_runner/flows/mode2_follow_followers.py:188`, hàm `_classify_row_button` quét text và `content_desc` của nút qua danh sách `FOLLOWED_TEXT` ("Đã follow", "Following", "Bạn bè", "Nhắn tin"...).
         - Khi TikTok đổi layout hoặc subtext trong hàng/cluster bị overlap, nút quan hệ bị phân loại nhầm thành `followed`, dẫn tới `follow_one_follower` trả về `("skipped", "đã follow sẵn (skip)")` hàng loạt (ví dụ: M59 chưa từng follow ai nhưng bị skip 11 nick liên tiếp).
         - Khi tất cả hàng bị skip hoặc gán `follow_button = None` (`missing_button_rows`), `internal_pending` rỗng, bot kích hoạt vòng lặp vuốt `idle_scrolls += 1` lên 25 và thoát an toàn.
       + **Bẫy `_ensure_anchor_followed` kẹt cửa Profile video (Bằng chứng M8 chạy ~89s) & Bản vá Live Fallback:**
         - Tại dòng 504–575, trước khi vào Following list, bot tìm `video_covers` trên Profile anchor để xem video trước khi follow. Nếu không bắt được cover (`cover`, `tv_play_count`, `exx`, `aweme`), bot coi là `no_video` và safe-skip anchor.
         - *Lỗ hổng cũ:* Code cũ chặn fallback bằng điều kiện `if is_mock_adapter:`, khiến máy thật trên farm bị skip 100% khi không bắt được video cover.
         - *Bản vá chuẩn (Commit 613d201):* Mở fallback tap nút Follow trực tiếp trên Profile cho cả live device và mock adapter sau khi dwell. Chỉ khi không tap được nút mới coi là `no_video`.
       + **Bẫy telemetry mù khiến Operator không đọc được lỗi (Đã vá):**
         - Khi Mode 2 kết thúc với 0 lượt follow (`used == 0`), code cũ để `res.reason = ""` khiến Watchdog gom vào `Bỏ qua: Khác` gây mù hiện trường.
         - *Bản vá chuẩn:* Thu thập `skipped_anchors_reasons` và ghi rõ vào `res.reason = "MODE2_ANCHOR_EXHAUSTED: ..."` và `res.details['skipped_anchors']`, giúp báo cáo Telegram hiển thị minh bạch lý do từng máy kẹt ở đâu.
       + **Bẫy telemetry `skipped: []`:** Khi không nhận diện được nick nội bộ (`not internal_pending`), code cuộn tiếp mà không vào vòng `for row in pending`, nên `res.skipped` vẫn là `[]`.
       + **Kẹt trước khi vào list:** Bot chạy ~70-90s có thể do kẹt ở khâu tìm kiếm 2-3 anchor (`_nav_search` timeout 35s/anchor) rồi thoát ra mà chưa từng vào được list Following.
   - **TRƯỜNG HỢP 3: Chưa mở được Anchor hoặc Search không ra (`not_found`):**
     * Log: `status: OK, followed: [], skipped: []`, bot thử lần lượt qua 3-5 anchor và back về feed.
     * Nguyên nhân: Search anchor bị lag timeout hoặc màn hình tìm kiếm trả về không khớp thẻ card.
   - **TRƯỜNG HỢP 4: Bị nhả ngay tại Anchor (`FOLLOW_FAILED: anchor @{uid} bị nhả sau vuốt`):**
     * Xảy ra khi máy bốc trúng Anchor **chưa follow** và tìm kiếm thành công, vào được Profile anchor (`_ensure_anchor_followed`).
     * Bot xem video, thả tim, bấm Follow trên video rồi quay về Profile vuốt kéo reload kiểm tra.
     * Nút follow bị TikTok revert ngay lập tức về màu đỏ (`refreshed_classification == 'not_followed'`) ➔ Bot ngắt phiên ngay lập tức để bảo vệ nick. Lúc này máy thậm chí chưa kịp bấm vào tab Following của anchor.

## 4. Kỷ luật điều tra bắt buộc & Cảnh giác bẫy gõ `@` qua ADB
- **Cấm tự ý vá code khi Ca nuôi đang chạy:**
  * Trước khi đụng vào code runner, BẮT BUỘC kiểm tra xem farm có đang chạy ca live không (`psutil` kiểm tra `run_tiktok.py` hoặc inspect lock `~/.codex/device-locks`). Tuyệt đối không can thiệp code/process khi farm đang chạy ca (ví dụ Ca 1 sáng 06:00).
- **Cảnh giác bẫy gõ ký tự đặc biệt `@` bằng ADB (Case UI-08):**
  * Hàm `adapter.type_text` dùng `adb shell input text <string>`. Lệnh này trên Android (đặc biệt Galaxy S7) KHÔNG xử lý được ký tự `@` (bị nuốt hoặc lỗi ký tự). CẤM sửa `type_text(uid)` thành `type_text(f"@{uid}")` qua `input text` thô nếu không qua `AdbKeyboard` broadcast Base64.
- **Kỷ luật điều tra 0 lượt (Chống suy đoán mò):**
  * BƯỚC 1: Kiểm tra Dual Gate: `video_count >= 10` và `age >= 30` không? Nếu không -> `budget = 0` là hành vi đúng.
  * BƯỚC 2: Kiểm tra thời lượng chạy follow hook trong `log.jsonl`:
    - Dưới 10s: Thoát do budget = 0 hoặc cooldown.
    - ~70-100s: Chạm trần `idle_scrolls >= 25` (do trượt selector / mù UI) hoặc kẹt 2-3 anchor search timeout (~35s x 2). BẮT BUỘC kiểm tra selector nút follow / handle text / XML dump hiện trường, TUYỆT ĐỐI KHÔNG đổ lỗi "nick non đã follow hết list của anchor" hay "anchor toàn người ngoài".
    - ~3-5 phút: Bấm follow thật và bị nhả (`FOLLOW_FAILED`) sau quy trình xem video + reload.

## 5. Pitfall Unit Test Cô Lập `priority_targets.txt` (Regression Gate)
- **Hiện tượng:** Chạy `pytest follow_runner/tests/test_mode2_following.py` bị rớt test `test_anchor_prefers_row1_row2` với lỗi:
  `AssertionError: assert 'bangtam2311' in ('user_01', 'user_02')`.
- **Nguyên nhân gốc rễ:**
  * Hàm `FollowEngine.follow_uids()` tự động kiểm tra sự tồn tại của file `config/priority_targets.txt` (dùng cho các chiến dịch follow target bên ngoài do operator chỉ định).
  * Nếu file này có dữ liệu (ví dụ `@bangtam2311`), `follow_uids()` sẽ chèn các target ưu tiên này lên đầu danh sách trả về.
  * Test `test_anchor_prefers_row1_row2` khởi tạo `FollowEngine` thông thường mà không cô lập file cấu hình này, khiến `uids[0]` nhận giá trị `bangtam2311` thay vì `user_01` hoặc `user_02`.
- **Giải pháp chuẩn hóa (Pattern từ `test_priority_targets_prepend_and_dedup`):**
  * Trong test suite, bắt buộc tạo một thư mục repo cô lập trong `tmp_path`, ghi file `config/priority_targets.txt` rỗng.
  * Sử dụng `monkeypatch.setattr(follow_engine_module, "__file__", str(isolated_repo / "follow_runner" / "flows" / "follow_engine.py"))` để test đọc đúng file rỗng cô lập, bảo toàn thứ tự workbook ban đầu.

## 6. Khắc Phục Bẫy CRLF Explosion Gây `DIFF_TOO_LARGE` (>30,000 bytes) Trong Closeout Gate
- **Hiện tượng:** Khi sửa test file lớn như `test_mode2_following.py` (886 dòng), nếu file bị lưu ở định dạng Windows CRLF trong khi repo đặt `core.autocrlf = false`, `git diff` sẽ coi toàn bộ 886 dòng là thay đổi, làm dung lượng diff vọt lên 79KB.
- **Hậu quả:** `closeout_gate.py` fail ngay tại Step 2 với lỗi `DIFF_TOO_LARGE (79027 > 30000 bytes)` và từ chối gọi Reviewer.
- **Kỷ luật xử lý:** Phải giữ/chuẩn hóa file về LF (`b'\r\n' -> b'\n'`) trước khi add/commit, đưa diff thực tế về đúng phạm vi O(1) (<25 dòng thay đổi).


