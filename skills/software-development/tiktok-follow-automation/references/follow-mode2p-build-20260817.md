# Build mode 2' — Following-list nội bộ (2026-08-17, commits `0ec5ef7` + `451ea5c` + `7e2e41f` + `2cbab70`)

Kết quả triển khai spec `follow-hybrid-following-list-20260816` trên repo
`D:\Taadaa\tiktok-follow`. Full suite **275 passed** (271 sau mode 2' + 4 test
gate video mới, bớt 18 test = gỡ tracker). ĐÃ XONG PHẦN B (sync gộp cột Video
Đã Đăng) + PHẦN C (gate video) + Claude code audit. Chưa canary live máy thật.

## Cấu trúc code ĐÃ ĐỔI (so với trước build)

- **`follow_runner/flows/mode2_follow_followers.py`** — mode 2 cũ (follow
  follower tab) đổi thành mode 2' (follow Following tab):
  - `_open_follower_tab` → **`_open_following_tab`** (search anchor → profile →
    verify exact @uid → tap tab **Đã follow/Following**). Dùng lại dump profile
    đã verify identity (KHÔNG dump thêm — tránh queue-cạn của test + tiết kiệm
    dump thật).
  - `_FOLLOWER_HEADER_RE` / `_FOLLOWER_EMPTY_LABELS` thêm `đã follow|following`.
  - Loop follow trong `run_mode2`: **lọc nội bộ** `_normalize_handle(uname) ∈
    internal_uids` (casefold toàn bộ `engine.follow_uids()`); external →
    append `res.skipped` 1 lần (qua `session_external_seen` set, KHÔNG persist
    state). **`if not internal_pending: break`** — list chỉ còn external đã seen
    → scroll vô ích → break, KHÔNG MANUAL_REVIEW scroll-cap.
  - **Inter-follow delay 30–90s** (`cfg.inter_follow_delay_min/max`) sau follow
    đầu (audit MAJOR-2 velocity).
- **`follow_runner/flows/follow_engine.py`** — `follow_uids()` **anchor ưu tiên
  Tik1/Tik2**: uid có `account_row_index ≤ 2` (1-based, từ
  `uid_source_mapping.rows`) đưa lên trước, phần còn lại sau. Dùng làm cả
  internal set lẫn seed loop.
- **`follow_runner/core/follow_state.py`** — `session_budget()` **bỏ clamp daily**:
  chỉ random `budget_per_session_min/max` (default 6–10); `budget_remaining()`
  không còn là trần.
- **XÓA hoàn toàn**: `core/follower_tracker.py`, `export_follower_tracking.py`,
  `tests/test_follower_tracker.py`, `tests/test_export_follower_tracking.py`,
  config `extra.follower_tracking` + 2 dòng wire `_track_follower` trong
  `verify_follow.py`. State `followed` dict giữ làm dedupe (mode 1 skip nick đã
  follow).
- **Tests**: `tests/test_mode2_following.py` mới (6 test: internal filter +
  external skip không persist, external-only → OK không MANUAL, anchor ưu tiên
  row1/2, budget không daily cap, inter-delay ≥30, empty → fallback). Migrate 71
  test cũ `test_mode2_follow_followers.py` sang semantics Following-list
  (`_follower_list_xml` header "Follower 3" → "Đã follow 3"; seeds động).

## PHẦN B (ĐÃ XONG commit `451ea5c`, nuôi acc repo) — sync gộp cột Video Đã Đăng

`safe-workbook sync` build **4 cột `May|Device ID|ID|Video Đã Đăng`** từ
taikhoandat_v2 + Tik1..Tik6 đối chiếu theo **ID** (mọi thứ quay về ID — user
chốt; không theo row/slot); acc không khớp file Tik nào (Tik4–6 chưa tồn tại)
→ **ghi 0**. Gate follow: ≥10 → full 6–10; <10 (kể cả 0) → nửa 3–5.
LUẬT: **1 writer duy nhất, KHÔNG thêm cron thứ 2** (sync rebuild-from-source
xóa state của writer khác — race nằm ở rebuild, không ở file lock); upload
KHÔNG ghi safe; follow đọc safe read-only. Chi tiết code:
- `sync-safe-workbook.py`: `_read_tik_video_counts(tik_dir)` đọc Tik1..Tik6 →
  `{id: video_count}`; `OUTPUT_COLS` 4 cột; verify check 4 cột + row count;
  `--tik-dir` flag (default `D:\OneDrive\TaadaaData\kibe`).
