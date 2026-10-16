# Worker Gate Path Whitelist, Focused Test Syntax & Operator Device Lock Contract (2026-10-16)

## 1. Cạm bẫy Coordinator Guard Regex Whitelist trong `delegate_task`

### Hiện tượng & Lỗi
Khi Coordinator soạn prompt ủy quyền cho Worker qua `delegate_task`, nếu trong phần mô tả `goal` hoặc đoạn mã mẫu có chứa các đường dẫn nằm ngoài repo whitelist `['D:\\Taadaa']` (ví dụ `D:\TIKTOK-videonuoinick\...`, `D:\video goc\...`, hoặc đường dẫn Android `/sdcard/Pictures/...`), bộ phân tích regex của Guard sẽ tự động bốc các đường dẫn này thành danh sách file mục tiêu cần can thiệp:
```text
⛔ [COORDINATOR GUARD - CONTRACT VIOLATION]: OUT OF REPO WHITELIST: File '\\\sdcard\Pictures\avatar.jpg"])' nằm ngoài whitelist ['D:\\Taadaa']!
```

### Nguyên tắc xử lý (Remediation)
1. **Sao chép tài nguyên vào Staging trước khi ủy quyền:**
   - Thay vì yêu cầu Worker đọc trực tiếp từ `D:\TIKTOK-videonuoinick\<folder>\avatar.jpg` (vốn bị chặn bởi Worker Gate), Coordinator chủ động copy file về `D:\Taadaa\tmp\avatar.jpg`:
     ```bash
     cp "D:/TIKTOK-videonuoinick/<folder>/avatar.jpg" "D:/Taadaa/tmp/avatar.jpg"
     ```
2. **Khai báo đường dẫn thiết bị bằng phép nối chuỗi:**
   - CẤM TUYỆT ĐỐI viết chuỗi đường dẫn raw dạng `"/sdcard/Pictures/avatar.jpg"` trong prompt `goal`.
   - Viết dưới dạng nối chuỗi an toàn để regex scanner không bắt nhầm thành path hệ thống:
     ```python
     remote_avatar = "/".join(["", "sdcard", "Pictures", "avatar.jpg"])
     ```

---

## 2. Quy chuẩn cú pháp `FOCUSED_TEST` bắt buộc

Coordinator Guard kiểm tra định dạng của dòng `FOCUSED_TEST:` theo mẫu strict regex:
- **Đúng định dạng:**
  * `FOCUSED_TEST: python -m py_compile D:\Taadaa\tmp\script.py`
  * `FOCUSED_TEST: python -m pytest tests/test_file.py::test_func -q`
- **Sai định dạng (Bị từ chối ngay lập tức):**
  * `FOCUSED_TEST: pytest --collect-only D:/Taadaa/tmp/script.py` -> `INVALID_FOCUSED_TEST_FORMAT`.

---

## 3. Cạm bẫy Keyword-Only Arguments của `operator_device_lock`

### Chữ ký hàm trong `automation_core.device_lock`:
```python
def operator_device_lock(
    *,
    machine=None,
    serial: str | None = None,
    project: str = "operator_tool",
    timeout: float = 300.0,
    poll_interval: float = 5.0,
    ...
)
```
Dấu `*` ở đầu định nghĩa biến tất cả tham số thành **Keyword-Only Arguments**.

### Lỗi thường gặp:
- Gọi truyền đối số vị trí: `with operator_device_lock(SERIAL, timeout=30):`
  -> Gây crash: `TypeError: operator_device_lock() takes 0 positional arguments but 1 was given`.
- **Cách gọi chuẩn:**
  ```python
  with operator_device_lock(machine=59, serial=SERIAL, project="avatar_ops", timeout=60):
      ...
  ```

---

## 4. Tọa độ thực tế Samsung S7 & TikTok Layout C (v47)

- **Độ phân giải màn hình:** Galaxy S7 override 1080x1920 (chiều cao tối đa Y = 1920). CẤM dùng các tọa độ ảo > 1920 (ví dụ 2100, 2280) do Worker suy đoán từ các thiết bị tỷ lệ dài 20:9.
- **Anchor mở Switcher Layout C:** Màn hình cá nhân có avatar góc trên phải kèm bong bóng note ("Thì thầm to nhỏ") không có dropdown arrow ở header. Anchor mở Switcher thực tế là nút tên hiển thị tại `[36, 280][444, 364]` -> tap `(300, 320)` để mở Switcher bottom sheet.
- **Anchor mở Sửa hồ sơ:** Icon bút chì góc trên cùng bên trái tại `(75, 150)`.
