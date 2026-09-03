# Jitter tap toạ độ anti-detect (2026-08-08)

Pattern chuẩn cho tap/swipe toạ độ trên farm Samsung để tránh bị detect automation
(tap trùng pixel liên tục). Rút từ `Tiktok_Reg/social_reg_v1.py` — đã live-proven.

## Hàm chuẩn (social_reg_v1.py:314-332)

```python
def _jitter(coord, max_offset=6):
    """Random offset ±4..max_offset px — chống detect automation."""
    return coord + random.choice((-1, 1)) * random.randint(4, max_offset)

def tap(device_id, x, y, wait=None):
    time.sleep(random.uniform(0.05, 0.2))          # pre-tap hesitation
    shell(device_id, "input", "tap", str(_jitter(x)), str(_jitter(y)))
    time.sleep(wait if wait is not None else random.uniform(1.2, 2.5))

def swipe(device_id, x1, y1, x2, y2, duration="400"):
    shell(device_id, "input", "swipe",
          str(_jitter(x1, 4)), str(_jitter(y1, 4)),
          str(_jitter(x2, 4)), str(_jitter(y2, 4)), str(duration))
```

- Offset ±4-6px: an toàn với mọi target ≥ 40px (nút XML bounds, nút X ~60px) — không trượt khỏi nút.
- MỌI call tap/swipe phải qua helper (hoặc wrap `_jitter` trực tiếp) — **cấm `shell("input","tap",cx,cy)` trực tiếp** (deterministic → detect).

## Rà soát "chỗ dùng chung toạ độ" — phân loại

1. **Helper có jitter** (tap()/swipe()) → OK, không sửa.
2. **Bypass helper**: `shell(device_id, "input", "tap", str(cx), str(cy))` trực tiếp (bounds center từ XML) → deterministic giữa máy cùng layout → **phải wrap `_jitter`**.
3. **Hardcoded literal**: `shell(..., "tap", "999", "1041")` → wrap `_jitter(999), _jitter(1041)`.
4. **Tool calibrate/hiệu chỉnh** (`calibrate.py`): KHÔNG jitter — cần toạ độ CHÍNH XÁC để đo; không production (không import trong runner).

Lệnh rà: `rg -n '"input", "tap"' *.py` — mỗi dòng phải chứa `_jitter(`.

## Test bắt buộc (pattern đã có trong tests/test_login_method_entry.py)

- Range assert KHÔNG dùng `random.seed` global (đổi RNG state ảnh hưởng test sau):
  `samples = [social._jitter(540) for _ in range(200)]; assert all(534 <= s <= 546 ...); assert len(set(samples)) > 1`.
- **Source-scan test** (bắt mọi call-site bypass, không phụ thuộc runtime): đọc file, mọi dòng chứa
  `'"input", "tap"'` + `shell(` phải có `_jitter(`.

## Hiện trạng 2026-08-08

- `Tiktok_Reg/social_reg_v1.py` + `tiktok_login_v1.py`: ĐÃ jitter đủ (helper + 6 chỗ bypass; `_jitter` import từ social_reg_v1).
- `register gmail/gmail_reg_v10.py`: tap() helper CHỈ delay random, KHÔNG jitter toạ độ → toàn bộ tap Gmail deterministic —
  **phase B treo (08-08)**: file dirty bởi session khác, chờ sửa (helper + hide_keyboard (540,200)).
- `Tiktok-video`, `tiktok-luot nuoi acc`, `tiktok-add-bao-mat-f2a`, `Hotmail`: không có `input tap/swipe` trực tiếp — không cần.
