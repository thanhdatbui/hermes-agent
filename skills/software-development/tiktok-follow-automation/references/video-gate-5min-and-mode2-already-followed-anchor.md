# Quy tắc Video Gate >= 5 & Mode 2 Anchor Already Followed (30/08/2026)

## Parent Feed Session Follow Hook Gating — 4 Cổng Bắt Buộc (Cập nhật 03/09/2026)

Trước khi `follow_runner` (repo `tiktok-follow`) được spawn, parent feed session (`python_runner/flows/multi_machine_feed_session.py` → `_run_follow_hook`, lines 1910–2100) ép **4 gate liên tiếp**. Gate nào fail → skip follow hook hoàn toàn (`status: "skipped"`, `failed: 0`, **không spawn subprocess**).

| Gate | Điều kiện | Hành động skip | Reason code |
|------|-----------|----------------|-------------|
| **1. Video Gate ≥ 5** | `video_count < 5` (0..4, `None`, empty) | Safe-Skip | `under-5-videos-follow-disabled` |
| **2. Warmup Phase Row 3–6** | `account_row_index ∈ {3,4,5,6}` | Safe-Skip | `tik{row}-warmup-feed-only` |
| **3. Feed Session Allowlist** | Feed `status ∉ {success, degraded}` **và** không phải fail do hết swipe/timeout | Safe-Skip | `sensitive-skip-{status}` |
| **4. Per-Nick Cooldown** | `follow_state_<M>_row_<idx>.json` có `follow_failed: true` hôm nay | Safe-Skip (chỉ nick đó) | `nick-cooldown-active` |

### 1. Video Gate >= 5 (Cập nhật 30/08/2026)
- **Quy tắc cứng:** Chỉ các tài khoản TikTok đã đăng tối thiểu **>= 5 video** (`video_count >= 5`) mới được kích hoạt Follow hook.
- **Lý do:** Các nick mới dưới 5 video chưa đủ điểm Trust Score tự nhiên, khi follow sẽ bị máy chủ TikTok áp cơ chế silent action-block và tự động nhả nút Follow (`FOLLOW_FAILED`) sau khi reload profile.
- **Cơ chế xử lý:**
  - `multi_machine_feed_session.py` (`_run_follow_hook`, lines 1939–1967): Nếu `video_count < 5` (0, 1, 2, 3, 4 video hoặc None), runner tự động Safe-Skip (`status: skipped`, `reason: under-5-videos-follow-disabled`), không kích hoạt subprocess follow.
  - `follow_state.py` (`FollowState.session_budget`): `video_count >= 5` cấp FULL budget (6–10 lượt); `video_count < 5` trả về budget `0`.

### 2. Warmup Phase Row 3–6 (Cập nhật 03/09/2026)
- **Quy tắc cứng:** Tik 3, 4, 5, 6 (Row 3–6) đang trong giai đoạn warmup (nuôi feed, up video) → **CẤM bật follow hook**.
- **Cơ chế:** `_run_follow_hook` (lines 1969–1989) check `row_idx in (3, 4, 5, 6)` → skip ngay, reason `tik{row}-warmup-feed-only`.
- Chỉ Row 1, Row 2 (đã đủ ≥5 video, qua warmup) mới được phép chạy follow.

### 3. Feed Session Allowlist (Cập nhật 03/09/2026)
- Chỉ cho phép follow hook khi phiên feed **thành công** hoặc **fail an toàn do hết budget swipe/timeout**:
  - Allow status: `success`, `degraded`.
  - Allow stop_reason: `feed_swipe_limit_reached`, `swipe_timeout`, `feed_session_limit_reached`, `max_swipes_completed`, `swipe_limit`, `feed_swipe_limit`.
- Fail do popup login, account error, recovery kẹt, manual challenge, sensitive marker → **Skip follow hook** (reason `sensitive-skip-{status}`).

### 4. Per-Nick Cooldown Check (Cập nhật 03/09/2026)
- Đọc file state `D:/Taadaa/tiktok-follow/runs/state/follow_state_<machine>_row_<index>.json`.
- Nếu nick bị `follow_failed: true` + `follow_failed_date: today` → **chặn riêng nick đó** (nick khác trên máy vẫn chạy bình thường).
- Đây là cơ chế tách biệt cooldown theo nick, không khóa cả máy.

---

## 2. Mode 2 Follow Chéo — Anchor Đã Follow / Nút Bạn bè (30/08/2026)

---

