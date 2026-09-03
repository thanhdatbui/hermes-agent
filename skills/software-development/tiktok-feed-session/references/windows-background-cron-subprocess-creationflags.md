# Quy chuẩn Subprocess CreationFlags & Cohort Target Identity trong Windows Background Cron

## 1. Windows Background Cron Subprocess CreationFlags
### Bối cảnh
- Khi `tiktok_runner.py` (hoặc các wrapper cron Python chạy nền không có console) khởi chạy tiến trình con PowerShell hoặc Python (ví dụ `scripts/run-feed-session.ps1`):
- Nếu sử dụng `creationflags = 0x00000208` (`CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS`), tiến trình con PowerShell sẽ bị đóng ngay lập tức (PID chết sau 0.1s) trong môi trường Windows MSYS/Git-Bash do không có handle console hợp lệ.

### Giải pháp chuẩn hóa
- Luôn sử dụng flag `0x08000200` (`CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`):
```python
if sys.platform == "win32":
    popen_kwargs["creationflags"] = 0x08000200  # CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
else:
    popen_kwargs["start_new_session"] = True
```

---

## 2. Cohort Target Identity Validation Rules
### Bối cảnh & Hiện tượng
- Hàm `_apply_cohort_identity` trong `multi_machine_feed_session.py` làm nhiệm vụ đối soát tài khoản thực tế đọc từ workbook với kế hoạch được chỉ định trong cohort plan.
- Nếu code kiểm tra cứng:
```python
if "tik" not in expected:
    mismatches.append("missing:tik")
```
thì trên các ca nuôi acc buổi chiều/tối (Row 3, 4, 5, 6) mà manifest cohort không khai báo trường `tik`, toàn bộ máy sẽ bị báo lỗi `cohort target identity mismatch: missing:tik`, sinh file lock `blocked` và dừng toàn bộ phiên.

### Giải pháp chuẩn hóa
- Chỉ đối soát `tik` khi trong cohort plan thực sự có khai báo key `"tik"`:
```python
if "tik" in expected:
    val = expected.get("tik")
    if type(val) is bool or not isinstance(val, (int, str)) or not str(val).strip() or str(val) != str(account.tik):
        mismatches.append("mismatch:tik")
```
