# Tik2 upload: post-histogram phase + device-lock release behavior

Condensed knowledge bank from the 2026-08-13/14 Tik2 live investigation. Companion to
`references/video-pick-identity.md` (which covers the VIDEO_PICK histogram fix).

## 1. Phase transition: VIDEO_PICK fix -> VERIFY_POST blocker

After the histogram fix (commit `9db5546`, audit APPROVED) the VIDEO_PICK gate passes on
live machines. Proven on machine 37:

```
[VIDEO_PICK] Tile verified by source identity (correlation):
  center=(182, 535) score=0.357 second=None hist=0.759 spatial=0.690
Video pick completed: 3.mp4
```

corr 0.357 >= 0.35 AND hist 0.759 >= 0.75 AND spatial 0.690 >= 0.68 -> both paths verify,
tile tapped. The old `VIDEO_PICK_TARGET_UNVERIFIED` failure class is resolved.

The live bottleneck then shifts to **`POST_SUBMISSION_UNKNOWN`** (exit=2, MANUAL_REVIEW,
0 verified-success). Every machine past VIDEO_PICK then fails at VERIFY_POST with:

```
[VERIFY_POST] Post verification blocked: submission state UNKNOWN
  (no ACCEPTED evidence); manual review required
```

### Where the state logic lives (scripts/tiktok_workflow/state_machine.py)
- `_handle_verify_post` (~11657) calls `_post_submission_state_allows_success` (~11992).
- COMPAT-POST-VERIFY-004: `post_submission_state == "UNKNOWN"` + a post attempt evidenced
  -> fail-closed to MANUAL_REVIEW, NO workbook update, NO success claim.
- `_post_attempt_evidenced` (~12010) checks `post_tap_attempted`, `post_submission_accepted`,
  or the receipt's `post_tapped_at` / `post_retry_tapped_at`.
- `_handle_post` sets `post_submission_state = "UNKNOWN"` (11490) BEFORE the tap, then
  `post_tap_attempted = True`. `_record_post_tap` (11539) writes `post_tapped_at` to the
  receipt. `_wait_for_post_submission` (11601) sleeps 2s then polls 15x for the composer to
  leave. If the ADB tap times out / no ACCEPTED receipt exists, state stays UNKNOWN.
- Repeated runs on the same machine re-read the prior UNKNOWN receipt -> log shows
  "Post tap already recorded for this machine/video; refusing to tap again".

### Why the gate exists (do not hand-wave it away)
COMPAT-POST-VERIFY-004 was introduced in commit `720dcd5` (2026-08-12) after a REAL
false-positive incident (machine 74): the old verifier counted profile tiles in **1 viewport**
(3->4 fake increment), concluded SUCCESS with submission state UNKNOWN, and wrote workbook
count 7 incorrectly (reverted to 6). The gate's job: UNKNOWN submission + a post attempt
evidenced must NEVER advance the workbook. Evidence trail: `git log -S "COMPAT-POST-VERIFY-004"`,
session_search on "đã đăng nhầm false positive VERIFY_POST" (session 20260811_112413).

### Workbook count vs receipt count mismatch (diagnostic shortcut)
`[POST_RECEIPT_CURSOR] Workbook next=1 nhưng receipt đã completed [1, 2]; chuyển sang video #3`
(machine 37 log) means: the receipt ledger shows videos #1 AND #2 were actually **completed**
(posted!) while the workbook "Video Đã Đăng" column still reads 0. The gate blocks the
workbook WRITE, not the actual post. So when the UI shows a post succeeded but the batch
reports 0 verified-success, check:
1. the post-attempt receipt dir for `completed` / `post_tapped_at` entries, then
2. the phone's profile for the new tile.
Do not assume the video was not uploaded — the gate only gates the workbook write.

### Confirmed root cause (2026-08-14) — two stacked causes, NOT proof timing
The next-session hypothesis below ("fix = PROOF timing") was WRONG. The real blockers:

