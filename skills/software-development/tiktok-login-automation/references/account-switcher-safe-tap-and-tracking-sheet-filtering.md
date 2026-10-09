# Account Switcher Bottom-Sheet Safe Tap & Tracking Sheet Filtering

## 1. Bối cảnh & Hiện tượng sự cố (Incident Root Cause)

### A. Lỗi nạp tracking từ nhiều worksheet (`load_tracking_accounts_for_stt`)
- **Hiện tượng**: Khi chạy fast login bù tài khoản cho một máy (ví dụ Máy 72 với `@m.ngc4624`), script báo lỗi dừng khẩn cấp:
  `STOPPED: Khong tim thay Gmail live tren may khop local-part 'duongthimyngoc190320011903' de xac nhan domain`
  mặc dù nick có đầy đủ TikTok ID, mật khẩu và mã 2FA TOTP trong workbook.
- **Nguyên nhân cốt lõi**:
  - File Excel tracking (`taikhoan_dat_v2_updated .xlsx`) chứa nhiều worksheet: sheet chính `Tài Khoản` (đầy đủ email `@gmail.com`, pass, 2FA secret), nhưng cũng chứa các sheet audit/nháp như `Khong Co Trong GmailClean`, `Audit Pending`, `Máy Thiếu Acc`.
  - Trong các sheet audit, cột email thường chỉ ghi local-part không có domain `@gmail.com` (ví dụ: `duongthimyngoc190320011903`).
  - Hàm `load_tracking_accounts_for_stt` lặp qua mọi worksheet không phân biệt, nạp cả dòng audit với cờ `issues = ["email_missing_domain"]`.
  - Khi script gọi `resolve_missing_domains_from_device`, nó truy vấn danh sách Gmail đang đăng nhập trên máy S7. Vì trên máy không có Gmail này, script ném ngoại lệ dừng lại dù nick hoàn toàn có thể đăng nhập bằng ID + Password + TOTP!

### B. Bẫy tọa độ tap sát đáy thanh điều hướng (`tap_add_account`)
- **Hiện tượng**: Máy có 7 tài khoản trong Account Switcher (chưa chạm trần 8 nick), nút *"Thêm tài khoản"* vẫn hiển thị nhưng script bị timeout 300s hoặc văng `[04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)`.
- **Nguyên nhân cốt lõi**:
  - Khi Switcher đã có 7 nick, nút *"Thêm tài khoản"* bị dồn xuống đáy màn hình: bounds `[0,1788][1080,1920]`.
  - Hàm mặc định `find_text_tap()` tính tọa độ tâm của node: `(cx, cy) = (540, 1854)`.
  - Trên màn hình Samsung Galaxy S7 (1080x1920), vùng $y \ge 1840$ là vùng sát mép đáy / thanh điều hướng hệ thống (Navigation Bar / Gesture Guard). Tap vào tọa độ $y = 1854$ bị hệ thống chặn hoặc trượt khỏi vùng nhận diện click của TikTok bottom sheet.

---

## 2. Giải pháp chuẩn hóa (Production Architecture)

### 1. Khóa lọc Sheet Canonical trong `load_tracking_accounts_for_stt`
Chỉ nạp tài khoản từ các worksheet chính quy, loại trừ tuyệt đối các sheet audit:
```python
def load_tracking_accounts_for_stt(stt, tracking_path=TRACKING_PATH):
    wb = openpyxl.load_workbook(tracking_path, data_only=True)
    accounts = []
    # Chỉ đọc sheet tài khoản chính chủ ("Tài Khoản" hoặc "Accounts"), loại trừ các sheet audit/nháp
    if "Tài Khoản" in wb.sheetnames:
        worksheets = [wb["Tài Khoản"]]
    elif "Accounts" in wb.sheetnames:
        worksheets = [wb["Accounts"]]
    else:
        worksheets = [
            ws for ws in wb.worksheets
            if ws.title not in ("Khong Co Trong GmailClean", "Máy Thiếu Acc", "Audit Pending")
        ] or [wb.active]
    for ws in worksheets:
        # load rows...
```

### 2. Ưu tiên Bản ghi Canonical & Fallback Inferred Domain
- Trong `pick_accounts`: Nếu target khớp nhiều bản ghi (do sheet dự phòng), ưu tiên lấy bản ghi từ sheet `Tài Khoản`/`Accounts` không có cờ `issues`.
- Trong `resolve_missing_domains_from_device`: Nếu tài khoản đã có `id` và `tiktok_pass` (không bật `--otp-only`), tự động fallback gán `local_part + "@gmail.com"` để cho phép flow đăng nhập trực tiếp bằng ID + Pass + TOTP:
```python
if not resolved:
    if acc.get("id") and acc.get("tiktok_pass") and not acc.get("otp_only"):
        resolved = f"{local_part}@gmail.com"
        log(f"   [gmail-check] warn: Khong tim thay Gmail live tren may cho '{local_part}', fallback inferred: {resolved} (ID+Pass login)")
    else:
        raise RuntimeError(f"Khong tim thay Gmail live tren may khop local-part '{acc['gmail_raw']}' de xac nhan domain")
```

### 3. Công thức Tọa độ Tap An Toàn (Upper-Third Safe Point) cho Row Sát Đáy
Trong `tap_add_account()`: Trước khi gọi `find_text_tap`, tìm node bằng `find_node_in_xml`. Nếu tìm thấy node, tính tọa độ tap ở **1/3 phần trên của row** thay vì tâm:
```python
add_node = find_node_in_xml(
    get_ui_xml(device_id),
    "Thêm tài khoản", "Add account", "Thêm tài khoản khác",
    "Add another account", "add_account",
    prefer_clickable=True,
    package=APP_PACKAGE,
)
if add_node:
    row_bounds = add_node.get("bounds", "")
    bounds_match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", row_bounds)
    if bounds_match:
        x1, y1, x2, y2 = (int(value) for value in bounds_match.groups())
        safe_x = (x1 + x2) // 2
        safe_y = y1 + max(1, (y2 - y1) // 3)
        log(f"   ✓ tap Add account safe row point ({safe_x}, {safe_y}) bounds={row_bounds}")
        tap(device_id, safe_x, safe_y, wait=D_MEDIUM)
        return
```
- **Chứng minh số học trên Samsung S7 (1080x1920)**:
  - Row bounds: `[0, 1788][1080, 1920]`
  - Tâm cũ: $y = (1788 + 1920) / 2 = 1854$ (dính thanh điều hướng)
  - Safe-y mới: $y = 1788 + (1920 - 1788) / 3 = 1788 + 44 = 1832 < 1840$ (hoàn toàn nằm trong vùng hiển thị an toàn của row).

---

## 3. Focused Verification Unit Tests (< 15s)
- `tests/test_tap_add_account_safe_point.py`:
  - `test_tap_add_account_uses_safe_point_not_center`: Mock XML chứa node bounds `[0,1788][1080,1920]`, xác minh lệnh tap gọi `(540, 1832)` thay vì `(540, 1854)`.
  - `test_safe_point_calculation_contract`: Kiểm tra hợp đồng tính toán công thức 1/3.
- `tests/test_tiktok_login_sheet_filter.py`:
  - `test_load_tracking_accounts_for_stt_only_loads_canonical_sheet`: Xác minh chỉ nạp sheet `Tài Khoản`, bỏ qua sheet audit.
  - `test_resolve_missing_domains_fallback_for_id_pass`: Xác minh ID+Pass không bị crash khi thiếu domain Gmail trên máy.