- `hermes_taikhoan_sync_cron.py`: `_source_signature()` = DAT sig + tik_sigs
  (mỗi TikN size/mtime) → Tik đổi → sync lại; state lưu cả 2; truyền `--tik-dir`.
- **Header "Video Đã Đăng" canonical trong sync repo = `video a ang`** (NFKD +
  bỏ combining) — KHÁC `workbook.py` follow repo (`video đa đang`, NFKC giữ dấu)
  — alias cover cả 2.
- Tests: 2 mới (merge theo ID + Tik dir missing → 0) + migrate 4-tuple assert.
  Dry-run thật OK: 480 rows, video khớp Tik1(8)/Tik2(1)/tik3(0). KHÔNG đụng
  safe thật khi test cron (env writer rỗng → chặn).

## PHẦN C (ĐÃ XONG commit `7e2e41f`) — gate video nửa budget

- `workbook.py`: `RowMapping.video_count` + `_parse_int` (float-string `"12.0"`/
  empty/`,` đều xử lý) + `_VIDEO_ALIASES` đầy đủ; `load_mapping` đọc cột
  Video Đã Đăng, **thiếu cột → None (fail-safe full budget)**.
- `follow_state.session_budget(video_count=None)`: `video_count < 10` (kể cả 0)
  → NỬA (random nửa base-min/max = 3–5); `≥10`/`None` → full 6–10.
- `follow_engine`: `self.video_count = getattr(row, "video_count", None)` ở
  `run_session` + `run_account_ready_only`; mode1/mode2 budget =
  `min(session_budget(video_count), ...)`.
- Tests: 2 follow_state (half/full/zero) + 2 workbook (đọc cột + fallback 3 cột).
- **Pitfall rewrite**: method `run_account_ready_only` + `_write_account_ready_artifacts`
  bị xóa nhầm khi rewrite khối try/except → 3 test fail AttributeError → khôi phục
  từ HEAD. Sau rewrite luôn đối chiếu `grep -n "def "` với HEAD.

## Audit code (commit `2cbab70`) — Claude Opus qua ag_audit_direct.py

Verdict **MINOR_FIXES — 7 findings, NHƯNG 6 false positive**: audit dùng tên file
KHÔNG tồn tại (`follow_mode2.py`, `video_gate.py`, `budget_manager.py`,
`tiktok_navigation.py`, `state_manager.py` — repo thật khác tên) và không đọc
được code thật (chỉ prompt). Đối chiếu code thật: F2 (float-string → `_parse_int`
đã cover), F3 (`_clean_header` đã normalize), F4 (session_external_seen bounded),
F5 (anchor 1-based đúng), F6 (file không tồn tại), F7 (`FOLLOWING_TAB_TEXT` đã có
EN "Following"). **F1 THẬT**: scroll loop khi list xen kẽ external — đã fix:
`consecutive_skip` counter, ≥20 external skip liên tiếp → break đổi anchor sớm.
**Quy tắc cho audit LLM: grep locator trước khi fix; file không tồn tại = finding
đáng ngờ; chỉ fix khi đối chiếu được code thật.**

## Pitfalls build (đã nộp vào SKILL.md — tóm tắt)

- CRLF file + `patch` tool → lệch indent (12/24-space) mỗi lần; rewrite nguyên
  khối bằng python.
- FakeAdapter cạn queue lặp phần tử cuối → scroll vô hạn MANUAL_REVIEW; push đủ
  dump hoặc XML đổi button.
- `_Engine.follow_uids()` = internal ∩ loop → seeds thiếu → all external.
- External skip vẫn vào `res.skipped` (báo cáo) nhưng không persist state.
- `_open_following_tab` còn dòng `wait_for_node(text="Follower")` thừa tiêu thụ
  dump → bỏ.

## Audit

Plan APPROVED sau 2 vòng AG Opus (`ag/claude-opus-4-6-thinking` qua
`ag_audit_direct.py`, 9router 127.0.0.1:20128): v1 MINOR_FIXES (selector
Following chưa spec, velocity 6–10 thiếu delay, hybrid double-follow, tracker
callers, skip phình state, gate cột thiếu, anchor off-by-one) → fix → v2
APPROVED + 1 MINOR (canary-max clamp). Cách gọi đúng script: truyền **path file
prompt**, không phải nội dung `$(cat ...)` (sai → exit 1 rỗng); timeout 600s →
background + notify.