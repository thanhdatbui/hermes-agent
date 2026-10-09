# Account Switcher Duck-Typed Adapter Contract & Viewport Scroll

## 1. Context & Architecture

`automation_core.tiktok.account_switcher` cung cấp các hàm điều hướng và chuyển đổi tài khoản TikTok (`open_profile_root`, `open_switcher`, `select_exact_account`). Module này thiết kế theo mô hình **Duck-typing**: nó không phụ thuộc cứng vào bất kỳ client ADB cụ thể nào, mà nhận một đối tượng `adapter` từ repo consumer (ví dụ: `TikTokAdapter` trong `tiktok-video/scripts/tiktok_workflow/adapter.py`).

### Interface Duck-Typed Bắt Buộc

| Method | Signature | Mục đích |
|---|---|---|
| `dump_ui` | `() -> str` | Dump UI XML từ thiết bị (bắt buộc ATX session primary) |
| `tap` | `(x: int, y: int) -> None` | Tap tại tọa độ x, y |
| `back` | `() -> bool` | Nhấn nút Back (keyevent 4) |
| **`swipe`** | **`(start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 450) -> None`** | **BẮT BUỘC để cuộn danh sách account switcher khi có >= 7 tài khoản** |
| `tap_profile` | `(force: bool = False) -> None` | (Optional) Tap vào tab Hồ sơ ở thanh điều hướng dưới |
| `is_profile_root`| `(xml_text: str) -> bool` | (Optional) Kiểm tra màn hình Profile chính |
| `profile_identity`| `(xml_text: str \| None) -> dict` | (Optional) Trích xuất username/display name hiện tại |
| `sanitize_switcher_profile_xml`| `(xml_text: str) -> str` | (Optional) Lọc bỏ các phần tử gây nhiễu |
| `coordinate_fallback`| `(action: str) -> tuple[int, int] \| None` | (Optional) Tọa độ fallback khi anchor XML bị che |

---

## 2. Lỗi Hạ Nguồn Khi Thiếu Method `swipe()`

Khi máy có 7–8 tài khoản, hoặc danh sách tài khoản bị xáo trộn do tài khoản phụ/parasite nằm ở đầu, tài khoản mục tiêu (ví dụ: Tik 1 hoặc Tik 8) sẽ bị đẩy xuống ngoài màn hình (viewport > 1920px).

Trong `automation_core.tiktok.account_switcher.select_exact_account`:
```python
try:
    node = find_exact_account(xml, account)
except AccountSwitcherError as exc:
    if exc.code == "ACCOUNT_MISSING":
        logger.info("[ACCOUNT_SWITCHER] Account %s not visible in current viewport; attempting scroll", account)
        swipe_fn = getattr(adapter, "swipe", None)
        if callable(swipe_fn):
            # Vuốt lên để cuộn xuống
            ...
        if found_node is not None:
            node = found_node
        else:
            raise  # Re-raises ACCOUNT_MISSING
```

Nếu `TikTokAdapter` **không có method `swipe`**:
1. `swipe_fn` trả về `None`, vòng lặp cuộn không được thực thi.
2. Hàm văng lỗi ngay lập tức: `[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found. Cần MANUAL_REVIEW...`
3. `batch_aggregator.py` phát hiện lỗi này và gắn nhãn: `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]`.
4. **Hậu quả**: Báo động giả nghiêm trọng. Nick vẫn đăng nhập 100% trên máy nhưng bot tưởng nhầm bị văng nick và dừng batch.

---

## 3. Triển Khai Chuẩn Trên Consumer Adapter

Trong class adapter (ví dụ: `scripts/tiktok_workflow/adapter.py`):

```python
def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 450) -> None:
    """Swipe between coordinates (e.g. for scrolling account switcher list)."""
    if self.dry_run:
        logger.info(f"[DRY-RUN] swipe({start_x}, {start_y}, {end_x}, {end_y}, {duration_ms})")
        return
    logger.debug("[ADAPTER_SWIPE] Swiping (%d, %d) -> (%d, %d) dur=%dms", start_x, start_y, end_x, end_y, duration_ms)
    result = self._adb.shell(
        ["input", "swipe", str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)],
        timeout=15,
        check=False,
    )
    if not result.ok:
        logger.warning("[ADAPTER_SWIPE_FAILED] swipe (%d, %d) -> (%d, %d) err: %s", start_x, start_y, end_x, end_y, result.stderr or result.stdout)
        raise AccountSwitcherError("SWIPE_FAILED", f"swipe failed: {result.stderr or result.stdout}")
```

---

## 4. Kỷ Luật Sol Auditor Closeout Gate (>= 85 Điểm)

Khi sửa code adapter hoặc runner tương tác với ADB, Sol Auditor (:20129) chấm điểm rất khắt khe về độ tin cậy và khả năng quan sát (Observability):

1. **Tuyệt đối cấm chỉ viết 1 happy-path test**: Nếu chỉ test lệnh ADB dispatch thành công, điểm review sẽ rơi xuống **70/100 (REJECTED)** vì thiếu kiểm chứng failure mode, integration và telemetry.
2. **Bộ test 4 lớp bắt buộc (`tests/test_adapter.py`)**:
   - **Happy Path**: Xác nhận `adb.shell` gọi đúng danh sách `["input", "swipe", "x1", "y1", "x2", "y2", "dur"]`.
   - **Dry Run**: Xác nhận khi `dry_run=True`, không có lệnh ADB nào được gửi.
   - **Failure Exception**: Khi `result.ok=False`, bắt buộc raise đúng `AccountSwitcherError` với code `SWIPE_FAILED`.
   - **Integration Test**: Giả lập kịch bản `select_exact_account` gọi `adapter.dump_ui` lần 1 (chưa có nick) -> gọi `adapter.swipe` -> gọi `adapter.dump_ui` lần 2 (thấy nick) -> hoàn tất chọn nick.
3. **Telemetry & Log**: Bắt buộc có logging cấu trúc rõ ràng (`[ADAPTER_SWIPE]`, `[ADAPTER_SWIPE_FAILED]`).
4. **Lệnh chạy Closeout Gate an toàn**:
   ```bash
   python D:/Taadaa/tools/closeout_gate.py --repo <đường_dẫn_repo> --base HEAD~1 --json-output
   ```
   *Lưu ý*: Luôn đặt `timeout: 60` trong terminal foreground để không bị guard chặn.
