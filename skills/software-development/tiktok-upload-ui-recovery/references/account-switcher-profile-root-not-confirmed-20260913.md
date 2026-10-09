# ACCOUNT_SWITCHER_FAILED / PROFILE_ROOT_NOT_CONFIRMED — Root Cause & Fix (2026-09-13)

## Triệu chứng
- **28/78 máy** Ca 3 Row 5 (Tik5.xlsx) fail upload với `exit_code: 2`
- `reason: [ACCOUNT_SWITCHER_FAILED] open_profile_root failed: PROFILE_ROOT_NOT_CONFIRMED`
- Log: `[TAP_PROFILE] Tap profile tab by text 'Hồ sơ': (595, 322)` hoặc `(573, 1587)` — tọa độ sai, không phải bottom-nav.
- Máy thành công tap đúng `(972, 1883)` = center của node `[864,1864][1080,1903]` (bottom-nav tab Hồ sơ).

## Root Cause
**Commit `a51a1c6` (12/09) thêm logic:** Khi phát hiện feed video overlay, tap `Hộp thư (756, 1857)` trước → mở màn hình Inbox.

Sau khi vào Inbox, `tap_profile()` gọi `_find_ui_element(xml_text, text_contains='Hồ sơ')`:
- `_find_ui_element` với `text_contains` **không gắn điều kiện `require_clickable` hay `bottom-nav constraint`**.
- Trên màn hình Inbox, TikTok render nhiều node có text chứa `Hồ sơ`:
  - Notification text: "... đã xem hồ sơ của bạn" → `(573, 1587)` (giữa màn hình)
  - Popup title: "Cập nhật hồ sơ" → `(595, 322)` (góc trên)
  - Tab bottom-nav thật: `[864,1864][1080,1903]` → center `(972, 1883)`
- `_find_ui_element` trả về node **đầu tiên tìm thấy** (DFS), không phải bottom-nav → tap sai.

**Secondary:** Resource-id thật của profile tab trên TikTok 33.x+ là `com.ss.android.ugc.trill:id/oly` (không phải `profile_tab`) → nhánh resource-id trượt → rớt xuống nhánh text.

## Chuỗi lỗi đầy đủ (machine 10 - serial `988627464e374e3234`)
```
18:19:49 [TAP_PROFILE] Phát hiện Feed video overlay; tap Hộp thư (756, 1857)
18:19:55 [TAP_PROFILE] Tap profile tab by text 'Hồ sơ': (573, 1587) ← notification node
18:20:09 [TAP_PROFILE] Tap profile tab by text 'Hồ sơ': (595, 322) ← popup title node  
18:20:44 [ACCOUNT_SWITCHER] Restored TikTok subpage detected; Back recovery 1/12
18:20:50..07 [CORE_POPUP] contact_follow_suggestion ×4
18:21:11 [ACCOUNT_SWITCHER] Back recovery 6/12
18:21:15 [ACCOUNT_SWITCHER] Back recovery 7/12
18:22:06 [ERROR] ACCOUNT_SWITCHER_FAILED: PROFILE_ROOT_NOT_CONFIRMED
18:22:09 → SOFT REBOOT
18:24:35 [ERROR] proxy readiness timed out → MANUAL_REVIEW
```

## Fix yêu cầu trong `tap_profile()`
1. **Ưu tiên resource-id `oly`** cùng với `profile_tab` trong `ui_profile.py` → selector hiện có `com.ss.android.ugc.trill:id/profile_tab`, cần thêm `oly`.
2. **Lọc text match bằng bottom-nav constraint:** node phải có `center_y > screen_height * 0.85` (tức là nằm ở bottom-nav, không phải giữa/trên màn hình).
3. **Hoặc:** Thêm `require_clickable=True` vào nhánh text và lọc thêm `bounds_bottom > 1700` (1080x1920).

### Patch gợi ý cho `adapter.py` `tap_profile()`
```python
# Thay vì:
element = self._find_ui_element(xml_text, text_contains=t)

# Thêm bottom-nav constraint sau khi tìm được element:
if element and element.get("center"):
    cx, cy = element["center"]
    # Lọc: phải là bottom-nav (y > 80% màn hình)
    if cy > 1536:  # 1920 * 0.8
        self.tap(cx, cy)
        return
    # Tiếp tục tìm element khác với y cao hơn
```

Hoặc tốt hơn: thêm resource-id `oly` vào selector:
```python
# ui_profile.py - get_tiktok_selectors()
"profile_tab": Selector(
    text=["Hồ sơ", "Profile"],
    accessibility_id="Hồ sơ",
    resource_id=["com.ss.android.ugc.trill:id/profile_tab", "com.ss.android.ugc.trill:id/oly"],
),
```

## Thống kê thiệt hại Ca 3 Row 5 (13/09/2026)
- **Success:** 23/78 (29.5%) — 1,6,9,11,16,17,18,20,22,24,25,31,37,40,43,45,46,49,54,57,65,67,71
- **ACCOUNT_SWITCHER_FAILED:** 28 máy (35.9%) — nguyên nhân chính
- **ADB timeout dumpsys power:** 10 máy — 2,4,5,12,15,27,32,33,44,60 (lỗi riêng)
- **Offline/khác:** 8 (M8 offline, M58 POST_VERIFY_PROOF_INSUFFICIENT, 6 no file do feed fail)
- **Bỏ qua đúng:** 9 (cooling_period 5 + unverifiable_date 3 + video_not_rendered 1)

## Pattern phân biệt (healthy vs lỗi)
- **Máy OK:** `[TAP_PROFILE] Tap profile tab by text 'Hồ sơ': (972, 1883)` — y ≈ 1883
- **Máy lỗi:** `[TAP_PROFILE] Tap profile tab by text 'Hồ sơ': (573, 1587)` hoặc `(595, 322)` — y thấp hơn nhiều

## Cron/Watchdog ghi nhận
- `shift_upload_history.json`: Row 5 hôm nay 23 success + 40 "launched" (không thành công)
- Phiên 2 20:00 skip đúng 61 máy `already_uploaded_in_shift` — không đăng trùng
- Row 1 (55 success) và Row 3 (63 success) không bị ảnh hưởng — commit `a51a1c6` chỉ ảnh hưởng khi TikTok mở ở Feed
