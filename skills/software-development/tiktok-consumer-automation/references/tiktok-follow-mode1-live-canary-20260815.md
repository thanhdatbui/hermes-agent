# tiktok-follow Mode 1 — live canary máy 1 (4 run, 2026-08-15) + B1 hardkill

Kết quả: **run thứ 4 `FOLLOW_RESULT {"status":"OK","followed":["charakrh768"]}`** — lần đầu
Follow thật thành công trên máy 1. State sau run: `BUDGET_USED=1`, `FOLLOWED_COUNT=2`
(thêm charakrh768), `BLOCKED=False`; post-live capture `CLASS=followed` (nút đã thành
"Đã follow"); 0 process follow sống; không lock file. HEAD `07b23a1259061ee0c7e1f5213e1c1da25a559593`
(dirty worktree — CHƯA commit, chờ user).

## Bốn lần canary — mỗi lần fail-closed ĐÚNG, không tap bậy, state/budget không đổi

| Run | Exit | Lỗi live bắt được | Fix canonical | Tests |
|---|---|---|---|---|
| 1 | 1 | Search autocomplete: input echo exact UID nhưng mọi suggestion `tvl_unified_sug` gần đúng → `_wait_search_result` timeout | `_unique_search_submit`: đúng 1 Button `clickable` + bounds + class `android.widget.Button` + rid suffix `id/tv_search_textview` + text ∈ {tìm kiếm, search}; chỉ submit khi chưa có exact suggestion | +1 |
| 2 | 1 | `OPEN_TIKTOK` fail vì backend ATX JSON-RPC HTTP 502 + shell `uiautomator dump` timeout trong khi screencap vẫn cho thấy Feed bình thường | B1 hardkill: `pkill -9 -f atx-agent` + `pkill -9 -f uiautomator` + `am force-stop com.github.uiautomator` + `uiautomator quit` → `capture_persistent_ui` chấp nhận chỉ khi verified XML; **+1 warmup recapture** (`restart_attempts=0`) vì lần capture đầu sau hardkill có thể trả XML None dù service vừa start (live chứng minh: `ATTEMPT_COUNT=2` → VERIFIED_HEALTHY 96,558 bytes) | +3 |
| 3 | 1 | Search submit PASS, identity PASS, nhưng classifier "không thấy đúng một nút Follow": profile render nút Follow là TextView `id/fds` **clickable=false, KHÔNG ancestor clickable** (vùng bấm flatten không expose trong hierarchy) và cùng profile có label stats "Đã follow" `id/sdn` (cũng non-clickable) | `classify_button` ưu tiên node action rid suffix `id/fds` khi ambiguous (stat + action); `_action_targets` chấp nhận non-clickable label có bounds khi duy nhất; `_node_or_clickable_ancestor` fallback cho layout ancestor clickable thật | +4 |
| 4 | **0** | — | — | 253 passed |

## Dump thật profile đích (run 3, `%TEMP%\tiktok-follow-m1-postlive3-20260815-102136\ui.xml`)

```
text='Đã follow'  rid=...:id/sdn   clickable=False  bounds=(88,711,300,48)   ← stats label
text='Follower'   rid=...:id/sdn   clickable=False  bounds=(456,717,168,42)
text='Follow'     rid=...:id/fds   clickable=False  bounds=(114,789,348,132) ← ACTION thật
```
Ancestor chain của `id/fds`: LinearLayout `id/fdu` → `id/fdm` → ... — TẤT CẢ `clickable=false`.
Không node nào clickable ngoài `@hongggg.yn` (sf5) và tab "video". → ancestor-clickable
fallback trả 0; chỉ path "non-clickable label có bounds + duy nhất" hoặc "ưu tiên id/fds" cứu.

## Invariant rút ra (đã merge vào SKILL.md mục Search-Follow #3)

1. **KHÔNG yêu cầu clickable cho action button TikTok** — `id/fds` là TextView `clickable=false`
   không ancestor clickable. Clickable-only classifier (như bản đầu canary run 3) fail-closed
   MÃI (0 target) dù profile ĐÚNG.
2. **Stat label vs action button cùng marker**: "Đã follow" `id/sdn` (stats) + "Follow" `id/fds`
   (action) cùng tồn tại trên 1 profile → 2 node trùng marker → ambiguous → phải ưu tiên
   `id/fds`. Không ưu tiên = unknown vĩnh viễn.
3. `test_classify_nonclickable_follow_label_is_not_an_action` (cũ) assert clickable-only →
   SAI với reality → phải sửa thành "non-clickable label có bounds + id/fds = action"
   (TDD: test cũ fail vì đúng lý do).
4. Thứ tự ưu tiên `_action_targets`: (a) clickable node mang label; (b) non-clickable label
   có ancestor clickable bounded; (c) non-clickable label có bounds DUY NHẤT. Ambiguity
   (≥2 cùng state) fail-closed.

## B1 hardkill + warmup recapture (run 2)

- Signature: persistent `/jsonrpc/0` trả HTTP 502; shell `uiautomator dump` timeout;
  screencap vẫn chứng minh Feed render bình thường → KHÔNG kết luận Feed fail từ UI-backend fail.
- `recover_persistent_ui` cleanup: `pkill -9 -f atx-agent`, `pkill -9 -f uiautomator`,
  `am force-stop com.github.uiautomator`, `uiautomator quit` (đúng `_recover_uiautomator` core).
- Sau hardkill, `capture_persistent_ui(restart_attempts=1)` có thể trả `xml=None` (service vừa
  start) → **re-observe 1 lần `restart_attempts=0`** → live: attempt 1 `UNHEALTHY`/no-XML,
  attempt 2 `VERIFIED_HEALTHY` 96,558 bytes. Fail-closed nếu vẫn None.
- CẤM restart ADB / reboot / pm clear trong B1.

## Workflow canary (đã chạy đúng)

1. Preflight: dump + parse node counts (171 nodes, identity `sf5` count=1, clickable flags),
   `PRODUCTION_BUSY_GUARD` check, `follow_uids` total 242 → 241 sau self-exclusion.
2. Config thật `%TEMP%\tiktok-follow-m1-mode1-canary.yaml`: `mode: "1"`, `budget_per_session: 1`,
   `verify_reload_retries: 2`, `delay_min/max: 1/5`, `swipe_before_search: 3`, `swipe_between_follows: 1`.
3. Chạy: `PYTHONPATH=<wheel 0.4.44> python -B -m follow_runner.run_follow --machine 1 --mode 1
   --config <yaml> --account-row-index 1` (background + notify + meta file ghi HEAD/sha256/log).
4. Xác minh: log `FOLLOW_RESULT`, state json (`BUDGET_USED`/`FOLLOWED_COUNT`), post-live
   capture `CLASS=followed`, process/lock scan 0.
