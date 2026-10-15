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
   - **TRƯỜNG HỢP 2: Đã vào list Following nhưng không có nick farm chưa follow (`idle_scrolls >= 25`):**
     * Log: `status: OK, followed: [], skipped: []` (hoặc `skipped` có vài nick nếu có row internal xen kẽ), thời gian chạy ~70-95s (tương ứng 25 lần cuộn x ~3.8s/cuộn).
     * Nguyên nhân: Anchor có nhiều following nhưng phần lớn là nick tự nhiên ngoài farm, hoặc các nick farm trong list đó nick này đã follow hết từ trước.
     * **Cạm bẫy telemetry `skipped: []`:** Trong `mode2_follow_followers.py`, khi màn hình không có nick farm nào (`not internal_pending`), code lập tức cuộn tiếp (`_scroll_follower_list`) mà KHÔNG duyệt vòng lặp `for row in pending`. Do đó `res.skipped` VẪN LÀ `[]` dù bot đã mở list và cuộn 25 lần qua hàng chục nick ngoài farm. CẤM TUYỆT ĐỐI kết luận "skipped: [] là do không tìm thấy anchor".
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
    - ~70-100s: Đã vào Mode 2 cuộn 25 lần chạm trần `idle_scrolls >= 25`.
    - ~3-5 phút: Bấm follow thật và bị nhả (`FOLLOW_FAILED`) sau quy trình xem video + reload.
