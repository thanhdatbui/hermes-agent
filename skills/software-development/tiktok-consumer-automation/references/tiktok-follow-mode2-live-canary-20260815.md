# Mode 2 live canary — 6 run máy 1 (2026-08-15)

Kết quả: run 6 **OK** — follow follower list thật thành công `hoangthiennguyen_34`
(FOLLOW_RESULT status=OK, exit 0), state `BUDGET_USED=2`, `FOLLOWED_COUNT=3`,
không blocked. 5 run trước fail-closed đúng (không follow nhầm, state không đổi).

## Chuỗi fail→fix

| Run | Reason log | Stage fail thật | Fix |
|---|---|---|---|
| 1 | `MANUAL_REVIEW: không quay về được feed trước seed search` | `_back_to_feed` không detect Search history fullscreen (máy đang ở màn search do session trước để lại) | `_is_search_history_screen` v1: `tv_search_textview` + `tvl_recent_search`/`tvl_history` + không bottom-nav |
| 2 | cùng reason | vẫn không detect — **marker recent KHÔNG phải `tvl_recent_search`**; dump thật dùng content-desc `Thời gian`/`Đóng` cho mỗi item recent | mở rộng `_is_search_history_screen` nhận `content-desc ∈ {Thời gian, Đóng}` |
| 3-5 | cùng reason | đã qua `_back_to_feed` (probe tay + instrument `engine._debug` chứng minh: Search history → 1 Back → Feed nav); fail THẬT ở Path B: `_classify_profile_action` tự viết yêu cầu `clickable is True` → profile action `id/fds` clickable=false → `unknown` → Path B sample fail | `_classify_profile_action(xml_text)` delegate `verify_follow.classify_button` |
| 6 | — | — | **OK** |

## Bài học chính

1. **Cùng reason string ≠ cùng stage fail.** 5 run cùng log `"không quay về được feed..."` nhưng thực tế 2 lỗi khác nhau (detector thiếu marker, rồi Path B classifier). Đừng "sửa tiếp chỗ cũ" khi reason không đổi — instrument + probe để tìm stage thật.
2. **Instrument tạm bằng `engine._debug` hook** (không sửa production lâu dài): trong `_back_to_feed`, mỗi vòng dump ghi `{homes, profiles, searches, sf5, search_history, texts[:4]}` vào list nếu engine có attr `_debug`. Chạy `run_mode2` trực tiếp với engine thật + `_debug=[]` → đọc JSON để biết UI thấy gì mỗi vòng. Gỡ hook sau khi xong.
3. **Đừng đổ lỗi pycache/env khi code mới không ăn**: `rm -rf __pycache__` là red herring nếu `inspect.getsource(m2._is_search_history_screen)` đã chứa marker mới (verify trước khi xóa). Run fail do chạy trước khi patch, không phải cache.
4. **Marker UI KHÔNG nên khóa theo resource-id giả định**: dump thật dùng `Thời gian`/`Đóng` content-desc thay vì `tvl_recent_search`. Luôn probe trực tiếp detector trên `ui.xml` capture thật trước khi chốt.

## Chi tiết evidence

- Run OK: `%TEMP%\tiktok-follow-m1-mode2-live6-20260815-120223.log` — `FOLLOW_RESULT {"status":"OK","followed":["hoangthiennguyen_34"]}`, exit 0, HEAD `642aeab`.
- Post-run UI: `CLASS=followed` trên dump follower list (3 row `id/tcj`: 1 Đã follow + 2 Follow) — follower thật đã follow xong.
- 0 process follow sống sau run, không lock file.
- Commit: `642aeab` (Mode 1 + wiring + lockless), `cbc5a69` (Mode 2 fix Search history + classify delegate). Full suite 256 passed.
- Mode 2 wiring: `mode1_search_follow._nav_search` được Mode 2 import (dòng 41) — search nick (M1) → profile → tab Follower → follow từng follower (M2). `run_session` mode "both" = M1 → M2 cùng session budget.
