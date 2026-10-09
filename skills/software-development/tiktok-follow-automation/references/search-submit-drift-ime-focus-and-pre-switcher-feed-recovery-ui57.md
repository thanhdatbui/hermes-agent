# Case UI-57: Search Submit ID Drift, IME Occlusion (`focused=False`), & Pre-Switcher Feed Recovery

## Background & Incident Context
- **Incident:** Máy 51 (và các máy chạy follow Mode 1) kẹt ở màn hình Search UID mục tiêu (`tranngan8642`) và fail `VERIFY_IDENTITY` khi switch account:
  `🚨 [MÁY 51] DỪNG PHIÊN • Script: tiktok-follow • Tài khoản: ... • Lý do: VERIFY_IDENTITY fail — nick không khớp @... (hoặc switcher fail) / search navigation fail`.
- **Live UI Observation:**
  1. Nút đỏ "Tìm kiếm" trên đỉnh thanh search không có hoặc bị thay đổi resource-id (không còn kết thúc bằng `id/tv_search_textview`).
  2. UID đã được gõ vào ô `EditText`, nhưng bàn phím Samsung (`com.sec.android.inputmethod`) đang mở và chiếm focus. Trong XML dump của uiautomator, thuộc tính `focused` của `EditText` trả về `False` (do IME window giữ focus).
  3. Khi runner bắt đầu phiên mới (`run_session`), app TikTok vẫn còn giữ nguyên hiện trường màn hình Search hoặc bàn phím mở, khiến thanh bottom navigation bar bị ẩn/che khuất. Khi gọi `switch_account_and_verify` (hoặc `run_account_ready_only`), `open_account_switcher` không tìm thấy tab "Hồ sơ", dẫn đến fail `VERIFY_IDENTITY`.

## Root Cause Analysis
1. **`_unique_search_submit` ID Hardcoding:**
   Selector kiểm tra cứng `node.get("resource_id", "").rstrip("/").endswith("id/tv_search_textview")`. Khi TikTok render nút submit bằng ID khác hoặc không gắn resource-id này, hàm trả về `None`.
2. **`_nav_search` IME Occlusion `focused=False` Block:**
   Nhánh fallback `KEYCODE_ENTER (66)` yêu cầu cứng:
   ```python
   valid_input = any(
       n.get("class") == "android.widget.EditText"
       and is_tiktok_package(n.get("package"))
       and (n.get("focused") is True or str(n.get("focused", "")).lower() == "true")
       and _normalize_search_value(n.get("text") or "") == _normalize_search_value(uid)
       for n in nodes
   )
   ```
   Khi bàn phím Samsung mở, `focused` trả về `False` -> `valid_input` là `False` -> runner bỏ qua `keyevent(66)`, không đóng bàn phím và không submit tìm kiếm.
3. **Pre-Switcher Screen State Drift:**
   `run_session` giả định app luôn ở Feed sau khi mở (`open_tiktok()`). Nếu app đang mở sẵn ở Search hoặc bàn phím đang bật (bottom nav không xuất hiện), `switch_account_and_verify` sẽ fail `profile_root_not_confirmed`.

## Proven Fix Pattern

### 1. Nới lỏng `_unique_search_submit` trong `mode1_search_follow.py`
Chấp nhận mọi node thuộc TikTok package có class `android.widget.Button` hoặc `android.widget.TextView`, text hoặc content-desc chuẩn hóa là `"tìm kiếm"` hoặc `"search"`, nằm ở đỉnh màn hình (`bounds[1] < 450`), không phụ thuộc cứng vào `id/tv_search_textview`:
```python
labels = {"tìm kiếm", "search"}
matches = [
    node for node in nodes
    if node.get("bounds")
    and node["bounds"][1] < 450
    and node.get("class") in ("android.widget.Button", "android.widget.TextView")
    and is_tiktok_package(node.get("package"))
    and (
        _normalize_search_value(node.get("text") or "") in labels
        or _normalize_search_value(node.get("content_desc") or "") in labels
    )
]
return matches[0] if len(matches) == 1 else None
```

### 2. Cho phép fallback `KEYCODE_ENTER (66)` khi `focused=False` do bàn phím mở
Khi uiautomator dump chứng minh có `EditText` thuộc package TikTok chứa text hoặc content-desc khớp với UID mục tiêu (chuẩn hóa qua `_normalize_search_value` hoặc `_clean_handle_text`), cho phép dispatch `KEYCODE_ENTER (66)` kể cả khi `focused` là `False`:
```python
target_norm = _normalize_search_value(uid)
valid_input = any(
    n.get("class") == "android.widget.EditText"
    and is_tiktok_package(n.get("package"))
    and (
        _normalize_search_value(n.get("text") or "") == target_norm
        or _normalize_search_value(n.get("content_desc") or "") == target_norm
    )
    for n in nodes
)
if valid_input:
    res_key = adapter.keyevent(66)
    ...
```

### 3. Pre-Switcher Feed Recovery trong `follow_engine.py`
Ở đầu `run_session` (và trước `switch_account_and_verify` / `account_ready`), nếu giao diện chưa thấy bottom nav hoặc đang ở màn hình Search / bàn phím mở, chạy `_back_to_feed(self)` hoặc `self.recover_ui()` để thoát Search về Feed sạch:
```python
# Trước khi gọi switch_account_and_verify
from .mode2_follow_followers import _back_to_feed
curr_xml = self.adapter.dump_ui()
nodes = parse_nodes(curr_xml)
has_profile_tab = any(
    (n.get("content_desc") or "").strip() in {"Hồ sơ", "Profile"}
    for n in nodes
)
if not has_profile_tab or _is_search_screen_or_results(curr_xml):
    if not _back_to_feed(self):
        self.recover_ui()
        _back_to_feed(self)
```

## Testing & Verification Guidelines
- **Focused pytest:** Chạy focused test thay vì full test file để tránh timeout:
  `PYTHONPATH="D:/Taadaa/tiktok-follow;D:/Taadaa/automation-core/src" D:/Taadaa/python-envs/automation/Scripts/pytest follow_runner/tests/test_mode1_search_follow.py -k "search_submit or enter_fallback"`
- **Live canary máy 51:**
  `D:/Taadaa/python-envs/automation/Scripts/python.exe -m follow_runner.run_follow --machine 51 --account-row-index 2 --config config/machine51.yaml --force-preempt`
