# Samsung Switcher Dead-Space Bug (CONFIRMED 09/09/2026)

## Tên lỗi
`profile username still mismatched after switch` — Samsung switcher dead-space tap

## Phạm vi ảnh hưởng
- 21/79 máy (26.6%) trong batch Row 3, ngày 09/09/2026
- Máy Samsung (SM-G930F/W8 series) có switcher sheet dạng bottom-sheet với full-width Button rows

## Root Cause
Account Switcher trên TikTok 46.x Samsung hiển thị mỗi tài khoản là một `Button` element:
```xml
<Button resource-id="com.ss.android.ugc.trill:id/lkp" content-desc="phamthy2004"
        bounds="[0,492][1080,708]" clickable="true">
    <TextView text="phamthy2004" bounds="[252,570][596,630]" />
    <View content-desc="9+" bounds="[942,572][1032,628]" />  <!-- badge icon -->
</Button>
```

Hàm `_find_account_switch_option` trong `feed_swipe_smoke.py` (dòng ~15469) ưu tiên giữ nguyên bounds của Button clickable:
```python
if node.attributes.get("clickable", "false").casefold() == "true":
    best_bounds = node.bounds  # → center x=540, y=600
```

Vấn đề: Tâm x=540 nằm trong vùng dead-space giữa TextView (kết thúc x=596) và badge icon (bắt đầu x=942). Trên Samsung, TikTok bỏ qua sự kiện touch tại vị trí này, khiến switcher không chuyển tài khoản.

## Bằng chứng hiện trường
- **Máy M4** (serial: 9885e6484432423046): expected=`phamthy2004`, actual=`thuuy.thy`
- `switch_attempts: 3` — cả 3 lần tap đều không chuyển được
- Switcher sheet mở đúng, `find_exact_account` tìm đúng element, tap "thành công" (adb shell input tap không lỗi), nhưng TikTok không nhận
- Bằng chứng XML: `selected="true"`始终 ở row `thuuy.thy`, `selected="false"`始终 ở row `phamthy2004` sau 3 lần tap

## Fix
Thay đổi logic trong `_find_account_switch_option` — thay vì giữ nguyên bounds Button full-width khi clickable, LUÔN tìm inner TextView bounds trước:
```python
# Luôn ưu tiên inner TextView (narrower, centered on text) hơn full row center
if node.bounds is not None and (node.bounds[2] - node.bounds[0]) >= 600:
    try:
        from automation_core.tiktok.account_switcher import _nodes
        for inner in _nodes(xml_text):
            for val in (inner.text, inner.content_desc):
                if val and not _is_login_or_add_account_option_text(val) and ...:
                    if inner.bounds and inner.center:
                        inner_w = inner.bounds[2] - inner.bounds[0]
                        if 0 < inner_w < 600 and ...:
                            best_bounds = inner.bounds  # → center x≈424
                            break
    except Exception:
        pass
```

Với inner bounds `[252,570][596,630]`, tâm tap chuyển thành x≈424, y=600 — rơi vào vùng chữ "phamthy2004", TikTok nhận tap và chuyển account.

## Cách kiểm tra nhanh khi gặp lỗi tương tự
1. Đọc XML switcher: `<attempt_1/ui.xml>` trong artifact path
2. Tìm `<node resource-id="com.ss.android.ugc.trill:id/lkp" content-desc="<expected_username>">`
3. Kiểm tra bounds của Button vs inner TextView
4. Nếu Button width >= 600px và center x ≈ 540 → dead-space bug
5. Fix: tap inner TextView center hoặc giới hạn x vào `[bounds[0]+250, min(bounds[0]+600, bounds[2])]`

## Commit tham khảo
- `7430415` — fix: raise PROFILE_SWITCH_MAX_ATTEMPTS 2->3 (fix trước đó, chưa triệt để)
- Fix triệt để inner TextView bounds: còn pending dispatch worker #2 (deleg_a88ad3c8)
