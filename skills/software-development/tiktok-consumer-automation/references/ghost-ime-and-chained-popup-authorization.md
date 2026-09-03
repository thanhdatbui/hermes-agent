# Ghost IME Precedence & Chained Benign Popup Authorization

## 1. Samsung Ghost IME vs. Window Manager Precedence

### Vấn đề (The Problem)
Trên các dòng máy Samsung Galaxy (Galaxy S7/S8 Android 7/8 với bàn phím `com.sec.android.inputmethod/.SamsungKeypad`), lệnh `dumpsys input_method` thường lưu lại các cờ yêu cầu hiển thị cũ (`mInputShown=true`, `mShowRequested=true`) dù bàn phím đã đóng xong từ lâu.
Nếu parser chỉ tìm kiếm `mInputShown=true`, runner sẽ nhận định sai rằng bàn phím vẫn còn mở (`visible=True`), dẫn đến lỗi kẹt `keyboard remained visible after dismiss attempt` và dừng session.

### Quy tắc phân giải tín hiệu (Authoritative Resolution Order)
1. **XML-First Positive-Only:** Cây UI XML chỉ dùng để phát hiện xác thực khi **CÓ** node bàn phím (`KNOWN_KEYBOARD_PACKAGES`). Nếu XML không có node bàn phím, **KHÔNG ĐƯỢC** tự ý kết luận âm tính (vì layout `adjustPan` hoặc edge-to-edge có thể không đưa IME vào hierarchy). Luôn fallback xuống `dumpsys input_method`.
2. **Window Manager Bitmask Precedence:** Trong `dumpsys input_method`, trường `mImeWindowVis` của Window Manager là nguồn sự thật tối thượng:
   - **Bit 1 (`0x2 = IME_VISIBLE`):** Cho biết cửa sổ bàn phím có đang thực sự hiển thị trên màn hình hay không.
   - Nếu `mImeWindowVis` là `0x0` hoặc `0x1` (chỉ active, window ẩn) hoặc `mInputViewShown=false`, kết luận dứt khoát `visible=False`, ghi đè (override) hoàn toàn các cờ stale `mInputShown=true` / `mShowRequested=true`.
   - Nếu `mImeWindowVis` có bit `0x2` (như `0x2`, `0x3`), kết luận `visible=True`.
3. **Conservative Fallback:** Chỉ khi dumpsys hoàn toàn không có trường `mImeWindowVis` hay `mInputViewShown`, mới dùng `mInputShown=true` / `mShowRequested=true` làm fallback thận trọng.

```python
def _parse_ime_window_vis(output: str) -> bool | None:
    match = _IME_WINDOW_VIS_RE.search(output)
    if not match:
        return None
    val_str = match.group(1)
    try:
        val = int(val_str, 16) if val_str.lower().startswith("0x") else int(val_str)
        return bool(val & 0x2)
    except Exception:
        return None
```

---

## 2. Chuỗi Popup Liên Hoàn & Token Authorization (Chained Popup Lifecycle)

### Vấn đề (The Problem)
Khi đóng popup Add Phone (`Thêm số điện thoại`), một popup thứ hai (như `facebook_contacts_email_permission` xin quyền truy cập Facebook/danh bạ) có thể xuất hiện ngay sau đó với package focus là `com.facebook.katana`.
- Nếu chặn ngay vì "TikTok focus lost", flow sẽ dừng trước khi kịp từ chối cấp quyền.
- Nếu mở toang allowlist cho Facebook package, một popup Facebook lạ hoặc độc lập có thể bị bấm nhầm mà không có ngữ cảnh Add Phone.

### Giải pháp Token Authorization Chuẩn (Fail-Closed Token Protocol)
1. **Chỉ cấp Token khi Add Phone đóng thành công:**
   - Sau khi tap `X` đóng Add Phone, kiểm tra nếu màn hình kế tiếp là `manual-needed:popup` và phát hiện đúng dialog Facebook.
   - Cấp một token ngắn hạn (TTL 30 giây) gắn chặt với bộ nhận diện `(device_id, account)`.
2. **Immutable XML Content Hash Binding:**
   - Tính SHA-256 hash của file XML chụp ngay sau khi Add Phone đóng (`_xml_content_hash(after_attempt["xml_path"])`).
   - Token chỉ hợp lệ khi áp dụng cho đúng attempt có nội dung XML khớp với `xml_hash` đã lưu. Mọi hành vi copy token sang XML khác đều bị từ chối `without Add phone chain token`.
3. **Pre-Action Atomic Consumption:**
   - Hàm `_validate_and_consume_add_phone_chain_token` thực hiện `_ACTIVE_CHAIN_TOKENS.pop(key)` **TRƯỚC KHI** phát lệnh tap hoặc dispatch sang Registry.
   - Ngăn chặn triệt để race condition, re-entrant call, hoặc replay token lần thứ 2.
4. **Hủy Token ở tất cả nhánh lỗi:**
   - Bất kỳ failure nào trong flow Add Phone (như popup còn tồn tại, bàn phím kẹt thật, màn hình lạ ngoài allowlist) đều phải gọi `_clear_active_chain_token(ctx)` để hủy token còn sót.