## 2. Mode 2 Follow Chéo — Anchor Đã Follow / Nút Bạn bè (30/08/2026)
- **Quy tắc cứng:** Khi Mode 2 tìm kiếm anchor nick (nick Tik1/Tik2):
  - Nếu profile anchor đã được follow từ trước, hoặc hiển thị nút `"Bạn bè"`, `"Nhắn tin"`, `"Đang theo dõi"` (không có nút `"Follow"` đỏ), runner **tuyệt đối KHÔNG được coi là unknown hay skip/error**.
  - Runner xác nhận `already_followed`, tiếp tục giữ nguyên luồng để mở tab Đang theo dõi / Following (`FOLLOWING_TAB_TEXT`: `"Đã follow"`, `"Following"`, `"Đang theo dõi"`) của anchor để quét các nick nội bộ farm bên trong.
- **Feed Precondition & Swipe trước Search Anchor:**
  - Trước khi search mỗi anchor UID, sau khi đảm bảo giao diện đang ở Feed (`_back_to_feed`), luôn thực hiện lướt nhẹ trên Feed (`swipe_before_search` 1–3 video) tạo hành vi người dùng tự nhiên như Module 1 rồi mới bấm Search.
- **Quy trình Verify Nick Con trong List Following (Path A + Path B):**
  - Sau khi tap nút Follow ở danh sách row (Path A), **100% tự động bấm vào xem trang profile nick vừa follow (Path B)** để kiểm tra có bị nhả follow không.
  - **Không cần vuốt refresh** trên profile nick con: Chỉ cần dump XML kiểm tra nút quan hệ (`Bạn bè` / `Đang theo dõi` / `Follow`). Nếu vẫn là `Follow` (bị nhả follow) -> đánh dấu `FOLLOW_FAILED` dừng toàn bộ session ngay lập tức. Nếu hợp lệ -> nhấn `back` quay lại list để follow tiếp.
- **Cuộn List Following Không Bị Ngắt Sớm:**
  - Không ngắt sớm bằng ngưỡng `consecutive_skip` nick ngoài farm: Tiếp tục cuộn tìm nick farm nội bộ cho đến khi chạm đáy/hết list following của anchor hoặc đã đạt đủ budget.
- **Selectors & Fallback:**
  - `FOLLOWED_TEXT` mở rộng: `"Đã follow"`, `"Đang theo dõi"`, `"Following"`, `"Nhắn tin"`, `"Nhắn tin nhắn"`, `"Gửi .."`, `"Gửi tin nhắn"`, `"Message"`, `"Bạn bè"`, `"Friends"`, `"Tin nhắn"`.
  - `FOLLOWING_TAB_TEXT` mở rộng: `"Đang follow"`, `"Đang Follow"`, `"Đã follow"`, `"Following"`, `"Đang theo dõi"`.
  - `_following_tab_node`: Hỗ trợ nhận diện cả nhãn tab chứa số lượng (`120 Đang theo dõi`, `120 Đã follow`, `120 Đang follow`) ở hàng tab trên profile (`y < 550`).
- **Anchor 0 Following / Không Có Danh Sách Following (31/08/2026):**
  - **Hiện tượng:** Khi profile anchor có `0 Đang follow` / `0 Đã follow` / `0 Following`, tap vào chỉ số này trên TikTok 46.x không mở ra danh sách mà đứng im tại màn hình profile. Khay "Tài khoản được đề xuất" có thể bung ra bên dưới chứa các nút `Follow` màu đỏ của nick khác.
  - **Cấm đoán:** TUYỆT ĐỐI CẤM raise `MANUAL_REVIEW` hay coi là kẹt UI dừng phiên khi gặp anchor 0 following. CẤM nhầm lẫn nút Follow đỏ của nick đề xuất là anchor bị nhả follow.
  - **Quy trình xử lý chuẩn:**
    1. Kiểm tra sớm `_is_zero_following_profile`: Nếu chỉ số Following là `0`, skip ngay không cần tap chờ timeout 10s.
    2. Nếu không mở được tab Following (`open_ok == False`) và không phải bị nhả follow (`state.follow_failed == False`), runner tự động gọi `_back_to_feed(engine)` quay về Feed an toàn và `continue` duyệt anchor tiếp theo trong pool.
    3. Nếu tất cả anchor đều rỗng, Mode 2 kết thúc `status = "OK"` với 0 follow để Mode 1 (hybrid) tự động tìm kiếm bù budget.

---

## 3. Phân loại Watchdog: Phân biệt Máy Fail Feed vs Lỗi Follow
- **Vấn đề đã khắc phục:** Khi một máy bị lock/fail ở bước lướt Feed, máy đó không chạy Follow hook (không có `follow_result.json`).
- **Quy tắc báo cáo watchdog (`feed_session_watchdog.py`):**
  - Chỉ tính máy vào nhóm *"Lỗi script/xác minh"* của Follow/Upload nếu máy đó **đã lướt Feed thành công (`status: success`)** nhưng Follow/Upload hook bị lỗi.
  - Các máy fail Feed hoặc bị lock thiết bị từ trước không được tính vào lỗi của Follow hook.
