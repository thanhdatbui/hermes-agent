# 2026-08-15 — Avatar sweep recovery: ATX-kill retry, Recents escape, workbook scope

Session detail for the 55→56-machine `-AvatarOnly` sweep fixes. SKILL.md already
carries the CONNECT_DEVICE ladder fix (B1→B2→B3) and COMPAT-AVATAR-011; this file
holds the recovery-layer lessons that came after.

## B1 ATX-kill must run on EVERY retry attempt of `_execute_with_ui_retry`

User correction (2026-08-15): "rule 3 bước trc t cài là gặp lỗi UI cứ ATX r làm
liên tục r mà, chỉ có reboot và relaunch B2 và B3 chỉ đc làm 1 lần".

- Original rule: B1 (ATX-kill) is UNBOUNDED — run every time a UI/dump error is
  hit, INCLUDING between retry attempts of the same state; only B2 (relaunch)
  and B3 (soft reboot) are bounded 1×/turn/machine (B3 additionally
  1×/failure-signature via `soft_reboot_recovery_attempts[signature] >= 1`).
- `_execute_with_ui_retry` retried the handler 3× with NO ATX-kill between
  attempts → a wedged uiautomator stayed wedged across all retries.
- Fix (commit `6870d45`): before each retry attempt
  (`if attempt < ui_retry_limit and not is_ui_unavailable`) call
  `_recover_uiautomator(adb, timeout=10, attempts=[], label="ui_retry_atx_kill")`.
- Every state handler dispatches through `_run_states` → `_execute_with_ui_retry`
  (state_machine.py:963) → ONE edit covers the whole state machine. No
  per-handler patches.
- PROJECT_RULES.md updated to make B1 "LIÊN TỤC mỗi lần" explicit (commit
  `735a2f4`). 96 tests pass; `test_acquire_lock_reconciles_stale_proxy_marker_with_live_vpn`
  fails pre-existing (VPN/lock, unrelated).

## Machines stuck on non_xml_ui_dump / uiautomator_null_root_node — manual ATX + fresh turn

2026-08-15:
- **Machine 32** (chronic `non_xml_ui_dump`, B1/B2/B3 all failed in-batch)
  recovered after a MANUAL `pkill -9 -f atx-agent` + `am force-stop
  com.github.uiautomator` + `uiautomator quit` — dump immediately returned
  `UI hierarchy dumped` — then a fresh `-AvatarOnly` run → THÀNH CÔNG.
- **Machine 27** (uiautomator died permanently after repeated kills; even
  `pkill -9` left `could not get idle state`) recovered on a FRESH turn — the
  accessibility service self-recovered after time passed (dump test OK), new run
  passed.

Triage ladder for a persistent startup/uiautomator machine:
1. `adb shell ps -A | grep -E "atx|uiautomator"` + `cat /proc/<pid>/cmdline`
   (check for zombie `server -d --stop` — see android-device-automation ATX bullets).
2. Manual `pkill -9 -f atx-agent; am force-stop com.github.uiautomator; uiautomator quit`.
3. Verify `uiautomator dump` E=0 BEFORE launching.
4. Re-run the machine alone (MaxParallel 1).

When the user asks "reboot thử lại vẫn k đc à": the first attempt exhausted the
in-turn budget (1 reboot), but a NEW turn resets the budget, and the device may
have self-recovered in the meantime — verify the dump first, then re-run. Do NOT
loop code changes for machine-level uiautomator limits.

## Recent-apps escape (COMPAT-RECENTS-ESCAPE-001, commit e329cc7)

Machines stuck on the Samsung RecentsActivity after a B3 reboot fail
`AVATAR_UPLOAD_MENU_MISSING` because the app never reaches the profile.

- After a soft reboot, some machines land on the Recent-apps switcher
  (RecentsActivity) instead of the launcher; `close_all_recent_apps` needs a
  uiautomator dump to find the clear-all button, but uiautomator is dead
  (`non_xml_ui_dump`) → fail → app never launches → avatar flow sees no
  "Tải ảnh lên".
- Manual fix proven on machine 69: tap HOME (`input keyevent 3`) to exit Recent,
  then launch TikTok from the feed — no dump needed.
- Fix in `_handle_open_tiktok`: at the top of each relaunch attempt, probe
  `_read_focused_activity(adapter)`; if focused activity contains
  "recents"/"recent", log `Đang kẹt Recent; bấm HOME để thoát` and send
  `keyevent 3` + sleep 1 before `prepare_app_for_automation`.
