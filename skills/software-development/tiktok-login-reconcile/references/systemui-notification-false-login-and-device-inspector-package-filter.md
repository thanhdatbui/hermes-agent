# SystemUI Notification False-Positive Login & Device Inspector Package Filter

## Bối cảnh sự cố (Session 2026-09-22 / Machine M40)
- **Triệu chứng**: Trong ca nuôi feed Row 6, máy M40 thiếu nick `gabruync3o9` trong Switcher (máy có 7 nick, thiếu 1 nick). Runner kích hoạt cơ chế `auto_login_recovery` gọi `reconcile_tiktok_accounts.py`.
- **Lỗi dừng phiên**: Reconcile crash ngay lập tức với lỗi:
  `AccountInventoryError: machine 40: TikTok ID/password is unavailable for kanyeujfauq`
- **Nghịch lý**: `kanyeujfauq` thực tế ĐÃ ĐĂNG NHẬP và hiển thị sờ sờ trên Account Switcher của máy, nhưng trong file Excel chưa điền mật khẩu TikTok (nick mới reg). Tại sao reconcile lại đòi nạp `kanyeujfauq`?

---

## Phân tích nguyên nhân gốc rễ (Root Cause Chain)

1. **SystemUI Leak trong UI XML Dump**:
   - Khi uiautomator dump toàn bộ cây view trên Android, cây hierarchy chứa cả các node thuộc `package="com.android.systemui"` (thanh trạng thái, notification drawer ngầm):
     ```xml
     <node package="com.android.systemui" text="" content-desc="Thông báo của Dịch vụ Google Play: Yêu cầu đăng nhập" />
     <node package="com.android.systemui" text="" content-desc="Thông báo của Dịch vụ Google Play: Mới đăng nhập trên Windows" />
     ```
2. **_allowlisted_ui_text quét phẳng không lọc package**:
   - Trong `login_runner/device_inspector.py`, hàm `_allowlisted_ui_text(xml_text)` bóc toàn bộ `text` và `content-desc` của mọi node trong hierarchy mà không kiểm tra thuộc tính `package`.
   - Cụm từ `"Yêu cầu đăng nhập"` chứa từ khóa `"đăng nhập"` thuộc `LOGIN_MARKERS = ("log in", "login", "đăng nhập", ...)`.
3. **Phân loại sai màn hình (False-Positive Login Classification)**:
   - `classify_screen` nhận thấy `"đăng nhập"` trong searchable text nên trả về `screen = "login"` ngay cả khi app TikTok đang mở tab Feed hoặc Account Switcher.
4. **Trigger bẫy văng sạch tài khoản trong Reconcile**:
   - Trong `account_reconcile.py`, hàm `_is_logged_out_auth_screen` kiểm tra `inspection.screen == "login"`.
   - Khi trả về `True`, script kích hoạt giả định: *Máy đã bị văng toàn bộ tài khoản, switcher không mở được -> Phải nạp lại toàn bộ 8 nick trong Excel*:
     ```python
     before = compare_accounts(target, ())  # coi như device_missing = ALL 8 ACCOUNTS
     ```
5. **Crash do tài khoản thiếu pass trong Excel**:
   - Khi `_select_missing_accounts` duyệt qua danh sách 8 tài khoản, nó kiểm tra tính khả dụng của mật khẩu.
   - Gặp nick `kanyeujfauq` (pass rỗng), script quăng `AccountInventoryError`, hủy toàn bộ phiên cứu hộ mà không kịp nạp nick `gabruync3o9` thật sự đang thiếu.

---

## Giải pháp kỹ thuật chuẩn hóa (2-Layer Guard)

### Lớp 1: Package Allowlist trong `_allowlisted_ui_text`
Chỉ gom text từ các node thuộc `TIKTOK_PACKAGES = ("com.zhiliaoapp.musically", "com.ss.android.ugc.trill")`. Bỏ qua tuyệt đối các node thuộc `com.android.systemui` hoặc app rác ngoài luồng:
```python
def _allowlisted_ui_text(
    xml_text: str | None,
    package_allowlist: tuple[str, ...] = TIKTOK_PACKAGES,
) -> str:
    if not xml_text or not _is_ui_xml(xml_text):
        return ""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return ""
    values: list[str] = []
    for node in root.iter("node"):
        pkg = node.attrib.get("package")
        if pkg and package_allowlist and pkg not in package_allowlist:
            continue
        values.extend((node.attrib.get("text", ""), node.attrib.get("content-desc", "")))
    return " ".join(values).casefold()
```

### Lớp 2: Switcher Guard trong `classify_screen`
Trước khi phân loại là `login`, kiểm tra xem màn hình có phải là Account Switcher đang mở không bằng `is_switcher_open(xml_text)`:
```python
    if xml_text and _is_ui_xml(xml_text):
        try:
            from automation_core.tiktok.account_switcher import is_switcher_open
            if is_switcher_open(xml_text):
                return "account_switcher", ()
        except Exception:
            pass
```

---

## Pitfall vận hành & kiểm thử
1. **Windows Drive Cross-Mount trong Unittest**:
   - Khi đứng tại ổ `C:` (`C:\Users\Kibe`), lệnh `python -m unittest D:/Taadaa/...` sẽ văng lỗi `ValueError: path is on mount 'D:', start on mount 'C:'` do hàm `os.path.relpath` nội tại của unittest.
   - **Bắt buộc**: Phải `cd /d/Taadaa/tiktok-log-in` trước khi chạy unittest.
2. **Tránh chạy nhầm test suite tích hợp ADB**:
   - `test_account_reconcile.py` chứa các test case kết nối ADB thực tế tới `localhost:5037` nếu không mock kín, gây timeout 180s.
   - Khi kiểm thử phân loại màn hình, CHỈ chạy focused test:
     ```bash
     cd /d/Taadaa/tiktok-log-in && PYTHONPATH=".;D:/Taadaa/automation-core/src" python -m unittest discover -s tests -p "test_device_inspector.py"
     ```
     (thời gian chạy `< 0.1s`).
3. **Tiêu chuẩn Test Fixture cho `is_switcher_open`**:
   - Hàm `is_switcher_open` trong `automation_core.tiktok.account_switcher` có guard chặt: đòi hỏi `bool(account_like)` kết hợp với `has_add_account` hoặc `has_selected_account`.
   - CẤM viết fixture XML chỉ có mỗi node tiêu đề `"Chuyển đổi tài khoản"`. Fixture bắt buộc phải có đủ:
     1. Node tiêu đề: `text="Chuyển đổi tài khoản"`
     2. Node tài khoản: `text="<username>"`
     3. Node thêm tài khoản: `text="Thêm tài khoản"`
     (Thiếu 1 trong các node này sẽ khiến `is_switcher_open` trả về `False`).
