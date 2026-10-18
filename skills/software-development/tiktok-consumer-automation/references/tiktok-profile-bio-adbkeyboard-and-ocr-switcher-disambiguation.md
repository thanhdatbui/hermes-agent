# TikTok Profile Bio Update, AdbKeyboard Broadcast Contract, and OCR Switcher Disambiguation

## 1. AdbKeyboard Broadcast Action Protocol & Pitfall

### The Bug Pattern
When updating text fields (such as Bio or Display Name) via `AdbKeyboard` on Samsung Galaxy S7 devices, subagents frequently attempt to use generic broadcast actions:
```python
# ❌ INCORRECT (Ignored by farm AdbKeyboard receiver):
shell("am", "broadcast", "-a", "ADB_CLEAR_TEXT")
shell("am", "broadcast", "-a", "ADB_INPUT_B64", "--es", "msg", b64_text)
```

### The Impact
- `AdbKeyboard` ignores unrecognized intent actions.
- Any preceding or accompanying `KEYCODE_DEL` (67) keyevents only partially erase multiline text.
- The field is saved with leftover truncated text (e.g., saving only the final word `"ngay"` from `"Góc nhỏ bình yên chia sẻ chuyện mỗi ngày"`), resulting in broken profile bios.

### The Canonical Contract
Farm runners and `social_reg_v1.py` / `do_rename_canonical_runner.py` use the canonical `ADB_KEYBOARD_*` actions:
```python
# ✅ CORRECT AdbKeyboard protocol:
shell("ime", "set", "com.github.uiautomator/.AdbKeyboard")
time.sleep(1.0)

# Clear existing text cleanly:
shell("am", "broadcast", "-a", "ADB_KEYBOARD_CLEAR_TEXT")
time.sleep(0.3)

# Robust fallback clear for stubborn multiline fields:
shell("input", "keyevent", "123")  # KEYCODE_MOVE_END
for _ in range(5):
    shell("input", "keyevent", " ".join(["67"] * 20))
    time.sleep(0.1)
shell("am", "broadcast", "-a", "ADB_KEYBOARD_CLEAR_TEXT")
time.sleep(0.3)

# Commit UTF-8 text via base64:
b64_str = base64.b64encode(text.encode("utf-8")).decode("ascii")
shell("am", "broadcast", "-a", "ADB_KEYBOARD_INPUT_TEXT", "--es", "text", b64_str)
time.sleep(1.5)
```

---

## 2. OCR State Machine: False-Positive Account Switcher Pitfall

### The Substring Trap
In OCR state machines classifying TikTok screens (`classify(lines)`), relaxed substring matching can accidentally trigger `SWITCHER`:
```python
# ❌ TRAP:
if ("tai khoan" in t or "khoan" in t) and ("chuy" in t or "switch" in t or "them" in t):
    return "SWITCHER"
```
On the FYP Feed, a video with the caption:
`"Khoảnh khắc thiên tài Yamal ... thêm"`
normalizes to:
`"khoanh khac thien tai yamal ... them"`
Because `"khoan"` is a substring of `"khoanh"` and `"them"` is present, the feed video is misclassified as the Account Switcher sheet.

### The Consequence
1. The runner attempts to "scroll the sheet" by swiping up at `(540, 1500, 540, 900)`.
2. Swiping up on a feed screen navigates to the next video or gestures out to the Android Launcher.
3. The runner gets stuck in an `UNKNOWN` state on the launcher until `MAX_SAME_STATE` aborts the run.

### The Fix
1. Require exact boundary matching for switcher indicators:
   ```python
   if re.search(r"\b(chuyen doi tai khoan|switch account|them tai khoan|add account)\b", t):
       return "SWITCHER"
   ```
2. Check for navigation bar / Feed indicators (`trang chu`, `cua hang`, `hop thu`, `de xuat`) before or alongside switcher checks.
3. In `UNKNOWN` recovery, detect launcher apps (`photos`, `chrome`, `launcher`) and re-launch the target package (`monkey -p com.ss.android.ugc.trill ...`).

---

## 3. Creator Persona Bio Discipline

### The Problem
Repeatedly applying generic placeholder bios (e.g., `"Góc nhỏ bình yên chia sẻ chuyện mỗi ngày ⛅🌾"`) across multiple accounts triggers user frustration and patterns bot detection.

### The Standard
- Generate natural, lively Vietnamese bios aligned with the account's persona, display name, and content niche:
  - Female personal/vlog/event niche (e.g., `Huỳnh Diễm`):
    `"Hôm nay có gì mới? Để Diễm kể bạn nghe nhé!"`
    `"Cùng Diễm lưu lại những khoảnh khắc đẹp mỗi ngày ✨🌷"`
  - Storytelling / Daily life:
    `"Chuyện đời chưa kể: Hay quên nhưng nhớ dai điều vui 🥑"`
- Avoid repetitive generic fallbacks across different accounts on the farm.