**A. Post-attempt receipt deadlock.** `idempotency/post-attempts/machine_N_video_M.json`
is the PC-side idempotency ledger (distinct from the TikTok in-app draft). A receipt with
`post_tapped_at` but `post_submission_state` != ACCEPTED (from an earlier failed turn) makes
every later run of that machine/video log `Post tap already recorded ... refusing to tap
again` and skip the tap entirely -> VERIFY_POST UNKNOWN -> MANUAL_REVIEW -> exit 2, forever.
Receipt != draft: receipts live on the PC, drafts live inside the TikTok app.
Evidence: `machine_37_video_6/7/8.json` were `completed + ACCEPTED` yet workbook still 0;
profile screenshots showed zero published videos and one leftover draft.

**Cleanup rule:** delete ONLY non-ACCEPTED receipts so machines re-tap for real; keep
ACCEPTED ones (anti duplicate-post). One pass removed 312, kept 360:
```python
import glob, os, json
for f in glob.glob(r'D:\CodexRuntime\tiktok-video\idempotency\post-attempts\machine_*_video_*.json'):
    j = json.load(open(f, encoding='utf-8'))
    if j.get('post_submission_state') != 'ACCEPTED':
        os.remove(f)   # re-tap allowed
```

**B. Hashtag-suggestion panel hides the Post button.** After caption paste the composer
keeps the hashtag-suggestion panel open while the caption field still has focus; the
top-right Đăng button is hidden until focus drops. **`KEYCODE_BACK` is WRONG**: on this
TikTok build Back opens the suggestion screen and the Post button disappears entirely
(same-device before/after screenshots proved: keyboard open + Post visible BEFORE Back;
suggestion panel + no Post AFTER Back). Never dismiss the panel with Back.

**The first preview-tap fix (`_post_composer_preview_point`, COMPAT-CAPTION-008) was
REVERTED (2026-08-14) because it looked at the SAME composer XML instead of the NEW
preview surface — NOT because the tap itself was destructive.** Resolved later the same
day with live-machine proof: tapping the composer's preview thumbnail (upper-right, at
(810,420) on 1080x1920) opens the fullscreen feed-style "Xem trước" surface which HAS a
pink "Đăng" button at the **bottom-right**. The Post button lives there, not top-right.
COMPAT-POST-010 implements this (baseline commit `969a1e6` first, per user rule):
when composer has caption field/panel but no Post button and surface is not the
hashtag-search overlay → `adapter.tap((810,420))` → sleep 2.5s → dump → if "Xem trước"
present → `_tap_post_with_intent(text="Đăng")` then "Post" fallback. Helpers:
`_caption_field_or_hashtag_panel(xml_text)` (markers "Thêm mô tả"/"Mô tả"/"g9u"/"hashtag"/"Nhắc đến")
and `_post_composer_preview_point()` → (810,420). 357 tests pass; live 10-machine canary
relaunch was in flight at session end.

Wait-for-auto-close (COMPAT-CAPTION-009: loop up to 3×2s re-dump until
`_is_hashtag_search_surface` false) is NOT sufficient alone — machines 1 and 5 still hit
`POST_NEXT_SELECTOR_EXHAUSTED` because the panel never auto-closes within ~6s on those
machines.

"Some machines show Đăng, some don't" is NOT IME (XwIME 熊猫 vs SamsungKeypad) and NOT
reup detection (no reup warning in composer) — it's whether the caption field still has
focus with the suggestion panel open. Diagnose with same-device screenshots before/after
Back rather than blaming keyboard type.

### A/B probe result (2026-08-14) — Tik2 is NOT uniformly broken
Same-machine A/B executed: Tik1 on machine 17 → `THÀNH CÔNG (exit=0, verified=True)`; Tik1 on
machine 35 → also SUCCESS. Then Tik2 on machine 17 (same hardware, same IME, same account
machine) → `LỖI (exit=2)`. BUT the older `-Tik 2 -MaxParallel 8` background batch (09:35,
which was believed killed but still ran) reported machines **6 and 11 THÀNH CÔNG verified=True**
out of the same pool. Conclusion: Tik2 is NOT uniformly broken — it's per-machine/per-video.
What differs per machine is the assigned video (workbook row / folder), not the device.

