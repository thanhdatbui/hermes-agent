# UIAutomator Popup Detection & False Positive Prevention Rules

Use this reference whenever inspecting, developing, or modifying UIAutomator XML detection, popup registry handlers, or navigation/profile verification in Taadaa repositories (`tiktok-luot nuoi acc`, `automation-core`, `Tiktok_Reg`, `tiktok-follow`).

## Incident Case Study: Camera Overlay False-Positive (28/08/2026)

### Failure Trace & Mechanism
During batch feed sessions, the runner executes 8–11 swipes on TikTok and transitions to the **Profile** tab (`Hồ sơ`) to verify the expected account username.
Before reading the username node, the runner probes registered popup detectors in `benign_popup_registry.py`.
The handler `_detect_camera_creation` used raw substring matching:
```python
# FLAWED DETECTOR (DO NOT REPEAT)
markers = ["10 phút", "60s", "15s", "ẢNH", "VĂN BẢN", "10m", "Photo", "Templates", "CAMERA"]
combined = ((xml_content or "") + " " + (ocr_text or "")).casefold()
match_count = sum(1 for marker in markers if marker.casefold() in combined)
return match_count >= 2
```
**The Farm-Wide Blast Radius:**
- A standard, healthy TikTok Profile tab always contains:
  1. `content-desc="Ảnh hồ sơ"` (matches `"ảnh"` / `"photo"`)
  2. `content-desc="Camera"` (story creation / avatar button)
- `match_count` evaluated to `>= 2` on 100% of normal Profile tabs across all devices.
- The handler misclassified the healthy Profile screen as a stuck Camera Creation overlay and issued a `KEYCODE_BACK` (`input keyevent 4`) to "dismiss camera".
- `KEYCODE_BACK` caused TikTok to navigate away from Profile back to the FYP feed.
- On FYP, the profile username was absent (`detected: null`).
- The safety gate classified `detected: null` as `profile verification mismatch: profile account mismatch`, activating `preserve_blocker_screen` and locking 28 machines simultaneously (`status: blocked`).

---

## 5 Non-Negotiable Rules for UIAutomator & Popup Handlers

### Rule 1: Negative Exclusions are Mandatory
Every popup or overlay detector that triggers destructive or navigation actions (like pressing BACK or tapping dismiss) **MUST** check negative exclusions first:
```python
# 1. Profile screen negative markers
profile_negative_markers = (
    "đã follow", "following", "follower", "followers", "sửa hồ sơ", "edit profile",
    "số lượt xem hồ sơ", "lượt xem hồ sơ", "profile views", "menu hồ sơ", "chia sẻ hồ sơ",
    "hoàn tất hồ sơ", "thêm tiểu sử", "bạn có tin vui?"
)
if any(neg in combined for neg in profile_negative_markers):
    return False

# 2. Main navigation bar (FYP / Inbox / Profile)
has_home = "trang chủ" in combined or "home" in combined
has_inbox = "hộp thư" in combined or "inbox" in combined
has_profile = "hồ sơ" in combined or "profile" in combined
if has_home and (has_inbox or has_profile):
    return False
```

### Rule 2: Never Match Raw Generic Substrings Across Dump XML
- Never do `marker in combined.casefold()` with generic words like `"ảnh"`, `"photo"`, `"camera"`, `"video"`, `"text"`, `"live"`.
- Compound recording markers must be required together (e.g. at least 2 shoot durations like `15s`, `60s`, `10 phút`, `10m`, `templates`, `văn bản`, or 1 duration + 1 recording control like `lật`, `flip`, `hẹn giờ`, `timer`, `bộ lọc`, `filters`, `thêm âm thanh`).

### Rule 3: Safe Dismissal Protocol
- Prefer targeted element taps (close button / cancel button bounds) over blind `KEYCODE_BACK`.
- If `KEYCODE_BACK` is sent, verify that the active screen after back does not lose destination context.

### Rule 4: Zero False-Positive Validation Against Fleet XML Dumps
- Every popup detector change must be regression-tested against real `ui.xml` dumps saved under `D:\Taadaa\runtime\kibe\live\...` across all standard screens (FYP, Profile, Search, Inbox, Follow).

### Rule 5: UI Navigation Failures != Account Mismatch
- `detected: null` resulting from a missed tap or immersion mode is a UI navigation issue, not proof that the account password or login is invalid.
- Only classify as `account mismatch` when the Profile page is conclusively loaded (`xml_available == True`) and a different username is explicitly parsed.
