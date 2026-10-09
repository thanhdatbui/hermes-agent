# TikTok Storage & Cache/Downloads Clean-up Patterns

## Scope & Target
When automating storage clearing on TikTok ("Giải phóng dung lượng" / "Free up space"):
- Location: `automation-core/scripts/clear-tiktok-cache.py`
- Test suite: `automation-core/tests/test_clear_tiktok_cache.py`

## In-App Screen Elements
On the "Giải phóng dung lượng" screen:
1. **Bộ nhớ đệm (Cache)**:
   - Text/Content-desc: `Bộ nhớ đệm` / `Cache`
   - Size label: e.g. `120,5MB`
   - Action: "Xóa" button in row -> Confirm dialog ("Xóa bộ nhớ đệm?") -> "Xóa".
2. **Tải về (Downloads)**:
   - Text/Content-desc: `Tải về` / `Downloads` / `Tập tin tải về`
   - Size label: e.g. `45,2MB`
   - Action: "Xóa" button in row -> Confirm dialog ("Xóa mục tải về?" / "Hội thoại") -> "Xóa".

## Safe Execution Rules
- **Graceful skipping**:
  - If the "Tải về" row is absent, already `0,0MB`, or has no clear button, skip it without raising errors or stalling UI dumps.
- **Confirmation dialog detection**:
  - Check for dialog markers: `Xóa mục tải về?`, `Xóa các mục tải về?`, `Clear downloads?`, or `Hội thoại`/`Dialog` containing `Xóa`/`Clear`.
  - Pick the rightmost button: `target_btn = max(dialog_btns, key=lambda b: b[0])`.
- **Delays & Timing**:
  - `time.sleep(1.5)` after tapping row button.
  - `time.sleep(AFTER_CONFIRM_DELAY)` (2.5s) after confirming cache clear before taking final verification dump.
- **Combined Verification**:
  - Result status is `OK` if cache is `0,0MB` and downloads is `0,0MB` (or not present).
  - Result status is `PARTIAL` if either cache or downloads remains non-zero.
