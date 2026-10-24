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

---

## 5. Sticky Header Profile Switcher & Single-Account Edge Case

### Thiết Kế Chuẩn Mở Switcher (Sticky Header)
Trên các phiên bản TikTok mới (v46.x), ngoài nút mũi tên chevron ▼ ở cạnh tên, thiết kế chuẩn để mở Account Switcher là:
1. Khi ở tab Hồ sơ (Profile), thực hiện vuốt cuộn nhẹ (`swipe 540 1200 540 600`) để username/ID tài khoản ghim lên thanh **Sticky Header** trên cùng chính giữa màn hình (tương ứng container `pmi` / text `pmf`, `bounds=[366, 72][732, 228]`, tâm `(549, 150)`).
2. Tap vào thanh sticky header này (`tap 549 150`) để bung popup "Chuyển đổi tài khoản" (Account Switcher bottom sheet) chứa danh sách tài khoản và nút "Thêm tài khoản".

### Bẫy Ngoại Lệ Máy Chỉ Có 1 Tài Khoản (Single-Account Trap)
1. **Hiện tượng**:
   - Khi máy chỉ có duy nhất 1 tài khoản (ví dụ máy mới bắt đầu reg từ Slot 1, các slot 2–8 còn trống):
     * Cả Header thông thường lẫn thanh Sticky Header trên cùng chính giữa đều là text tĩnh, **hoàn toàn không có icon mũi tên chevron ▼** và tap/long-press vào đều trơ ra không bung switcher.
     * Trong `Cài đặt và quyền riêng tư` (Settings): Mục `"Chuyển đổi tài khoản"` / `"Thêm tài khoản"` biến mất hoàn toàn. Đáy trang Settings chỉ có danh mục `"Đăng nhập"` với nút duy nhất là **"Đăng xuất"**.
2. **Quy trình chuẩn reg tài khoản thứ 2**:
   - Kiểm tra sổ cái đối soát: nếu máy chỉ có 1 tài khoản, không cố lặp lại việc tìm switcher hay "Chuyển đổi tài khoản".
   - Điều hướng vào Settings -> cuộn xuống đáy -> chọn **"Đăng xuất"** (TikTok tự động lưu session nick cũ vào One-tap login) -> bấm xác nhận Đăng xuất.
   - Màn hình Profile trở về trạng thái Đăng ký (Signup) trống -> tiếp tục flow chọn Email để reg tài khoản thứ 2. Sau khi reg xong nick thứ 2, TikTok mới kích hoạt lại menu Account Switcher cho cả 2 tài khoản.

### Safe Swipe Bounds Tránh Cử Chỉ Samsung Pay (1080x1920)
- Trên Samsung Galaxy S7 (SM-G930F/L/K/S), mép dưới màn hình `[300, 1893][780, 1920]` có tab vuốt nhanh Samsung Pay / Quick Pay.
- CẤM vuốt bắt đầu từ `y >= 1500` (như `swipe 540 1650 540 350`) vì sẽ kéo nhầm Samsung Pay đè lên và làm văng TikTok ra ngoài màn hình chính Android.
- Dải tọa độ an toàn chuẩn: `y_start = 1350`, `y_end = 500`, duration 300–400ms.

### Kỷ Luật Phản Hồi Hình Ảnh Thực Tế
- User duyệt tiến độ bằng mắt qua ảnh. Khi báo cáo trạng thái Canary ("Chạy chưa?", "Xong chưa?"), BẮT BUỘC gửi kèm `MEDIA:<path_anh>` chụp màn hình giao diện TikTok máy thật.
- CẤM TUYỆT ĐỐI gửi text chay hoặc gửi ảnh màn hình Home/Launcher của điện thoại (tránh phản ứng: *"Hình đâu"*, *"Gửi tao màn home của máy chi v"*).

