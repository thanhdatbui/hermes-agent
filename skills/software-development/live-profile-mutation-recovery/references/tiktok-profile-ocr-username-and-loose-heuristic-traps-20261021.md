# TikTok Profile OCR Username, Find-Friends Trap, and Loose Heuristic Pitfalls (2026-10-21)

## Context & Symptoms

During farm-wide automated TikTok profile renaming (`tiktok_rename_rolling_watchdog.py` driving `do_rename_canonical_runner.py`), multiple machines reported false positives, switcher loops, and failed renames across specific layout variants:

1. **M15 & M43 (`exit_2` with `mo Switcher 3 lan, acc active van la @None`):** Runner was already on the correct account profile, but aborted after 3 failed switcher attempts.
2. **M28 (`exit_2` with `mo Switcher 3 lan, acc active van la @tangsa0702`):** Runner navigated to a stranger's profile (`@tangsa0702`) and got stuck.
3. **M52 (`ALREADY` reported with final name `"Ban cé"`):** Account had its rename skipped because runner falsely verified `"Ban cé"` as a valid target name.

---

## Root Cause Analysis

### 1. OCR Missing `@` in Username (`nickname_on_profile`)
- **Bug:** `nickname_on_profile()` strictly required `t.startswith("@")`.
- **Failure:** On low-contrast or stylized profiles, OCR frequently drops the `@` symbol (e.g. OCR returns `mthinh2415` instead of `@kimthinh2415`, or `rtisdi an ar1`).
- **Consequence:** `nickname_on_profile()` returned `(None, None)`. The runner concluded the active user was `None` (not `TARGET_USER`), triggered `canonical_switch_account()`, failed to find the account because it was already logged in and active on screen, and aborted after 3 attempts.
- **Fix:** Relax username detection to match either `@` prefix OR fuzzy/compact target user match:
  ```python
  is_user_line = (t.startswith("@") or is_target_user(t)) and b[1] < 750
  ```

### 2. The "Find Friends" Trap & Dual-Mode Profile Layouts
- **Bug:** When neither "Sửa hồ sơ" nor "+ Thêm tiểu sử" matched textually in OCR, the runner fell back to tapping `XY_EDIT_PENCIL = (72, 148)` unconditionally.
- **Failure:** TikTok Galaxy S7 profiles have two distinct layouts:
  - **Left-avatar legacy layout (M8):** Follower/likes count is at Y < 600. The top-left icon at `(72, 148)` is indeed the edit pencil.
  - **Center-avatar modern layout (M4, M28, M31, M32, M43):** Follower/likes count is at Y > 650. The top-left icon at `(72, 148)` is **"Find Friends" / "Tìm bạn bè / Tìm mọi người"**!
- **Consequence:** Tapping `(72, 148)` opened the "Find Friends" modal. In that modal, TikTok suggested other accounts (e.g. `@tangsa0702`). Subsequent taps clicked on the suggested user, opening a stranger's profile. From a stranger's profile, no account switcher exists, causing a fatal loop.
- **Fix:**
  1. Detect layout via follower Y position:
     ```python
     follower_box = find_box(boxes, r"follower|da follow|thich")
     xy = (315, 865) if (follower_box and follower_box[1] > 600) else XY_EDIT_PENCIL
     ```
  2. Implement an active safety guard against the "Find Friends" modal:
     ```python
     if any(k in norm(" ".join(lines)) for k in ("tim ban be", "tim moi nguoi", "tim ben be", "dong bo hoac tim", "ma qr")):
         keyevent(4, 2)  # Immediately press BACK
         continue
     ```

### 3. The Loose `has_vietnamese` Heuristic Trap in `is_target()`
- **Bug:** `is_target()` contained a fallback heuristic:
  ```python
  has_vietnamese = any(c in name_line for c in "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệ...")
  if has_vietnamese and not re.search(r"\d", name_line):
      return True
  ```
- **Failure:** On profiles showing prompt chips (e.g. "Bạn có tin vui?", "Trà hay cà phê?"), OCR extracted `"Ban cé"`. Because `"Ban cé"` contained `é` and no digits, `is_target()` returned `True`.
- **Consequence:** The runner falsely assumed the account had already been renamed to a proper Vietnamese name and marked it `ALREADY`, silently leaving the username unrenamed.
- **Fix:** Eliminate the loose `has_vietnamese` heuristic completely. A name is only accepted as target if:
  - It matches `NEW_NAME` directly (`nl == NEW_NAME_NORM`).
  - Or `SequenceMatcher(nl, NEW_NAME_NORM) >= 0.75`.
  - Or `is_name_related_to_username(name_line, TARGET_USER)` returns `True`.
