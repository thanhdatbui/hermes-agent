# Rename Watchdog: ADB Bridge Stale Socket Hang & FindFriendsPageActivity Loop Trap (2026-10-22)

## Incident Background
In the 11:20 run of `tiktok-rolling-rename-watchdog` (job_id: 35e94bb43979), 6 machines failed out of 8 eligible targets:
- M74 (@nguyentrang86016): `exit_1`
- M4 (@votam5319): `exit_1`
- M44 (@oquangduong7604): `exit_1`
- M13 (@trang74683): `exit_2`
- M69 (@tranthibich3499): `exit_2`
- M64 (@lyanh2912): `exit_2` / `exit_1`

When the operator asked `"- là có cứu đc k"`, a rigorous live triage and verification against real devices revealed two distinct layers of root causes and established the honest reporting contract.

---

## 1. ADB Bridge Stale Socket & Unhandled Subprocess Timeout (`exit_1`)

### Symptom
- Watchdog logs `[ROLLING RENAME FAILED] May N: @user reason=exit_1`.
- In `D:\Taadaa\reports\`, **NO** `mN_user_rename_confirmed.json` is generated.
- `python D:/Taadaa/tools/inspect_machine.py N` times out at 30s–60s on each ADB command (`dumpsys battery`, `getprop`, `dumpsys window`).

### Root Cause
1. ADB daemon on the Windows host enters a stale socket state with Samsung S7 physical devices, causing all subsequent `adb shell` calls to hang indefinitely until timeout.
2. In `do_rename_canonical_runner.py`:
   ```python
   def _execute_rename_inner():
       old_ime = shell("settings", "get", "secure", "default_input_method") # OUTSIDE try-except!
       try:
           result = run(ctx)
   ```
   `shell()` calls `subprocess.run(..., timeout=30)`. When the ADB socket hangs, `subprocess.TimeoutExpired` is raised **outside** the `try...except Abort` block. The runner process crashes immediately with exit code 1 (`exit_1`) before creating any JSON report or trace artifacts.

### Remediation & Verification
- Run `adb kill-server && adb start-server` in bash/terminal without device lock (server commands do not target a specific serial).
- Test with `python D:/Taadaa/tools/inspect_machine.py N` — devices respond within 1–2 seconds.
- In the next 15-minute cron cycle (or manual run), the runner successfully connects to the device.
- **Proof:** In the 16:00 cycle, M74 succeeded completely (`RENAMED`, verified `Trang Xù` via `browser_vision`), while M4 and M44 successfully advanced past the initial connection into the app flow.

---

## 2. The `FindFriendsPageActivity` Loop Trap (`exit_2` / 35-step Abort)

### Symptom
- Watchdog logs `reason=exit_2`.
- `mN_user_rename_confirmed.json` reports `reason="vuot qua 35 buoc"`, `final_state="UNKNOWN"`.
- `final_ocr` contains: `"Tim moi nguoi"`, `"Tim ban be"`, `"Tim kiem theo ten hoac ten nguoi..."`, `"Moi ban be"`.
- Device focus dump shows `mCurrentFocus=Window{... u0 com.ss.android.ugc.trill/com.ss.android.ugc.aweme.relation.ffp.ui.FindFriendsPageActivity}`.

### Root Cause
1. On newer TikTok UI or center-avatar / prompt-banner accounts (e.g. accounts with "Bạn có tin vui?" prompts), the text button "Sửa hồ sơ" is either scrolled off or absent.
2. The runner falls back to `XY_EDIT_PENCIL = (72, 148)` at the top-left toolbar.
3. On these layouts, `(72, 148)` is occupied by the **"Find Friends"** icon (person with `+`), NOT the edit pencil!
4. Tapping `(72, 148)` navigates to `FindFriendsPageActivity`.
5. In `FindFriendsPageActivity`, `classify()` cannot match `PROFILE`, `FEED`, or `EDIT_PROFILE`, classifying it as `UNKNOWN`.
6. The fallback branch tries `keyevent(4, 2.5)` (BACK), but because the page may have focus on a search field with the software keyboard open, the first BACK only dismisses the keyboard, leaving the activity active. On the next step, it classifies `UNKNOWN` again, resulting in an endless ping-pong loop until reaching the 35-step ceiling.

### Required Pattern / Fix
- **Explicit Screen Classifier for FindFriends:** Add `FRIENDS_FIND` / `FIND_FRIENDS` to `classify()`:
  ```python
  if any(k in t for k in ("tim moi nguoi", "tim ban be", "tim kiem theo ten", "moi ban be", "find friends")):
      return "FIND_FRIENDS"
  ```
- **Handler in Runner Loop:**
  ```python
  elif state == "FIND_FRIENDS":
      print("   Dang o man Tim ban be -> Force BACK ve Ho so")
      keyevent(4, 1.5)
      keyevent(4, 2.0)
      continue
  ```
- **Pencil Fallback Guard:** Only tap `(72, 148)` when the header indicates a left-avatar layout and follower count Y < 600. If follower Y > 600 or a center avatar is detected, look for center edit button `(315, 865)` or unlock edit mode by updating bio.

---

## 3. TikTok Server-Side 7-Day Cooldown (`COOLDOWN_7D`)

- Accounts like M13 (@trang74683) fail with `reason="TikTok gioi han 7 ngay: ... chi co the thay doi biet danh sau 7 ngay"`.
- This is an immutable server-side enforcement. No script, ADB reset, or UI recovery can bypass it.
- **Contract:** The runner correctly detects the cooldown warning text in `NAME_EDIT`, aborts with `exit_2`, and does NOT write state to `rename_natural_state.json`. The coordinator must inform the operator honestly that the account must wait until the 7-day cooldown expires.

---

## 4. Operator Communication & Realist Triage Contract

When the operator challenges a coordinator claim (`"- là có cứu đc k"`):
1. **Never make blanket promises** ("yes, all will succeed next cycle").
2. **Break down by root cause class:**
   - **Saved / Verified:** Show exact visual proof via `browser_vision` (e.g. M74 `Trang Xù`).
   - **Connectivity Unblocked but Secondary UI Blocker Pending:** Explain that ADB was resolved, but the runner hit the `FindFriendsPageActivity` UI trap (e.g. M4, M44, M69).
   - **Immutable Server Blocker:** Explain that tool recovery is impossible due to TikTok 7-day cooldown (e.g. M13).

---

## 5. Samsung S7 Profile Button Geometry (`y ≈ 865`) & Bio-less `+ Thêm tiểu sử` Unlock Flow

### Symptom
- Runner identifies state as `PROFILE`, tries to tap edit button, but remains in `PROFILE` for 5 consecutive steps, aborting with `ABORT: ket o trang thai PROFILE 5 lan lien tiep`.
- Or runner falls back to `(72, 148)` and enters the `FindFriendsPageActivity` loop.

### Coordinate Geometry on Samsung S7 (1080x1920)
- Display name: `y ≈ 539–587`
- Username `@user`: `y ≈ 606–644`
- Follower stats row (`Đã follow | Follower | Thích`): `y ≈ 689–774` (center: `y=744`)
- **Button row:** Sits strictly **BELOW** follower stats, at `y ≈ 845–882` (center: `y ≈ 865`)!
- **Fatal Trap at `y ≈ 660`:** Tapping `y ≈ 660` taps the empty white space between username and followers row. No action is triggered, causing a 5-step PROFILE stall.

### Bio-less Account Behavior
- When an account has no bio, TikTok suppresses the "Sửa hồ sơ" button entirely. It displays ONLY a single centered pill button `+ Thêm tiểu sử` at `(540, 865)` (`x: 383–685, y: 845–882`).
- **Required Handling:**
  1. Profile button matcher must match both `(sua|chinh sua|edit)\s*(h[o0]|profile)` AND `\+\s*th[eé]m|tid\w{0,2}\s*s|th[eé]m\s*ti|tieu\s*su`.
  2. Fallback coordinate must be `(540, 865)`, never `(72, 148)` or `(315, 660)`.
  3. When entering `BIO_EDIT`, if `not bio_saved`, the runner must write and save a simple bio (`TARGET_BIO or "Xin chao"`) via AdbKeyboard Base64.
  4. Saving the bio transforms the TikTok profile layout to reveal the full "Sửa hồ sơ" button upon returning to `PROFILE`.

---

## 6. Bio Placeholder `@` OCR Misidentification Trap (Case M43)

### Symptom
- Runner enters `PROFILE`, but logs `mo Switcher 3 lan, acc active van la @taikhoancuatoin6ive`, then aborts with `exit_2`.
- Real target account (e.g. `@kimthinh2415`) was already active on screen.

### Root Cause
- Below the profile buttons, TikTok displays placeholder prompt text starting with `@`: e.g. `@ Tài khoản của tôi nói về...`.
- `nickname_on_profile()` checked `t.startswith("@") and b[1] < 750`. Because the prompt was at `y < 750` and started with `@`, `compact(t)` parsed `@taikhoancuatoin6ive` as the account username.
- The runner misidentified the current account as wrong, tried opening Switcher 3 times to find `@kimthinh2415`, and failed.

### Remediation
- Require username candidates to have no spaces in the handle: `" " not in t.strip()[:10]`.
- Exclude common placeholder keywords: `not any(k in norm(t) for k in ("tai khoan", "nhac den", "noi ve", "chia se"))`.