- Machines 69 AND 71 both passed immediately after this landed (they had failed
  2× before). Detection via `dumpsys activity activities` (read-only) — do NOT
  attempt a uiautomator dump to detect Recent.

## Manifest-machine mismatch → preflight INVENTORY_ERROR

`Machine inventory preflight failed: INVENTORY_ERROR: assignment preflight
failed` (launcher ~line 184) = the manifest's `resources` do not match
`-ForceAvatarMachineList` (or `-WorkerId != owner_id`). Each retry of a subset
needs its OWN manifest matching exactly the `-ForceAvatarMachineList`. This bit
machine 27's 3rd retry (reused the 2-machine manifest). Also: `-WorkerId` MUST
equal the manifest's `owner_id` (AssignmentManifest.assert_owner), otherwise
AssignmentError with no detail. `worker-id=owner_id` is the fix.

## ATX restart-after-kill is REQUIRED after every B1 (commit b9351b7)

`_recover_uiautomator` (automation-core) pkill -9's atx-agent but never
restarts it → after the first B1 ATX-kill the atx-agent is dead, and
`capture_persistent_ui` fails HTTPERROR → falls back to shell uiautomator dump,
which dies on weak machines (Killed/137) → `PROFILE_ROOT_NOT_CONFIRMED` /
`non_xml_ui_dump`. Fix: state_machine `_restart_atx_agent(adb)` —
`/data/local/tmp/atx-agent server -d` then verify
`capture_persistent_ui(...).xml` contains `<hierarchy` — called right after
each of the 4 `_recover_uiautomator` sites (ui_retry, ui_failure_ladder,
connect_device, wait_feed). Saved machines 26 + 29. adapter `_dump_ui_real`
also prefers `capture_persistent_ui` (ATX JSON-RPC XML) before
`capture_ui_xml` (commit `850e883`).

## Popup "Tài khoản của bạn cần được cập nhật" → automation-core level (commit 6c6b6e8)

Machine 23's account switch kept failing `PROFILE_ROOT_NOT_CONFIRMED`: after
`select_exact_account`, TikTok shows a security popup "Tài khoản của bạn cần
được cập nhật — liên kết số điện thoại hoặc email trước khi chuyển đổi tài
khoản" with a "Để sau" (Later) button. User directive (2026-08-15): popups like
this must be recorded at AUTOMATION-CORE level, not just the workflow repo.

- Added `PopupRule("account_update_required_vi", ("tài khoản của bạn cần được
  cập nhật", "liên kết số điện thoại hoặc"), PopupAction.TAP, _text("Để sau"))`
  to `TIKTOK_POPUP_RULES` in `src/automation_core/tiktok_popup.py` + test
  (18 passed). Commit `6c6b6e8`.
- Note: `automation_core/tiktok/benign_popup.py` ALREADY has
  `detect_account_update_prompt` (title+body+Để sau) reachable via
  `detect_allowed_generic_popup` → `_dismiss_core_benign_popup`, so the popup is
  covered anywhere the workflow dismisses benign popups — the new rule covers
  the account-switcher path explicitly.
- Workflow: after `select_exact_account`, call
  `dismiss_shared_tiktok_popup(adb, package="com.ss.android.ugc.trill")`
  (commit `06aad66`). Check BOTH mechanisms exist in the VENV, not just the
  repo source.

## automation-core editable install bumps version → runner preflight mismatch

`pip install -e ".[test]"` from automation-core repo changes the installed
version (0.4.40 → 0.4.44). The runner pins
`$defaultAutomationCoreVersion` in run_tiktok_upload_batch.ps1 and aborts on
mismatch. Bump it alongside the editable install. Verify with
`python -c "from automation_core.tiktok_popup import TIKTOK_POPUP_RULES; print(len(...))"`
— the venv must actually see the new rules.

## Nick matching — Tik1 vs Tik2 per-machine counting (user correction 2026-08-15)

"Mày biết phân biệt tik 1 và tik2 k?" — do NOT count a run as "đã đăng video"
just because report status == SUCCESS. Each machine runs 2 nicknames on the
same device; match `report.account` against the workbook ID of the nick under
test. Script pattern (see check-tik2-video-done-20260815.py):
```
dev2m = {device: machine}                    # from workbook rows
tik2_id = {machine: ID}                      # from Tik2.xlsx, skip None/http
for run in runs:                             # every run_*/report.json
    if status == SUCCESS and str(account).strip() == tik2_id.get(machine):
        record video_number
```
Result 2026-08-15: 59/69 Tik2 machines had posted as Tik2; 10 had NOT
(5, 9, 10, 13, 23, 29, 35, 54, 67, 69) even though they had Tik1 SUCCESS runs.
Avatar scope likewise comes from Tik2.xlsx rows (minus excluded machines), not
prior batch manifests.

