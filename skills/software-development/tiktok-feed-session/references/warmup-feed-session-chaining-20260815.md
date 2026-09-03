# Nối feed-session trước follow + sự thật rate/cleanup (2026-08-15)

Session này user hỏi về việc nối feed-session (nuôi acc) đứng trước bước follow
mục tiêu. Đã đọc code 2 repo và user chốt quyết định. Tài liệu này là nguồn
tham chiếu cho cả 2 skill (tiktok-feed-session + tiktok-follow-automation).

## Rate mặc định — KHÔNG phải 100%
- like 12% (for-you) / follow 5%: `DEFAULT_FEED_LIKE_RATES` /
  `DEFAULT_FEED_FOLLOW_RATES` trong `python_runner/flows/feed_swipe_smoke.py`.
- Số `100` xuất hiện trong lệnh ví dụ (`--like-rate '{"for_you":100,...}'`) là
  flag TEST ép hành vi verify selector, KHÔNG phải production default.

## Random video — 2 thứ khác nhau (đừng nhầm)
- `selected_total_videos = random.randint(requested_min_total_videos,
  requested_max_total_videos)` — chọn 1 LẦN cho CẢ session (VD 15–30).
- `videos_until_tab_decision = random.randint(3, 8)` — cứ 3–8 video mới cân
  nhắc đổi tab; `DEFAULT_FEED_DISTRIBUTION` = For You 98% / Following 2%.
- KHÔNG nói "random 3–8 video mỗi lượt" — đó là khoảng đổi tab (user correction).

## multi-machine LUÔN close app sau feed (nguồn "chạy xong close hết app")
- `multi_machine_feed_session.py:685` + `:921` hardcode
  `child_config["_cleanup_close_all_after_session"] = True`.
- `cleanup_after_tiktok_smoke` = `close_all_recent_apps`
  (`flows/device_prepare.py:420`): keyevent 187 (Recent) → tap "Xóa tất cả" →
  HOME. TikTok bị tắt sau mỗi feed-session multi-machine.
- Mặc định False ở single-mode (`feed_swipe_smoke._cleanup_close_all_enabled`);
  CHỈ multi-machine ép True.
- `_defer_cleanup_close_all_after_session` đã tồn tại (`feed_swipe_smoke.py`,
  `_should_defer_cleanup_close_all`, mặc định False) — giữ app mở sau feed,
  NHƯNG chưa được lộ qua multi-machine/CLI. Muốn nối feed→follow liền mạch 1
  phiên phải lộ flag này.

## User CHỐT hướng nối (2026-08-15)
1. Lướt DÀI trước follow — "lướt lâu rồi mới follow uy tín hơn là lướt có tí
   rồi follow luôn". KHÔNG giảm swipe feed khi nối.
2. Nối ở TẦNG LỆNH (script chạy 2 lệnh trên cùng serial), không import chéo
   repo, không tách hàm swipe lên automation-core ("K cần tách lên hàm core.
   Chỉ cần nối nguyên repo kia vào").
3. Follow lạ rải rác trong feed = TỐT (real hơn), không phải "trùng follow";
   nguy thật là tổng follow/đơn vị thời gian (đã có budget_per_session +
   FOLLOW_FAILED).

## Follow runner tự xử lý cold start
- `tiktok-follow` prepare + relaunch TikTok khi bắt đầu (proven canary máy 1/2)
  → chạy follow sau khi feed close app vẫn OK, chỉ mất "liền mạch 1 phiên".
- `swipe_feed` bên follow (`follow_runner/core/adapter.py:438`) là swipe kỹ
  thuật: tọa độ theo screen size, không watch delay, không like; config
  `swipe_before_search: 3` + `swipe_between_follows: 1`.

## Plan đề xuất (chưa thực thi — chờ user xác nhận)
1. Nuôi acc repo: lộ flag defer cleanup qua multi-machine (mặc định giữ True).
2. Script nối tầng lệnh: run-feed-session.ps1 → run_follow.py --machine N
   --account-row-index R trên CÙNG serial.
3. Không đụng automation-core; test 2 repo + canary 1 máy (gate: HỎI acc row +
   order trước follow thật).
