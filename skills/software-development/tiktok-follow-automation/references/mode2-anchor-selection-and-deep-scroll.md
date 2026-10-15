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
   - **TRƯỜNG HỢP 1: Chưa mở được Anchor hoặc Search không ra (`skipped: []`, `followed: []`):**
     * Log: `skipped: []`, thời gian chạy ngắn (60-90s cho 3 anchor).
     * Nguyên nhân thực tế: Bot gõ UID anchor vào thanh tìm kiếm nhưng `_nav_search` trả về `not_found` (mạng lag, TikTok đổi layout search, hoặc không khớp exact thẻ card anchor), hoặc không xác minh được profile anchor.
     * Code tự động `_back_to_feed` và thử tiếp anchor kế tiếp. Hết 3 anchor không mở được ai -> thoát an toàn `status: OK, followed: 0`.
     * **Nick non (Row 5 ca tối) gặp 0 lượt mà `skipped: []` là 100% do trường hợp này**, tuyệt đối KHÔNG ĐƯỢC suy đoán bậy bạ là "đã follow hết list anchor" vì nick non mới tạo lịch sử cả đời mới follow vài nick.
     * Vì chưa mở được vào và chưa bấm nút Follow của bất kỳ ai, TikTok không có hành động để nhả -> cờ `follow_failed` giữ sạch nguyên.
   - **TRƯỜNG HỢP 2: Đã vào danh sách nhưng không có nick farm hợp lệ (`skipped: [uid1, uid2...]`):**
     * Log: `skipped` có chứa danh sách các handle bên ngoài farm (như M59 có 11 nick skipped).
     * Nguyên nhân: Đã mở được tab Following của anchor, nhưng các nick nhìn thấy là người ngoài farm (hoặc nick farm nhưng tài khoản đã follow từ trước).
     * Cuộn tới ngưỡng dừng an toàn (`idle_scrolls >= 25`) không còn nick mới -> dừng `status: OK, followed: 0`.
   - **TRƯỜNG HỢP 3: Bị nhả ngay tại Anchor (`FOLLOW_FAILED: anchor @{uid} bị nhả sau vuốt`):**
     * Xảy ra khi máy bốc trúng Anchor **chưa follow** và tìm kiếm thành công, vào được Profile anchor (`_ensure_anchor_followed`).
     * Bot xem video, thả tim, bấm Follow trên video rồi quay về Profile vuốt kéo reload kiểm tra.
     * Nút follow bị TikTok revert ngay lập tức về màu đỏ (`refreshed_classification == 'not_followed'`) ➔ Bot ngắt phiên ngay lập tức để bảo vệ nick. Lúc này máy thậm chí chưa kịp bấm vào tab Following của anchor.

## 4. Chi tiết kỹ thuật lỗi `not_found` khi tìm kiếm Anchor & Chuẩn hóa cách xử lý
- **Bản chất `not_found` trong `_nav_search`:**
  1. Bot gõ UID anchor vào thanh tìm kiếm TikTok (`_nav_search`).
  2. TikTok mở tab "Top": bot chờ thẻ user (`account_card` có `tv_username` hoặc `tv_aweme_id`) tối đa 12s.
  3. Nếu không có, bot tự động click tab "Người dùng" (Users) và chờ tiếp 12s.
  4. Nếu cả 2 tab đều không render ra thẻ user khớp exact normalized UID -> bot gán `_last_search_outcome = "not_found"`.
- **Nguyên nhân gốc rễ (Root Causes):**
  - **Gõ UID trần thiếu `@`:** `adapter.type_text(uid)` gõ chuỗi trần khiến thuật toán TikTok hiểu là tìm kiếm từ khóa nội dung chung (Video/Sound/Shop), đẩy thẻ User xuống dưới màn hình hoặc ẩn khỏi tab Top. Khi gõ kèm tiền tố `@` (`@{uid}`), TikTok nhận diện ngay đây là handle người dùng và ưu tiên hiển thị thẻ profile lên đầu.
  - **Timeout 12s không đủ bù độ trễ proxy:** Trên mạng VPN/proxy giờ cao điểm, trang kết quả tìm kiếm mất 13-16s để render danh sách user. Hết 12s bot đã vội timeout.
  - **Anchor Pool thử nghiệm quá hẹp (`uids[:3]`):** Chỉ lấy tối đa 3 anchor ngẫu nhiên. Nếu cả 3 anchor trúng nick khó search hoặc lag mạng, bot cạn anchor và thoát phiên 0 lượt.
- **Kỷ luật điều tra bắt buộc (Chống suy đoán bậy):**
  - Khi thấy máy trả về `status: OK, followed: 0`, BẮT BUỘC kiểm tra trường `skipped`:
    * `skipped: []` + thời gian chạy ~60-90s: Chắc chắn là chưa mở được Anchor (bị `not_found` ở bước tìm kiếm), CẤM TUYỆT ĐỐI bịa chuyện "đã follow hết list".
    * `skipped: [...]` (có handle): Đã vào được list và lướt qua nick ngoài farm.
  - Giải pháp code chuẩn khi nâng cấp:
    1. Gõ `@uid` thay vì `uid` trần: `adapter.type_text(f"@{uid.lstrip('@')}")`.
    2. Nâng timeout render `_wait_search_result` từ 12s lên 18s để dung sai tốt hơn với proxy.
    3. Mở rộng số lượng thử anchor từ 3 lên 5 (`uids[:5]`) để tăng khả năng chạy đủ budget.
