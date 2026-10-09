# No-video false positive — Mode 2 anchor verify (2026-09-13)

## Hiện tượng
Watchdog báo hàng loạt "Lỗi script/xác minh" Follow (34 máy) + Upload (27 máy).
Thực tế: anchor luôn có video; script kết luận sai `no_video`.

## Root cause
`follow_runner/flows/mode2_follow_followers.py::_ensure_anchor_followed` (~dòng 522-525):
gate `if is_mock_adapter:` chặn fallback tap Follow profile trên máy thật.
Dump sau `_nav_search` chưa cuộn tới lưới video + chỉ swipe bù 1 lần (dòng 503-505)
-> kết luận vội `no_video`, back ra bỏ qua.

Bằng chứng: `verify_profile/ui.xml` máy 12 chứa 4 node
`com.ss.android.ugc.trill:id/tv_play_count` ở y=1271/1751, `_parse_mode2_nodes`
parse đúng 4 video_covers với filter hiện tại — filter không sai, sai là kết luận.

## Fix class-level (patch 2 dòng, giữ logic fallback nguyên)
- old: `# Hỗ trợ mock unit tests cũ...` + `if is_mock_adapter:`
- new: `# Anchor luôn có video — dump chưa cuộn tới lưới là nguyên nhân chính...` + `if True:  # ex-is_mock_adapter (mở cho live device)`
- Verify: focused pytest `-k test_open_following_tab_searches_seed_then_opens_its_follower_list` → `1 passed in 1.17s`.
- Repo dirty 5 file chưa commit tại thời điểm fix — giữ nguyên, cấm reset/cấm commit vội.

## Pitfall cho lần sau
- User khẳng định "anchor luôn có video" = tín hiệu ưu tiên kiểm tra gate mock/live,
  không phải đi chứng minh filter resource-id đúng trên XML không liên quan.
- Profile anchor không có artifact lưu → đừng cố tìm XML anchor; suy luận từ code path.

## Kỷ luật coordinator (user nhắc 2026-09-13: sa đà quét ổ đĩa cả tiếng)
- Coordinator chỉ inspect O(1): `inspect_machine.py`, 1 file xác định, grep count 1 path đã biết.
- Mọi reproduce/verify/test giao worker qua `delegate_task` (fail-fast ≤3 iter, 15 calls).
- Worker timeout 600s = thất bại cấu trúc (Gate 3): cấm retry prompt cũ, re-dispatch contract mới hẹp hơn.
- Báo cáo Follow tách Module 2 (following-list nội bộ) / Module 1 (search bù):
  passthrough `details.mode1/mode2_followed_count` từ `run_follow._result_payload`
  vào `feed_session_watchdog.parse_run_all`, cộng dồn toàn phiên, thêm 1 dòng báo cáo.
