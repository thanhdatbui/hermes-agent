# Nối feed-session (nuôi acc) trước follow — quyết định 2026-08-15

Bối cảnh: user muốn chạy feed-session (lướt dài) TRƯỚC khi follow mục tiêu trên
cùng máy, và hỏi có nên giảm lượt swipe của feed-session không.

## User quyết định (bắt buộc, không hỏi lại)
1. **Lướt DÀI rồi mới follow** — "Chấp nhận lướt lâu r ms đi follow, t nghĩ v
   nó uy tín hơn là lướt có tý r đi follow luôn". KHÔNG giảm swipe khi nối.
2. **Nối ở tầng lệnh**: "K cần tách lên hàm core. Chỉ cần m nối nguyên repo kia
   vào, là trỏ về repo kia". Không import chéo repo, không tách hàm swipe lên
   automation-core (dù update sau này phải sửa 2 repo — user chấp nhận).
3. **Follow lạ trong feed KHÔNG hại** (user đính chính): pattern bot thật là
   search chính xác → follow liên tục; follow lạ rải rác (rate thấp) làm loãng
   chuỗi đó = real hơn. Cái nguy thật là tổng follow/đơn vị thời gian (đã có
   `budget_per_session` + FOLLOW_FAILED chặn), KHÔNG phải "follow lạ".

## Sự thật từ code 2 repo (đã verify 2026-08-15)
- **tiktok-follow**: `swipe_feed` sẵn có (`follow_runner/core/adapter.py:438`),
  config `swipe_before_search: 3` (mỗi UID) + `swipe_between_follows: 1` —
  swipe "kỹ thuật": tọa độ theo screen size, KHÔNG watch delay, không like.
- **feed-session (nuôi acc)**: watch delay random 2–8s/video, like DEFAULT 12%
  (for-you) / follow DEFAULT 5% (`DEFAULT_FEED_LIKE_RATES`/`DEFAULT_FEED_FOLLOW_RATES`).
  Số `100` trong lệnh ví dụ skill = flag TEST ép hành vi verify selector.
- `selected_total_videos = random.randint(min, max)` — chọn 1 lần cho cả
  session (VD 15–30); `videos_until_tab_decision = random.randint(3, 8)` — cứ
  3–8 video mới cân nhắc đổi tab (DEFAULT_FEED_DISTRIBUTION: For You 98%).
- **multi-machine-feed-session LUÔN close app sau feed**:
  `multi_machine_feed_session.py:685` + `:921` hardcode
  `_cleanup_close_all_after_session = True` → `cleanup_after_tiktok_smoke` =
  `close_all_recent_apps` (keyevent 187 → "Xóa tất cả" → HOME). Đây chính là
  "chạy xong nó close hết app" user quan sát. Mặc định False ở single-mode,
  CHỈ multi-machine ép True.
- `_defer_cleanup_close_all_after_session` đã tồn tại trong feed_swipe_smoke.py
  (`_should_defer_cleanup_close_all`, mặc định False) — giữ app mở sau feed,
  nhưng CHƯA được lộ qua multi-machine/CLI (muốn nối liền mạch 1 phiên phải
  lộ flag này).
- **Follow runner tự xử lý cold start**: prepare + relaunch TikTok khi bắt đầu
  (proven canary máy 1/máy 2) → chạy follow sau khi feed close app vẫn OK, chỉ
  mất "liền mạch 1 phiên".

## Plan đề xuất (chưa thực thi — chờ user xác nhận)
1. Nuôi acc repo: lộ flag defer cleanup qua multi-machine (mặc định giữ True
   như cũ để không đổi hành vi hiện tại).
2. Script nối tầng lệnh: `run-feed-session.ps1` → `run_follow.py --machine N
   --account-row-index R` trên CÙNG serial (không sửa code 2 repo).
3. Không đụng automation-core; chạy test 2 repo + canary 1 máy (gate live:
   HỎI acc row + order trước khi follow thật).

## Đừng lặp lại (sai đã sửa trong session này)
- KHÔNG nói feed-session "like/follow 100%" — default 12%/5%.
- KHÔNG nói "15–30 video mà random 3–8 mỗi lượt" — 3–8 là khoảng đổi tab,
  tổng video chọn 1 lần.
- KHÔNG gọi follow lạ trong feed là "trùng follow" — user đính chính là TỐT
  (real hơn).
