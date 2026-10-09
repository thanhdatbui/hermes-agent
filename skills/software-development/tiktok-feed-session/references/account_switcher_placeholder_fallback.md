# Account Switcher: Placeholder Account Fallback (`user\d+`) & API Quirks

## 1. Bản chất sự cố Placeholder Account
- Khi một tài khoản được đăng ký mới trên TikTok hoặc bị TikTok reset handle tạm thời, handle hiển thị trong Account Switcher có dạng placeholder: `user\d+` (ví dụ: `user1196792370966`).
- Trong workbook và hệ thống phân bổ, nick thường được ghi theo handle mong muốn (ví dụ: `stevemgjqec`).
- Hàm `find_exact_account` trong `automation_core.tiktok.account_switcher` sẽ raise `ACCOUNT_MISSING`, dẫn đến lỗi dừng phiên: `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`.
- **Thực tế kiểm chứng trên Máy 5 Row 2**: Sau khi tap vào placeholder `user1196792370966`, màn Profile thực tế đọc được `username: @stevemgjqec` và `display_name: Linh Chau1`, xác minh tài khoản khớp 100% (`profile_verify_status: matched`).

## 2. API Quirk: `automation_core.tiktok.account_switcher`
- **CẢNH BÁO 1 (Không có list_account_switch_options):** Không tồn tại hàm `list_account_switch_options` trong `automation_core.tiktok.account_switcher`.
  - Nếu code import `from automation_core.tiktok.account_switcher import list_account_switch_options` trong block `try...except Exception: return None`, nó sẽ luôn âm thầm bắt `ImportError` và trả về `None`, khiến fallback không bao giờ kích hoạt.
- **CẢNH BÁO 2 (`attributes` vs `attrib`):**
  - Hàm `_nodes(xml_text)` trả về danh sách `SwitcherNode`.
  - `SwitcherNode` là dataclass có thuộc tính dict là `.attributes`, **KHÔNG PHẢI `.attrib`**.
  - Nếu gọi `n.attrib.get(...)` trên `SwitcherNode`, sẽ văng `AttributeError: 'SwitcherNode' object has no attribute 'attrib'`.
  - Thuộc tính có sẵn: `node.text`, `node.content_desc`, `node.bounds` (tuple `(x1, y1, x2, y2)`), `node.center` (property tuple `(cx, cy)`), `node.attributes` (dict).
- **CẢNH BÁO 3 (`UIElement` signature):**
  - `UIElement(text, content_desc, resource_id, bounds, attrib)`.
  - Không truyền `name` hay `center` vào `UIElement(...)` vì `center` là `@property` tính tự động từ `bounds`.

## 3. Tương thích với `_tap_ui_element` và `is_already_selected`
- Trong `feed_swipe_smoke.py`, switcher option khi được chọn sẽ đi qua:
  1. Kiểm tra `is_already_selected`: `any(account_element.attrib.get(attr, "false").casefold() == "true" for attr in ("selected", "checked"))`.
  2. Tap qua `_tap_ui_element(ctx, account_element, ...)`: Yêu cầu `element.center`, `element.text`, `element.content_desc`, `element.resource_id`, `element.attrib`.
- Do đó, đối tượng trả về từ helper tìm placeholder BẮT BUỘC phải là hoặc kế thừa từ `automation_core.ui.UIElement`, đồng thời mapping `node.attributes` vào `attrib`.

## 4. Pattern chuẩn triển khai trong `feed_swipe_smoke.py`
```python
def _find_user_placeholder_switch_option(xml_text: str):
    import re
    from automation_core.tiktok.account_switcher import _nodes
    try:
        nodes = _nodes(xml_text)
    except Exception:
        return None
    for n in nodes:
        text = (getattr(n, "text", "") or getattr(n, "content_desc", "") or (n.attrib.get("text") if hasattr(n, "attrib") else "") or "").strip()
        if re.match(r"^user\d+$", text, re.IGNORECASE):
            bounds = getattr(n, "bounds", None)
            center = getattr(n, "center", None)
            if bounds is None and hasattr(n, "attrib"):
                b_str = n.attrib.get("bounds", "")
                m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b_str)
                if m:
                    x1, y1, x2, y2 = map(int, m.groups())
                    bounds = (x1, y1, x2, y2)
                    center = ((x1 + x2) // 2, (y1 + y2) // 2)
            attrib = dict(getattr(n, "attributes", None) or getattr(n, "attrib", {}))
            if bounds and center:
                return UIElement(
                    text=getattr(n, "text", text),
                    content_desc=getattr(n, "content_desc", ""),
                    resource_id=getattr(n, "resource_id", ""),
                    bounds=bounds,
                    attrib=attrib,
                )
    return None
```
- Khi `_find_account_switch_option(popup_xml, expected)` trả về `None`, gọi fallback:
```python
if account_element is None or account_element.center is None:
    placeholder_opt = _find_user_placeholder_switch_option(popup_xml)
    if placeholder_opt and placeholder_opt.center:
        account_element = placeholder_opt
        ctx.logger.log(
            device_id=ctx.device_id,
            account=ctx.account,
            step=f"{SESSION_ARTIFACT_PREFIX}/profile_preflight",
            action="try_user_placeholder_account",
            result="selected",
            extra={"placeholder_label": getattr(placeholder_opt, "text", "") or getattr(placeholder_opt, "name", ""), "expected": expected},
        )
```

## 5. Lưu ý liên quan khi Canary & Recovery
- **Lỗi cú pháp biến trong PowerShell (`run-feed-session.ps1`)**:
  - Khi string interpolation có biến đứng ngay trước dấu hai chấm, PowerShell sẽ hiểu là variable drive: `"$m:"` -> ParserError.
  - Bắt buộc dùng dấu ngoặc nhọn: `"${m}:"`.
- **Dọn Stale Locks trước khi chạy test**:
  - Phải xóa cả file theo tên máy và theo serial thiết bị:
    - `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json`
    - `C:\Users\Kibe\.codex\device-locks\serial_<SERIAL>.lock.json`