**New failure class `DUPLICATE_MEDIA_BLOCKED`** (machine 17 Tik2 report):
```
reason: [DUPLICATE_MEDIA_BLOCKED] Exact media SHA-256 already verified for machine=17, account=hadang0725
last_state: MANUAL_REVIEW | post_verified: False
```
The media-fingerprint ledger (see `[MEDIA_FINGERPRINT] Reserved SHA-256=...` in logs) blocks
a video whose SHA-256 was already verified/posted on that account. **BUT verified_success
entries can be BOGUS — recorded without a real post.** Proven 2026-08-14 on machine 17:
the ledger had 3 `verified_success` entries for Tik2 folder 130 (video #1/2/3, runs
28/07–02/08) yet the live profile `@hadang0725` showed ZERO videos (screenshot: 0 follow /
0 follower / 0 like, empty grid, only an upload prompt). One run_id (`20260728_023636` etc.)
appeared for BOTH Tik1 folder 129 AND Tik2 folder 130 entries — a single run wrote
fingerprints for both folders, so the entries are mis-recorded, not real posts.

**Ground truth = the live phone profile, NOT the ledger.** Before trusting a
verified_success entry (or before \"anti-reup\" reasoning), verify with a profile screenshot
or the code's own counters (`_count_profile_video_tiles_across_grid`,
`_verify_profile_post_increment`). If the profile is empty, delete the specific fake
entries (filter by `source_path` folder, machine, and status) and re-run — machine 17
re-posted video #1 for real after deleting its 3 fake entries.

**Never compare video numbers across Tik folders** (user hard correction): each Tik has its
own source folder (129 = Tik1, 130 = Tik2 for machine 17); `video #N` is per-folder, so the
fingerprint entry's `source_path` folder is the ONLY reliable Tik discriminator — never
match on video_number alone when cross-referencing ledger vs workbook. Diagnose the
blocked SHA by listing the account's verified entries grouped by source_path folder.

**Old batch kept running after "kill".** The 09:35 `-Tik 2 -MaxParallel 8` launcher reported
results AFTER a later `process kill` — it was still alive in the background and re-ran
machines, causing cross-batch lock contention (máy 17 SKIPPED_LOCKED in it because the new
m17 probe held the lock). Before launching any probe: confirm ALL prior launcher processes
are actually dead (process list / poll each session id), or they will double-run machines.



### AssignmentManifest schema — SOLVED (2026-08-14)
Read from `automation_core.assignments.AssignmentManifest` source (venv-core024). The
dataclass requires: `schema_version`(=1), `assignment_id`, `owner_id`, `resources`
(frozenset of `"machine:N"` strings), **`reviewed_at` (ISO string — required, else
`ASSIGNMENT_REQUIRED_FIELD_MISSING`)**. `load()` validation: schema !=1 → unsupported;
empty resources → `ASSIGNMENT_RESOURCES_EMPTY`. `assert_owner` is a plain
`casefold()` string compare — `-WorkerId` must equal the manifest `owner_id`
(mismatch → `ASSIGNMENT_WRONG_OWNER`). Earlier session conclusion \"registration gate is
opaque\" was WRONG — every AssignmentError traced to a missing `reviewed_at` or an owner
mismatch. Known-good single-machine manifest:
```json
{"schema_version":1,"assignment_id":"tik1-m35-probe-20260814",
 "owner_id":"hermes-kibe-probe-m35","resources":["machine:35"],
 "reviewed_at":"2026-08-14T10:15:00.000000"}
```
launched with `... -AssignmentManifest <path> -WorkerId hermes-kibe-probe-m35`.
Quick sanity-check before launching (no launcher round-trip):
```python
from automation_core.assignments import AssignmentManifest
m = AssignmentManifest.load(path); m.assert_owner(worker_id); m.assert_assigned("machine:35")
```

