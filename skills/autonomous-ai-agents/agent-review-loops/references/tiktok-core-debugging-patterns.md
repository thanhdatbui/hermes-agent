# TikTok Account Switcher Core Debugging Patterns

Phát hiện từ session live debug máy 62 (SM-G930F, swipe-only unlock, TikTok `@tongly2009`).

## 1. Subpage Marker False Positive

**Vấn đề:** `_SUBPAGE_MARKERS` trong `account_switcher.py` chứa `"số lượt xem hồ sơ"` — text này xuất hiện BÌNH THƯỜNG trên profile page (counter). `leave_profile_subpage()` detect subpage → press back → đi lạc khỏi profile → flow fail.

**Fix:** Chỉ giữ markers đặc trưng của subpage thực sự:
```python
_SUBPAGE_MARKERS = frozenset(
    {"chưa có người xem", "no profile views", "private account", "tài khoản riêng tư"}
)
```

## 2. Profile Root Marker Incomplete

**Vấn đề:** `open_profile_root` hardcode check `{"sửa hồ sơ", "edit profile"}`. TikTok profile mới/chưa hoàn thiện hiển thị "Thêm tiểu sử", "Hoàn tất hồ sơ của bạn", "Thêm ảnh hồ sơ". Không match → confirm fail.

**Fix:** Dùng `_PROFILE_MARKERS` constant, expand:
```python
_PROFILE_MARKERS = frozenset({
    "hồ sơ", "profile", "sửa hồ sơ", "edit profile",
    "thêm tiểu sử", "hoàn tất hồ sơ", "menu hồ sơ",
    "complete profile", "add bio", "profile menu"
})
```
Và thay hardcode trong `open_profile_root`:
```python
profile_root = profile_root or bool(values.intersection(_PROFILE_MARKERS))
```

## 3. profile_identity() Must Accept xml_text Parameter

**Vấn đề:** Core gọi `identity_getter(xml_text)` với 1 param. Nếu adapter định nghĩa `profile_identity(self)` không param → TypeError → identity=None → không tìm được switcher anchor.

**Fix:**
```python
def profile_identity(self, xml_text: str | None = None) -> dict[str, str]:
    if xml_text is None:
        xml_text = self.dump_ui()
    # Extract username từ text values
```

## 4. prepare_switcher_anchor() Required for Fallback

**Vấn đề:** Core `find_switcher_anchor` khi không tìm thấy semantic node → gọi `adapter.prepare_switcher_anchor()`. Nếu adapter không có method này → `SWITCHER_ANCHOR_AMBIGUOUS`.

**Fix:** Implement trên adapter:
```python
def prepare_switcher_anchor(self) -> bool | None:
    # Tìm "ảnh hồ sơ" trong content-desc → tap
```

## 5. Locked Detection False Positive

**Vấn đề:** Pattern `keyguard.*=true` match `deviceHasKeyguard=true` (capability field). Consumer `_is_locked_in_dumpsys` false positive, flow chặn nhầm.

**Fix:** Chỉ match:
```python
_LOCKED_PATTERNS = (
    re.compile(r"mShowingLockscreen\s*=\s*true", re.IGNORECASE),
    re.compile(r"isStatusBarKeyguard\s*=\s*true", re.IGNORECASE),
)
```

## 6. Soft Reboot Recovery Flow

Sau reboot, màn hình bị khóa → cần wake + swipe unlock TRƯỚC khi launch TikTok:
```text
REBOOT_1/7: adb reboot
REBOOT_2/7: wait-for-device (120s)
REBOOT_3/7: boot_completed poll (60s)
REBOOT_4/7: WAKE (keyevent 224) + swipe unlock (95%→25%, 500ms, 3 retry, verify dumpsys)
REBOOT_5/7: force-stop TikTok
REBOOT_6/7: launch TikTok
REBOOT_7/7: wait_for_feed (30s)
```

## 7. Consumer Swipe Parameters vs Core

- Core: `swipe 85%→35%, 280ms` — có thể không đủ cho một số device
- Consumer retry: `swipe 95%→25%, 500ms` — start từ sát bottom edge, duration dài hơn
- Verify bằng `dumpsys window policy` sau mỗi swipe
