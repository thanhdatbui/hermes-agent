# Profile Guard Feed Drift Recovery & Runner Verification Pitfalls

## 1. Triệu chứng lỗi "profile username still mismatched after switch"
- **Hiện tượng**: Máy farm báo lỗi `profile username still mismatched after switch (expected: ..., got: @...)`. Giá trị `got` thường là handle của creator video đang hiển thị trên feed (ví dụ màn hình For You).
- **Nguyên nhân gốc**:
  - Khi switch account qua TikTok account switcher, app mặc định quay về feed chính (Home / For You).
  - Thao tác tap vào nút Profile ngay sau đó bị dropped do độ trễ reload / render của TikTok, khiến màn hình vẫn ở Feed thay vì Profile.
  - Trong `python_runner/flows/feed_swipe_smoke.py`:
    - Hàm `_profile_guard_drifted_from_profile(row)` trước đây chỉ trả về `True` khi có `keyboard cleanup` trong reason hoặc `xml_error in FEED_CONFIRMED_XML_DEGRADED_ERRORS`.
    - Khi XML dump thành công (sạch, `xml_error == ""`), hàm trả về `False` dù `detected` là `home`, `FEED_TYPE_FOR_YOU`, `FEED_TYPE_FOLLOWING`, hay `FEED_TYPE_FRIENDS`.
    - `_read_profile_identity_with_add_phone_guard` do đó bỏ qua re-tap, gọi `read_profile_identity(ctx)` đọc nhầm màn hình Feed là Profile, lấy username của video creator và văng lỗi mismatch.

## 2. Quy tắc xử lý & Contract chuẩn
- **Tại `_profile_guard_drifted_from_profile`**:
  - Bắt buộc kiểm tra `if detected in {"home", FEED_TYPE_FOR_YOU, FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS}: return True`.
- **Tại `_read_profile_identity_with_add_phone_guard`**:
  - Nhánh gọi `_try_profile_retap_on_drift(ctx, guard_row, guard_step)` phải kích hoạt khi:
    `if _is_degraded_xml_drift(guard_row) or str(guard_row.get("detected") or "") in {"home", FEED_TYPE_FOR_YOU, FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS}:`

## 3. Ad-hoc Verification Pitfalls cho `python_runner`
- **Cấu trúc import**:
  - Package `core` (Actions, DeviceContext, ADBError, ...) nằm trực tiếp tại:
    `D:/Taadaa/tiktok-luot nuoi acc/python_runner/core`
  - Trong script test ad-hoc độc lập, bắt buộc cấu hình sys.path:
    ```python
    python_runner_path = r'D:/Taadaa/tiktok-luot nuoi acc/python_runner'
    sys.path.insert(0, python_runner_path)
    from flows.feed_swipe_smoke import _profile_guard_drifted_from_profile, ...
    ```
- **Kỷ luật chống quét đĩa**:
  - TUYỆT ĐỐI KHÔNG dùng `os.walk`, `glob(recursive=True)`, `find`, hay `grep -rn` quét tìm `core` hay file trên `D:/Taadaa`. Ổ đĩa farm và codebase rất lớn sẽ gây treo hoặc timeout command (900s).
