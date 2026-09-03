# Tap jitter anti-detect pattern (TikTok/Gmail consumers)

Nguồn: 2026-08-08 — rà toàn bộ script tìm toạ độ deterministic (dùng chung, trùng pixel giữa
máy/lần chạy) → thêm jitter ngẫu nhiên ±4-6px chống detect automation.

## Pattern chuẩn (đã có sẵn ở Tiktok_Reg/social_reg_v1.py — dùng làm template)

```python
def _jitter(coord, max_offset=6):
    """Random offset ±4..max_offset px — chống detect (toạ độ deterministic dễ bị nhận diện)."""
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

- Offset 4-6px: an toàn với nút ≥ 40px (bounds center từ XML, nút X ~60px); không trượt target.
- MỌI tap phải qua helper tập trung — không bypass bằng `shell(..., "input", "tap", cx, cy)` trực tiếp.
- Jitter = consumer anti-detect policy → nằm consumer, KHÔNG đưa vào core (core app-neutral).

## Rà soát: các chỗ hay bị sót (bypass helper)

- `shell(device_id, "input", "tap", str(cx), str(cy))` trực tiếp — cx,cy = center bounds từ XML
  (clear X, dismiss, Play Store ToS/close...). social_reg_v1.py có 4 chỗ + 1 hardcode (999,1041).
- Hardcode literal: `shell(..., "input", "tap", "999", "1041")`, `tap(device_id, 196, 969)`.
- Helper có delay random NHƯNG không jitter toạ độ: gmail_reg_v10.py `tap()` chỉ jitter timing →
  MỌI tap Gmail trùng pixel. Thêm `_jitter` local vào helper.
- `hide_keyboard` hardcode (540, 200) — vùng trống, jitter ±6 vẫn an toàn.

## Enforce bằng source-scan test (không phụ thuộc runtime)

```python
def test_no_direct_tap_without_jitter_in_sources():
    src_dir = pathlib.Path(social.__file__).parent
    for fname in ("social_reg_v1.py", "tiktok_login_v1.py"):
        text = (src_dir / fname).read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            if '"input", "tap"' in line and "shell(" in line:
                assert "_jitter(" in line, f"{fname}:{lineno} tap thiếu _jitter: {line.strip()}"
```
Test range (KHÔNG dùng `random.seed` global — đổi RNG state ảnh hưởng test sau; assert range
200 lần là đủ):
```python
def test_jitter_offset_within_6px_and_nonzero():
    samples = [social._jitter(540) for _ in range(200)]
    assert all(534 <= s <= 546 for s in samples)
    assert len(set(samples)) > 1
```

## Quy trình vận hành

- Rà bằng grep `"input", "tap"` + `"input", "swipe"` toàn repo (bỏ tests/) — semantic scan, không
  chỉ mẫu `str(cx), str(cy)` (luna audit bắt WARN này).
- File đang DIRTY bởi session khác (vd gmail_reg_v10.py `git status: M`) → tách Phase B chờ user
  xác nhận + backup + evidence; KHÔNG đè (trùng rule không sửa file dirty người khác).
- Kèm plan → luna audit (2 vòng: APPROVE_WITH_FIXES → fix → APPROVED) → worker implement →
  verify: pytest + source-scan + CRLF/sha256 so baseline.
