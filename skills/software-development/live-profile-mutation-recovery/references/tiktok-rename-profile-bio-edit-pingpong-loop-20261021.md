# TikTok Rename Profile-to-BioEdit Ping-Pong Loop Pitfall & Resolution

## Incident Summary (2026-10-21)
The cronjob `tiktok-rolling-rename-watchdog` failed across all 15 eligible targets (May 50, May 28, May 15, May 65, May 76, etc.) with `reason=exit_2`.
Inspection of report traces (`m50_nhathasz4vw_rename_confirmed.json`, `m28_anggiathinh2905_rename_confirmed.json`) revealed that all runners exhausted `MAX_STEPS = 35` and aborted.

## Root Cause
In `do_rename_canonical_runner.py`:
1. Under `if state == "PROFILE":` (line 434), the runner searched for the edit button using:
   ```python
   btn = find_box(boxes, r"(sua|chinh sua|edit)\s*(h[o0]|profile)") or find_box(boxes, r"\+\s*th[eé]m|tid\w{0,2}\s*s|th[eé]m\s*ti|tieu\s*su")
   ```
2. On accounts without a bio, TikTok on Samsung S7 displays a chip `+ Thêm tiểu sử` (`tidU sd`) instead of a text button `Sửa hồ sơ`. The regex matched this chip and tapped it.
3. Tapping `+ Thêm tiểu sử` navigated TikTok to `BIO_EDIT` (Edit Bio screen).
4. However, the task dispatched by the watchdog was **Rename Only** (`--name "..."`, no `--bio`), so `BIO_REQUESTED` was `False`.
5. In `state == "BIO_EDIT"` (line 474):
   ```python
   if BIO_REQUESTED and not bio_saved:
       ...
   print("   Back ve Ho so, KHONG sua bio")
   keyevent(4, 2)
   continue
   ```
   The runner recognized that bio modification was not requested, pressed `BACK` (keyevent 4), and returned to `PROFILE`.
6. Back on `PROFILE`, the account still had its old display name. Line 434 again matched `+ Thêm tiểu sử`, tapped it, navigated to `BIO_EDIT`, pressed `BACK`, and repeated this cycle exactly 35 times until `MAX_STEPS` was exceeded, triggering `Abort("vuot qua 35 buoc")` and returning `exit_2`.

## Invariant & Corrective Architecture
1. **Separation of Rename Entrypoint vs Bio Entrypoint:**
   - When renaming (and `BIO_REQUESTED == False`), NEVER match `+ Thêm tiểu sử` / bio chips as the fallback button on `PROFILE`.
   - If `(sua|chinh sua|edit)\s*(h[o0]|profile)` is absent, the runner must fallback directly to `XY_EDIT_PENCIL = (72, 148)` (toolbar pencil icon at top-left x: 50–90, y: 130–170 on Samsung S7 1080x1920) which enters `EDIT_PROFILE` directly.
2. **Preventing Ping-Pong Loops:**
   - Any runner state machine that navigates from State A to State B must never unconditionally press `BACK` from State B to State A without advancing the workflow or marking an abort.
   - If `BIO_EDIT` is accidentally reached during a rename-only task, pressing `BACK` once is acceptable, but the runner must blacklist the button that triggered navigation to `BIO_EDIT` from being tapped again on `PROFILE`.
3. **Focused Verification:**
   - Verify with focused pytest (`pytest tests/test_do_rename_canonical_runner.py -v`) ensuring both rename-only flow and bio-edit flow reach their intended targets without step exhaustion.
