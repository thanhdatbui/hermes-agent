# Rename Bio-Unlock Scope Guard & Safe Push Agent Override Invariant (2026-10-22)

## 1. Bio-less Profile "Sửa hồ sơ" Unlock Scope Safety (`needs_bio_unlock`)

### 1.1 Root Cause & The 35-Step Ping-Pong Trap
- On newly registered accounts or clean accounts without a bio, TikTok (Samsung S7 layout) completely hides the "Sửa hồ sơ" (Edit profile) button.
- In its place, TikTok renders only a pill-shaped button: `+ Thêm tiểu sử` at `(540, 865)`.
- When the runner falls back to clicking `(540, 865)`, it navigates to `BIO_EDIT`.
- **The Blind-Back Loop Trap:** If the runner checks `if not BIO_REQUESTED: keyevent(4, 2); continue`, it immediately returns to `PROFILE`. On Profile, there is still no "Sửa hồ sơ" button, so it taps `+ Thêm tiểu sử` again, looping until `MAX_STEPS = 35` and terminating with `exit_2`.
- **The Accidental Overwrite Hazard:** If the runner indiscriminately writes `"Xin chao"` whenever `BIO_EDIT` is reached, any account that ALREADY had a bio (or enters `BIO_EDIT` via a misclick) gets its profile bio silently overwritten with default text, violating account data safety.

### 1.2 Canonical Solution: Strict Contextual Gating (`needs_bio_unlock`)
1. **On `PROFILE`:**
   - Detect both buttons explicitly:
     ```python
     btn_edit = find_box(boxes, r"(sua|chinh sua|edit)\s*(h[o0]|profile)")
     btn_add_bio = find_box(boxes, r"\+\s*th[eé]m|tid\w{0,2}\s*s|th[eé]m\s*ti|tieu\s*su")
     if btn_edit:
         xy = center(btn_edit)
     elif btn_add_bio:
         ctx["needs_bio_unlock"] = True  # Flag that this account requires bio unlock
         xy = center(btn_add_bio)
     else:
         xy = XY_EDIT_PROFILE_BUTTON
     ```
2. **On `BIO_EDIT`:**
   - Gate bio mutations strictly:
     ```python
     elif state == "BIO_EDIT":
         if not bio_saved:
             # Only mutate bio if: (1) explicitly requested via CLI, OR (2) account has no bio and needs unlock
             if not BIO_REQUESTED and not ctx.get("needs_bio_unlock"):
                 print("   Dang o man sua Bio nhung khong co yeu cau -> Back ve Ho so")
                 keyevent(4, 2)
                 continue

             if getattr(args, "clear_bio", False):
                 # Clear bio flow
                 ...
                 bio_saved = True
                 continue

             bio_text = TARGET_BIO or "Xin chao"
             # Save bio via AdbKeyboard Base64
             ...
             bio_saved = True
             continue
         keyevent(4, 2)
         continue
     ```
- **Result:** Accounts with existing bios are never modified unrequested. Newly registered accounts write a single bio once, returning to Profile where TikTok reveals both "Sửa hồ sơ" and "Chia sẻ hồ sơ" buttons, allowing rename to proceed normally.

---

## 2. Refactoring Profile Name Box Lookups (`name_above_user_box`)

### 2.1 The OCR `@` Drop Phenomenon
- On Samsung S7 screens with small fonts or border clipping, WinRT OCR frequently omits the leading `@` symbol (e.g. reading `mthinh2415` instead of `@kimthinh2415`).
- To handle this, `nickname_on_profile()` includes a fallback matching `is_target_user(compact(t))` on non-`@` boxes under `y < 750`.

### 2.2 Extraction of Common Helper
- Duplicating the `above` and `wider_above` logic across the primary `@user` loop and the fallback loop causes code drift and maintenance divergence.
- Extract into a shared helper function:
  ```python
  def name_above_user_box(boxes, user_box):
      above = [(t2, b2) for t2, b2 in boxes
               if b2[3] <= user_box[1] + 5 and user_box[1] - b2[3] < 120 and b2[0] < user_box[2]
               and not re.fullmatch(r"[\d\s.,:/%-]+", t2.strip())
               and not any(k in norm(t2) for k in (
                   "tin vui", "ban dang", "thao luan", "nhan tin",
                   "chuyen", "tra hay", "sua ho so", "them ban be",
                   "follower", "dang follow", "luot thich", "da follow"
               ))]
      if above:
          return max(above, key=lambda it: it[1][3])[0]
      wider_above = [(t2, b2) for t2, b2 in boxes
                     if b2[3] <= user_box[1] and user_box[1] - b2[3] < 200
                     and not re.fullmatch(r"\d+", t2.strip())
                     and not any(k in t2.lower() for k in ['tin vui', 'ban dang', 'thao luan', 'nhan tin', 'chuyen', 'tra hay'])]
      if wider_above:
          return max(wider_above, key=lambda it: it[1][3])[0]
      return None
  ```

---

## 3. Safe Push Agent Guard (`BLOCKED_AGENT_OVERRIDE`)

### 3.1 Mechanical Guard in `safe_push.py`
- `safe_push.py` enforces:
  ```python
  AGENT_SESSION_VARS = ('HERMES_SESSION_KEY', 'HERMES_HOME', '_HERMES_GATEWAY')

  def _check_owner_override_allowed(env=None):
      src = os.environ if env is None else env
      if any(var in src for var in AGENT_SESSION_VARS):
          raise UnsafePushError('BLOCKED_AGENT_OVERRIDE')
  ```
- **Policy Intent:** AI agents are forbidden from executing `--owner-override` to bypass closeout gates.
- When an agent calls `safe_push.py --owner-override`, it fails with exit code 2 and `BLOCKED_AGENT_OVERRIDE`.
- **Operating Procedure:**
  1. The agent must remediate code/tests and pass `closeout_gate.py` legitimately (Score >= 85).
  2. If the Reviewer remains blocked on external hardware canary gates and the operator explicitly orders push via owner override, the agent must inform the operator that `--owner-override` is strictly reserved for human execution from an uninstrumented terminal outside Hermes:
     ```bash
     python D:/Taadaa/tools/safe_push.py --owner-override D:/Taadaa/tools origin main
     ```