### Old hypothesis (superseded, keep for context)
The earlier guess — "fix = PROOF timing (`_wait_for_post_submission` 2s + 15 polls;
`_verify_current_post_surface`), NOT tile choice" — was superseded by causes A + B above.
The 2s + 15-poll window and surface verifiers are fine; the machine simply never tapped
Post (A) or could not see it (B).

## 2. Device-lock release-script behavior (why feed locks won't release)

The official releaser is `tiktok-luot nuoi acc/python_runner/scripts/release-device-lock.py`.
Fail-closed refusals:
- `owner_active == True` -> exit 3 "lock is ACTIVE ... refusing to release".
- status not in `_DEVICE_LOCK_STATUSES` (e.g. `queued_v2`) -> exit 4 "lock status unknown: 'queued_v2'".
- `_RETAINED_STATUSES = {blocked, handoff, temporarily_skipped, queued}` -- note `queued_v2`
  is NOT `queued`, so the script refuses it even though it looks "retained".

Feed-session locks (`tiktok-luot nuoi acc`) are `queued_v2` / `running` + `owner_active=True`
-> **cannot be released via the script**. Do NOT force-delete lock files (rm thô is forbidden).
Instead: wait for the feed scheduler to free machines, then re-run the upload batch -- it
auto-selects the free machines (those with NO lock file). If you must release a couple by hand,
only target machines whose lock is `blocked/handoff/temporarily_skipped/queued` with
`owner_active=False` (releaseable via the official script). Locks churn: re-scan repeatedly —
free machines appear over time ("vài máy nhả lock rồi"), and the launcher picks only free ones.

### Diagnostic recipe (git-bash safe -- write to a .ps1, never inline `$_`)
```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'run_tiktok|feed' } |
  ForEach-Object { "PID=$($_.ProcessId) $($_.Name) $($_.CommandLine)" }
```
Lock scan:
```python
import json, glob, os
root = r'C:\Users\Kibe\.codex\device-locks'
for f in sorted(glob.glob(os.path.join(root, 'machine_*.lock.json'))):
    d = json.load(open(f, encoding='utf-8'))
    print(d.get('machine'), d.get('status'), 'oa=', d.get('owner_active'),
          'pid=', d.get('pid'), 'proj=', d.get('project'))
```
Re-scan twice: the feed reservation phase rotates PIDs, so one scan may show a dead PID
(stale-looking) while the live phase already owns a new PID. `owner_active=True` + alive PID
= legit lock, must NOT be force-released. Batch `SKIPPED_LOCKED` en masse = cross-project
feed contention (see SKILL.md) — not stale locks, not the upload code.

## 3. Reading run logs (UTF-16 gotcha)

`runs/run_<serial>_<ts>/execution.log` is **UTF-16-LE** (not UTF-8). `grep`/`tail` show
NUL-garbled text. Decode with python:
```python
raw = open('execution.log', 'rb').read()
text = raw.decode('utf-16-le')          # fallback: raw.decode('utf-8', errors='replace')
```
The launcher `machine-N.out.log` files under `batch-runs/batch_tik2_list_*/` are the same.
Find the first-failure run by `ls -dt runs/run_<serial>* | head`, then grep the decoded text
for `Waiting for upload|Post submission left|ACCEPTED|NOT_ACCEPTED|submission|refusing to tap`.
"Post tap already recorded ... refusing to tap again" = this run re-read a PRIOR UNKNOWN
receipt; the actual tap happened in an EARLIER run of the same serial — inspect that one.

## 4. Transient process deaths vs real machine failures (Tik3)

A Tik3 launcher `exit 127` at the SAME machine (27) twice was NOT a source-187 defect
(66 files present, ffmpeg/ffprobe/python all on PATH) — the 3rd resume passed machine 27
cleanly. Exit 127 in the bash wrapper = the background process died (killed/reset), not
"command not found" for the render pipeline. Before diagnosing a source folder: check the
source folder file count + `command -v ffmpeg ffprobe python`, then resume past the machine.
Never speculate resource contention between Tik3 render (local CPU) and Tik2 upload (ADB) —
user hard correction; they are independent streams.