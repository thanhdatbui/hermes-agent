# Rename Profile Geometry, Portable Flags & Bio Edit Safety Invariants (2026-10-22)

## 1. Samsung S7 (1080x1920) Profile Button Geometry
- **Layout Stacking Order (top to bottom):**
  1. Header / story prompt: `y ≈ 100 - 250`
  2. Avatar circle: `y ≈ 250 - 520`
  3. Nickname (Tên hiển thị): `y ≈ 539 - 587`
  4. Username (`@username`): `y ≈ 606 - 644`
  5. Follower stats (`Đã follow | Follower | Thích`): `y ≈ 689 - 774`
  6. Button row (`Sửa hồ sơ` at x=315, or `+ Thêm tiểu sử` at x=540): `y ≈ 845 - 885` (Center: `y = 865`).
  7. Video tab bar (Grid, Private, Liked): `y ≈ 950 - 1050`
- **Tapping Pitfall:**
  - Tapping `y ≈ 660` lands in the blank space between username and followers -> no UI response, causes premature `ABORT: ket o trang thai PROFILE 5 lan lien tiep`.
  - Tapping `(72, 148)` (top left toolbar) hits the "Find Friends" icon on center-avatar layouts -> opens `FindFriendsPageActivity` loop.
  - Fallback coordinate must always be `y = 865` (`x = 540` for bio-less accounts or `x = 315` for standard edit profile).

## 2. BIO_EDIT Scope Safety Invariant
- **Strict Adherence to `BIO_REQUESTED`:**
  - When running a Rename-only job (`BIO_REQUESTED == False`), the runner MUST NOT write or overwrite a bio with dummy text (e.g. "Xin chao") just to force the "Sửa hồ sơ" button to appear.
  - Doing so creates unrequested profile mutation side-effects and false-success reports.
  - If `BIO_EDIT` is entered while `BIO_REQUESTED == False`, the runner must immediately escape back to Profile via `keyevent(4, 2)` without injecting text or tapping save.

## 3. Strict Profile Username OCR Validation
- TikTok usernames contain strictly alphanumeric characters, underscores, and dots with NO SPACES.
- Limiting whitespace checks to a prefix slice (e.g. `[:10]`) fails when placeholder suggestion text (such as `@ Tài khoản của tôi nói về...`) has a long first token or weird spacing.
- Strict validation:
  ```python
  text = t.strip()
  is_user_line = (
      text.startswith("@")
      and b[1] < 750
      and " " not in text  # No whitespace in entire token
      and not any(k in norm(text) for k in ("tai khoan", "nhac den", "noi ve", "chia se", "follower", "thich"))
  )
  ```

## 4. Platform-Portable Subprocess Creationflags
- On Windows, `subprocess.CREATE_NO_WINDOW` (value `0x08000000`) prevents disruptive console window flash during automated tasks.
- However, hardcoding `creationflags=subprocess.CREATE_NO_WINDOW` crashes on non-Windows platforms with `AttributeError`.
- Portable pattern:
  ```python
  creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
  subprocess.run(cmd, creationflags=creationflags, ...)
  ```
