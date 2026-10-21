# TikTok Profile Rename: 7-Day Cooldown, Bio-less "Sửa hồ sơ" Unlock, and Username False-Match Traps

## 1. Profile Username OCR False-Match Trap (`is_target_user` Collisions)

### Symptom
The runner successfully renames on TikTok (e.g. changes name to `'Thạch Tâm'`), hits Save, confirms the dialog, and navigates back to `PROFILE`. However, it crashes with:
`da Luu nhung Ten tren Ho so (OCR) = None, khong phai 'Thạch Tâm'`
or mistakenly picks a header number (e.g. `'13'`).

### Root Cause
1. In `nickname_on_profile()`, trying to be lenient by matching `is_target_user(t)` on lines without `@` causes `difflib.SequenceMatcher.ratio() >= 0.7` to trigger on the **new display name** itself:
   - `compact("Thach Täm")` vs `compact("thachtam02")` yields a 0.78 ratio!
   - The runner misidentifies the new display name as the username, and then looks *above* it for the nickname. Above it is empty, resulting in `name = None`.
2. Random UI text or numbers (e.g. `'13'` unread messages, or chip text `'Trà hay cà phê?'`) above the username line get selected as the nickname if not filtered out.

### Verified Solution
- On the Profile screen, the username line **must strictly start with `@`**:
  `is_user_line = t.startswith("@") and b[1] < 750`
- Exclude standalone numbers (`re.fullmatch(r"\d+", t.strip())`) and known noise keywords (`tin vui`, `ban dang`, `thao luan`, `nhan tin`, `chuyen`, `tra hay`) from candidate nickname boxes.
- Implement an authoritative post-save verification gate:
  ```python
  if saved:
      found_new_name = any(is_target(t) for t, b in boxes if 200 <= b[1] <= 700)
      if found_new_name:
          return "RENAMED"
  ```
  If the name was saved and appears anywhere in the profile header area (Y: 200–700), accept it immediately as `RENAMED`.

---

## 2. Bio-less Profile "Sửa hồ sơ" Unlock Invariant (Ping-Pong Loop)

### Symptom
Accounts that have never had a bio (M44, M28, M4, M63, M64) fail with `vuot qua 35 buoc` after ping-ponging 35 times between `PROFILE` and `BIO_EDIT`.

### Root Cause
On TikTok Android (particularly Samsung S7 layout):
- If an account has an existing bio, TikTok displays the **`SỬA HỒ SƠ`** button (or two buttons side-by-side: `Sửa hồ sơ` and `Chia sẻ hồ sơ`).
- If an account has **NO BIO**, TikTok suppresses `Sửa hồ sơ` and displays ONLY **`+ Thêm tiểu sử`**.
- When the runner taps `+ Thêm tiểu sử`, it lands on `BIO_EDIT`.
- If the runner sees `BIO_REQUESTED == False` and immediately sends `BACK` (keyevent 4), it returns to `PROFILE`.
- On `PROFILE`, there is still no bio, so `Sửa hồ sơ` remains hidden. The runner taps `+ Thêm tiểu sử` again, looping until hitting `MAX_STEPS`.

### Verified Solution
When in `BIO_EDIT` and the account has not yet been renamed (`not saved`):
Do **not** back out! Automatically save a unique, compliant Vietnamese bio matching the account identity:
```python
if not saved:
    auto_bio = f"Chào bạn, mình là {NEW_NAME}"
    auto_b64 = base64.b64encode(auto_bio.encode("utf-8")).decode("ascii")
    # Clear and type via AdbKeyboard
    ...
    # Tap Luu
```
Once saved, TikTok returns to Profile and **permanently displays the `SỬA HỒ SƠ` button**, allowing the runner on the very next iteration to enter `EDIT_PROFILE` and complete the nickname change.

---

## 3. TikTok 7-Day Display Name Change Cooldown

### Symptom
Runner gets stuck in `NAME_EDIT` for 5 consecutive iterations and aborts with `ket o trang thai NAME_EDIT 5 lan lien tiep`.

### Root Cause
TikTok enforces a strict 7-day cooldown on display name (biệt danh) changes. When locked, TikTok displays:
*"Bạn chỉ có thể thay đổi biệt danh 7 ngày một lần. Bạn có thể tiếp tục thay đổi biệt danh sau ngày DD tháng MM, YYYY."*
The `Lưu` button is disabled or tapping it does nothing.

### Verified Solution
Detect cooldown phrases immediately upon entering `NAME_EDIT`:
```python
if any(k in box for k in ("tiep tuc thay doi", "tiep tvc thay ddi", "sau ngay")):
    tap(XY_NAME_CANCEL, 2)
    raise Abort(f"TikTok gioi han 7 ngay: {box[:60]}")
```
This fails fast with a clear diagnostic (`cooldown_7d`) instead of exhausting retry budgets.
