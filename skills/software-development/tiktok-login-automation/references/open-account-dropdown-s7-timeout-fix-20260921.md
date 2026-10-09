# Pitfall: open_account_dropdown timeout trên máy S7 chậm (2026-09-21)

## Triệu chứng
`tiktok_login_v1.py` fail bước 3 với log:
```
→ rv5/sticky chưa thấy, vuốt lên 400px thử lại (1/3)...
→ rv5/sticky chưa thấy, vuốt lên 400px thử lại (2/3)...
[dropdown-fallback] thử mở qua Menu hồ sơ...
✗ Không thấy: ('Cài đặt và quyền riêng tư', ...)
STOPPED: [03_dropdown] Khong mo duoc account dropdown
```

## Root Cause
`_wait_profile_screen_ready()` trong `social_reg_v1.py` default `timeout=12`s quá ngắn.
- Máy S7 (SM-G930F/S) Android 7 load Profile tab mất 24-30s thực tế.
- Hàm timeout → trả `False` → `_try_open_account_dropdown_once()` không chờ đủ → dump XML vẫn đang ở For-You feed.
- Anchor `rv5` (chevron ▼) không có trên feed XML → script loop 3 lần rồi fail.

**Chẩn đoán xác nhận:** dump XML fail tại `D:/Taadaa/runtime/kibe/artifacts/ui_dumps/fail_03_account_dropdown_*.xml` có các marker của Feed chứ không phải Profile:
- `long_press_layout` 
- `binh luan` / `thich video` / `chia se`
- `Hồ Sơ Mai Mai` (profile của người khác, không phải tài khoản của máy)

## Fix đã xác nhận

**File:** `D:/Taadaa/Tiktok_Reg/social_reg_v1.py`

| Chỗ | Old | New |
|-----|-----|-----|
| Signature hàm | `def _wait_profile_screen_ready(device_id, timeout=12):` | `timeout=25` |
| Fallback call #1 | `_wait_profile_screen_ready(device_id, timeout=6)` | `timeout=20` |
| Fallback call #2 | `_wait_profile_screen_ready(device_id, timeout=6)` | `timeout=20` |

**Verify nhanh (<5s):**
```python
txt = open('D:/Taadaa/Tiktok_Reg/social_reg_v1.py', encoding='utf-8').read()
assert 'timeout=25' in txt and 'timeout=12' not in txt, 'FAIL: timeout=25 missing'
assert txt.count('timeout=20') == 2 and txt.count('timeout=6') == 0, 'FAIL: fallback timeout wrong'
print('PATCH OK')
```

## Lý do không phải mất nick
Khi Batch Alert báo `account-switcher-missing-expected` cho Máy 1 (beheo5746) và Máy 32 (inhhongtram71) trong ca nuôi acc, kiểm tra Switcher thực tế cho thấy cả 2 nick **KHÔNG HỀ BỊ VĂNG**. Nick thực sự thiếu trên app là slot 3 của mỗi máy (tranngan767, thanhlee327) bị thiếu do logout trước đó. mapping SQLite tiktok_tracker.db cũng bị lệch (inhhongtram71 gán nhầm tik=3 thay vì tik=7 trên máy 32).

## Bài học
Khi nhận `account-switcher-missing-expected` hệ thống: LUÔN inspect Switcher thực tế bằng atx-agent/screencap trước khi kết luận nick bị văng. Chẩn đoán qua ảnh mới là EVIDENCE — log script không phân biệt được "nick không có trong list" vs "script không mở được dropdown".
