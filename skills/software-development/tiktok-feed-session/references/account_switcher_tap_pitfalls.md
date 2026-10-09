# Account Switcher Tap & Profile Re-navigation Pitfalls (Samsung / Android Farm)

## 1. Samsung Account Switcher Row Tap Pitfall (`_find_account_switch_option`)

### Triệu chứng:
Khi switch account trong bottom sheet switcher, script tìm thấy account nhưng tap không có tác dụng (không chuyển acc, modal vẫn mở hoặc timeout).

### Nguyên nhân:
- Row account trong switcher trên TikTok thường là một `android.widget.Button` (id/l9b) có `clickable="true"`, trải rộng toàn bộ chiều ngang màn hình (`bounds=[0, y1, 1080, y2]`, center x=540).
- Bên trong Button có `TextView` username/display name (`id/mtx`) với `clickable="false"` (`bounds=[216, y1, 578, y2]`, center x=397).
- Nếu script override `best_bounds` bằng bounds của inner TextView, lệnh `adb shell input tap 397 y` tap trúng TextView `clickable="false"`. Trên các thiết bị Samsung, sự kiện touch tại inner non-clickable view này bị nuốt hoặc bỏ qua, không kích hoạt click handler của outer Button `id/l9b`.

### Quy tắc xử lý:
- Trong `_find_account_switch_option`: Nếu `node.attributes.get("clickable", "false").casefold() == "true"` (outer node bản thân nó đã clickable), **CẤM** override `best_bounds` bằng inner non-clickable TextView.
- Giữ nguyên `best_bounds = node.bounds` để tap trực tiếp vào tâm của row button (x=540).

```python
is_clickable = str(node.attributes.get("clickable", "false")).casefold() == "true"
if not is_clickable and node.bounds is not None and (node.bounds[2] - node.bounds[0]) >= 600:
    # Chỉ override khi bản thân container không clickable
    ...
```

---

## 2. Profile Re-navigation Drift Pitfall (`verify_and_switch_profile`)

### Triệu chứng:
Sau khi tap chọn account thành công trong switcher, TikTok tự động đóng sheet và đứng ngay tại màn hình Profile của tài khoản mới. Tuy nhiên, script tiếp tục gọi `_navigate_profile_for_preflight`, tap lại vào tab Hồ sơ `[972, 1857]`, khiến Profile bị refresh, cuộn lên đầu, hoặc drift sang trạng thái không mong muốn.

### Quy tắc xử lý:
1. **Settle time:** Nâng thời gian chờ sau tap chọn account lên `random.uniform(4.0, 6.0)` giây để account load hoàn tất.
2. **Kiểm tra UI trước khi tap navigation:**
   - Trước khi gọi `_navigate_profile_for_preflight`, kiểm tra xem UI hiện tại đã ở Profile chưa (sử dụng `_profile_screen_confirmed_from_xml` hoặc `_is_profile_root_screen`).
   - Nếu app đã đứng ở Profile, **bỏ qua việc tap tab Hồ sơ `[972, 1857]`** và chuyển thẳng sang bước xác minh identity (`_read_profile_identity_with_add_phone_guard`).
   - Chỉ thực hiện navigation nếu UI bị drift ra khỏi Profile (về Home/Feed/Inbox).