## 2026-08-16: THE REAL SOURCE IS taikhoan_run_safe.xlsx — TikN = row N (user correction, read first)

User bác mạnh: "Đéo phải chỉ 2 nick đâu, trong file taikhoanrunsafe cả đống
nick đó, chả qua t ms làm tới nick 2" rồi "tik 1 thì là nick row 1 mỗi máy
tik2 là nick row 2 mỗi máy", và "Mở file tik2 lên đọc là biết mà".

- **`taikhoan_run_safe.xlsx` (cột `Máy`, `Device ID`, `ID`) = kho nick THẬT**:
  mỗi máy 2-5 nick (máy 29: 4 nick, máy 35: 5 nick). Tik1.xlsx / Tik2.xlsx /
  tik3.xlsx là các **view theo row**: Tik1 = nick row 1 mỗi máy, Tik2 = nick
  row 2 mỗi máy, tik3 = nick row 3... (Tik2.xlsx máy 1 = `duongkien1202` =
  row 2 của máy 1 trong taikhoan_run_safe — verify khớp).
- **Khi user hỏi "máy nào chưa đăng video Tik2" — ĐỪNG đếm report.json.**
  Mở thẳng `Tik2.xlsx` đọc cột `Video Đã Đăng` (cột 8): trống/0 = chưa đăng
  nick đó; `MISSING_ID` (cột Kiểm Tra Dữ Liệu) = workbook thiếu ID → không
  chạy được, báo user điền. SESSION 2026-08-16 kết quả từ chính workbook:
  máy 13, 23, 29, 35, 69 trống (chưa đăng) → chạy 5 máy này, tất cả
  `THÀNH CÔNG` (mỗi máy video #1, report SUCCESS + video_number=1). Trước đó
  đếm nhầm 2 lần từ report (10 máy, rồi 11 máy) vì run SUCCESS của nick row
  1 (Tik1) cùng device bị tính nhầm.
- Máy 38 (`benghxmk3zu` row 2) cũng trống nhưng CẤM đụng tuyệt đối — chừa
  khỏi mọi manifest.

## Device lock re-enabled for batch runs (2026-08-16, commit 3921421)

15/08 user removed auto device-lock; 16/08 user said "Lock lại khi chạy".
Runner fix in `run_tiktok_upload_batch.ps1`: `if ($LockRoot) { $inventoryArguments
+= "--lock-root", $LockRoot }` — pass `-LockRoot` param or set
`CODEX_DEVICE_LOCK_DIR` (default `C:\Users\Kibe\.codex\device-locks` exists).
Video batch ran 5 machines (13, 23, 29, 35, 69) with lock + manifest
(`-WorkerId` must equal manifest `owner_id`), all 5 THÀNH CÔNG.

## Workbook scope for `-Tik 2` — every machine 1-80 is in scope

Tik2.xlsx rows span machines 1-80; machines 1-37 have a Tik2 account too
(machine 39 = `tachau1704` folder 306, alongside its Tik1 `thanh.huyn4934`
folder 305). When the user says "batch avatar chạy cho tik2 hết", enumerate scope
from `Tik2.xlsx` (all rows minus explicitly-excluded machines), NOT from prior
batch manifests. Verify per-nick with a profile screenshot when the user
questions which account an avatar landed on.

## Final tally (2026-08-15)

- 55-machine `-AvatarOnly` sweep: 46/55 verified; 9 failed non-avatar
  (startup/app/login/UI-variant — see SKILL.md BATCH TALLY bullet).
- 9-machine recovery batch (ladder fix): 5/9 recovered (72, 40, 36, 58, 46).
- Remaining 4 (27, 32, 69, 71): 32 fixed by manual ATX; 69/71 fixed by
  Recents-escape; 27 fixed by fresh turn. **All 56 machines (excl. 38) up
  avatar verified.**
- Commits: `c623a57` (VPN gate, earlier), `e329cc7` (avatar+recents+ladder),
  `6870d45` (B1 per-retry), `735a2f4` (rule doc), `3db4d36` (workbook rule doc).
