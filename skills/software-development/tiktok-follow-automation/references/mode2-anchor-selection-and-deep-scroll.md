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
       + **Bẫy `_classify_row_button` nhận nhầm trạng thái "đã follow sẵn" (Bằng chứng M59/M65):**
         - Tại `follow_runner/flows/mode2_follow_followers.py:188`, hàm `_classify_row_button` quét text và `content_desc` của nút qua danh sách `FOLLOWED_TEXT` ("Đã follow", "Following", "Bạn bè", "Nhắn tin"...).
         - Khi TikTok đổi layout hoặc subtext trong hàng/cluster bị overlap, nút quan hệ bị phân loại nhầm thành `followed`, dẫn tới `follow_one_follower` trả về `("skipped", "đã follow sẵn (skip)")` hàng loạt (ví dụ: M59 chưa từng follow ai nhưng bị skip 11 nick liên tiếp).
         - Khi tất cả hàng bị skip hoặc gán `follow_button = None` (`missing_button_rows`), `internal_pending` rỗng, bot kích hoạt vòng lặp vuốt `idle_scrolls += 1` lên 25 và thoát an toàn.
       + **Bẫy `_ensure_anchor_followed` kẹt cửa Profile video (Bằng chứng M8 chạy ~89s):**
         - Tại dòng 504–575, trước khi vào Following list, bot tìm `video_covers` trên Profile anchor để xem video trước khi follow. Nếu không bắt được cover (`cover`, `tv_play_count`, `exx`, `aweme`), bot coi là `no_video` và safe-skip anchor.
         - `run_mode2` chỉ lấy tối đa 3 anchor (`uids = uids[:3]`). Nếu cả 3 anchor đều bị skip ở khâu tìm video cover, bot thoát vòng lặp, kết thúc phiên với `status: OK, followed: 0` mà **hoàn toàn chưa từng mở vào tab Following**.
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
