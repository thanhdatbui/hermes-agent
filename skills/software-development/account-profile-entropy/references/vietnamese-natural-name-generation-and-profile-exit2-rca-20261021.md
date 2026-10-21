# Vietnamese Natural Name Generation, Syllable Parsing & TikTok Profile exit_2 RCA (2026-10-21)

## Context & Incident Trigger

During rolling TikTok rename operations (`tiktok-rolling-rename-watchdog`), two distinct failure classes surfaced:
1. **The "Tên đần độn" / Juvenile Nickname Antipattern**:
   Account `@huehoafi23` (real identity: Huệ Hoài, mail `huehoa2302fi@gmail.com`) was renamed to **"Hoa Sữa"**. User expressed intense frustration: *"gọi planner vào kiểm tra chứ mày đặt tên trông đần độn quá xem còn hàm nào lỗi k"*. Later batch runs also generated names like **"Huy Sữa"** and **"Mai Chanh"**.
2. **The PROFILE <-> BIO_EDIT Ping-Pong Loop (`exit_2` / 35 steps)**:
   Batch runs on 15 machines repeatedly aborted with `reason=exit_2` after 35 steps without opening `EDIT_PROFILE`.
3. **The 7-Day Cooldown False Alert Trap (`reason=exit_2`)**:
   When TikTok limits an account with *"Bạn chỉ có thể thay đổi biệt danh 7 ngày 1 lần"*, runner raised `Abort()` which exited with code 2, causing watchdog to log a failure alert indistinguishable from a crash.

---

## 1. Root Cause Analysis: Juvenile Nicknames & Syllable Parsing

### A. Dictionary Gap & Greedy Substring Drop
- In `smart_name_generator.py`, dictionaries `HO_MAP`, `DEM_MAP`, `TEN_MAP` lacked common Vietnamese syllables:
  - Female: `hue` (Huệ), `hoai` (Hoài), `khue` (Khuê), `hanh` (Hạnh), `bich` (Bích), `uyen` (Uyên), `thuong` (Thương), `nhien` (Nhiên), `tuyet` (Tuyết), `lien` (Liên), `thoa`, `suong`, `bang`, `que`, `lai`, `vi`, `sa`.
  - Male / Unisex: `hau` (Hậu), `khai`, `khang`, `kha`, `thien`, `tin`, `tan`, `manh`, `luan`, `phu`, `quy`, `dong`, `dai`, `danh`, `hao`, `kiet`, `tuong`, `loi`, `dang`.
  - Surnames: `vuong` (Vương), `tong` (Tống), `dam` (Đàm), `ung` (Ứng).
- **The Substring Drop**: For username `huehoafi23`, the parser did not recognize `hue`. Greedy fallback skipped to `hoa` (from `h-o-a-f-i`), extracting only `['hoa']`.

### B. The `NICK_SFX` Forced Appending Trap
- When only 1 syllable was parsed, `make_smart_name_from_username` had a 60% probability branch forcing a suffix from `NICK_SFX`:
  `["Bông", "Miu", "Bơ", "Gạo", "Nhím", "Heo", "Cún", "Nấm", "Đậu", "Kem", "Sóc", "Còi", "Bé", "Mập", "Tít", "Thỏ", "Xù", "Su", "Dâu", "Mây", "Chanh", "Na", "Bi", "Sữa"]`
- Forcing terms like *Mập, Còi, Heo, Sữa, Chanh, Đậu* on adult Vietnamese users looks fake, juvenile, and bot-like.
- **Quy tắc chuẩn người dùng thật**: Real adult Vietnamese TikTok users use authentic 2-3 word full names (`Hoài Huệ`, `Bảo Tâm`, `Nguyễn Trâm`, `Thạch Khánh Trâm`). Suffixes should be eliminated or restricted to <= 5% for single-syllable handles with only gentle terms (*Bé, Miu, Bông*).

### C. Relation Checker Substring Flaw (`is_name_related_to_username`)
- The checker tested `seg_norm in name_norm`. Because `"hoa"` is inside `"hoa sua"`, the check returned `True` for `Hoa Sữa` vs `huehoafi23`.
- The watchdog considered `Hoa Sữa` as `ALREADY_VALID` (KEEP), preventing any self-correction.
- **Fix**: Relation checking must compare whole word tokens, and multi-syllable usernames must match all or primary syllables in the display name.

---

## 2. Root Cause Analysis: Profile Navigation & Ping-Pong Loop (`exit_2`)

### A. Layout Differences on Samsung S7 TikTok v47
- Regular accounts have a prominent text button: `"Sửa hồ sơ"` (Edit profile).
- New / low-interaction farm accounts often have **NO text button**. Instead, they display:
  - A chip button: `+ Thêm tiểu sử` (`tidU sd` in OCR) below stats.
  - A pencil icon at the top-left: `XY_EDIT_PENCIL = (72, 148)` (near profile title).

### B. The Ping-Pong Loop
1. When renaming (without `--bio`), runner looks for edit button on `PROFILE`.
2. Old regex: `find_box(boxes, r"sua.*profile") or find_box(boxes, r"tieu\s*su")`.
3. Because "Sửa hồ sơ" was absent, it matched `+ Thêm tiểu sử` and tapped it.
4. TikTok opened `BIO_EDIT`.
5. In `BIO_EDIT`, since `BIO_REQUESTED` is `False`, runner pressed `Back` (keyevent 4) to return to `PROFILE`.
6. Back on `PROFILE`, runner saw target name still not applied -> matched `+ Thêm tiểu sử` again -> opened `BIO_EDIT` -> pressed `Back`...
7. Ping-pong repeated exactly 35 times until `MAX_STEPS = 35` was exceeded, aborting with `exit_2`.

### C. The Fix
- In `PROFILE`, the edit button MUST ONLY match edit profile text:
  ```python
  btn = find_box(boxes, r"(sua|chinh sua|edit)\s*(h[o0]|profile)")
  xy = center(btn) if btn else XY_EDIT_PENCIL
  ```
- If text button is missing, fall back directly to `XY_EDIT_PENCIL = (72, 148)` to enter `EDIT_PROFILE`. Never match `tieu su` during a rename-only task.

---

## 3. TikTok 7-Day Cooldown Watchdog Alert Differentiation

- In `do_rename_canonical_runner.py`:
  When TikTok shows `"Bạn chỉ có thể thay đổi biệt danh 7 ngày 1 lần sau ngày..."`, the runner correctly detects `COOLDOWN_7D`, taps Cancel, and raises `Abort()`.
- However, `Abort` triggers `sys.exit(2)` by default.
- Watchdog receives exit code 2 and logs:
  `⚠️ [ROLLING RENAME FAILED] May <M>: @<user> reason=exit_2`
- **Distinction**:
  - `exit_2` with `reason: "vuot qua 35 buoc"` -> Real UI loop bug.
  - `exit_2` with `reason: "TikTok gioi han 7 ngay: ..."` -> Policy cooldown (normal platform behavior, NOT a runner bug).
  - Runner and watchdog should map `COOLDOWN_7D` to a distinct exit code (e.g. exit code 3 or write `KET QUA: COOLDOWN_7D`) so the watchdog reports:
    `ℹ️ [ROLLING RENAME COOLDOWN] Máy <M>: @<user> còn trong hạn 7 ngày (giữ nguyên)`.
