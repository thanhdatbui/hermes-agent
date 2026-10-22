# Rolling Rename Watchdog — exit_2 Triage & Root Cause Resolution

**Context:** `tiktok-rolling-rename-watchdog` cron fires alerts of the form:
```
⚠️ [ROLLING RENAME FAILED] May <N>: @<handle> reason=exit_2
```

## Critical Correction: The "SplashActivity Stuck" Fallacy

> **WARNING — PITFALL IDENTIFIED (2026-10-23):**
> Do NOT assume `exit_2` means "app is stuck on SplashActivity" just because `inspect_machine.py <N>` shows `SplashActivity` or `LauncherActivity` post-alert!
> The phone often falls asleep or reverts to splash/launcher *after* the runner has already finished and released the lock. 
> Inspecting phone focus *after* the failure only reveals post-teardown state, NOT the root cause during execution.

## True exit_2 Semantics

In `do_rename_canonical_runner.py` (line 678):
```python
return 0 if result in ("RENAMED", "ALREADY") else 2
```
`exit_2` is a **generic failure code** returned whenever `result == "FAIL"`. It covers state-machine aborts, verification mismatches, and step-count exhaustion.

---

## Mandatory First Step: Inspect the Execution Report JSON

Never guess or assume TRANSIENT without reading the runner's execution report:
```bash
# Path pattern:
D:/Taadaa/reports/m{machine}_{target_user}_rename_confirmed.json
```
Inspect the fields:
- `result`: `"FAIL"`
- `reason`: The exact abort message (e.g., `ket o trang thai PROFILE 5 lan lien tiep` or `da Luu nhung Ho so dang la @None, khong phai @...`)
- `saved_at`: If not null, the name was ALREADY SAVED to TikTok!
- `final_ocr`: What was actually visible on the screen.
- `trace`: Step-by-step state sequence (`FEED` -> `PROFILE` -> `BIO_EDIT` -> `EDIT_PROFILE` -> `NAME_EDIT`...).

---

## Two Proven Structural Failure Modes & Fixes

### Mode 1: Post-Rename OCR Whitespace Splitting (False Negative)
- **Symptom:** `saved_at` has timestamp, TikTok profile shows the new name, but runner fails with:
  `reason: "da Luu nhung Ho so dang la @None, khong phai @<target>"`
- **Root Cause:** WinRT OCR occasionally splits the `@username` text with internal spaces (e.g. `@ngotran g7771` instead of `@ngotrang7771`).
- **Mechanism:** In `nickname_on_profile()`, strict checks like `" " not in text` reject the line, returning `(None, None)`. The runner assumes it's on the wrong profile and marks `verified = False`.
- **Fix:** In `nickname_on_profile()`, when `text.startswith("@")`, do not reject spaces. Instead, use `compact(text)` (which strips all non-alphanumeric chars) to compare against `target_user`:
  ```python
  is_user_line = (
      text.startswith("@")
      and b[1] < 750
      and not any(k in normalized for k in ("tai khoan", "nhac den", "noi ve", "chia se", "follower", "thich"))
  )
  ```
  And in fallback without `@`: require `" " not in t.strip()` so display names aren't mistaken for handles.

---

### Mode 2: Gap Tapping Between Dual Buttons on Profile
- **Symptom:** Runner aborts with:
  `reason: "ket o trang thai PROFILE 5 lan lien tiep"`
- **Root Cause:** When an account already has a Bio ("Xin chao"), TikTok displays TWO side-by-side buttons:
  - Left: `[Sửa hồ sơ]` centered at `(315, 865)`
  - Right: `[Chia sẻ hồ sơ]` centered at `(765, 865)`
- **Mechanism:** If OCR fails to recognize the low-contrast text on `[Sửa hồ sơ]`, code falls back to `XY_EDIT_PROFILE_BUTTON`.
  If configured as `(540, 865)`, it taps directly into the **dead space / gap between the two buttons**! Tapping 5 times does nothing, staying on `PROFILE` until MAX_SAME_STATE aborts.
- **Fix:** Set `XY_EDIT_PROFILE_BUTTON = (315, 865)`:
  - For dual buttons: `(315, 865)` hits `[Sửa hồ sơ]` on the left.
  - For single wide button (`+ Thêm tiểu sử` spanning x=100 to 980): `(315, 865)` still lands squarely inside the wide button.

---

## Triage Checklist for exit_2

1. **Read JSON report:** `D:/Taadaa/reports/m{N}_{username}_rename_confirmed.json`.
2. **Check `saved_at`:**
   - If `saved_at` is present -> Nick already saved. Look for OCR post-verification failure (`final_ocr`, `nickname_on_profile`).
3. **Check `trace` states:**
   - If stuck on `PROFILE` -> Check if account has bio, and whether fallback tap `XY_EDIT_PROFILE_BUTTON` is `(315, 865)` (not `540, 865`).
   - If stuck on `UNKNOWN` / Splash -> Only then consider transient app freeze.
4. **Focused test command:**
   ```bash
   pytest D:/Taadaa/tools/tests/test_do_rename_canonical_runner.py -v
   ```
