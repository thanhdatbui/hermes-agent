# Feed Swipe Transient Failure Handling & Canary Testing

## 1. Transient Swipe Failure & Retry Pattern
Trong `python_runner/flows/feed_swipe_smoke.py`, hàm `_perform_feed_swipe` gửi lệnh qua ADB:
```python
cmd = ["input", "swipe", str(start[0]), str(start[1]), str(end[0]), str(end[1]), str(duration_ms)]
```

### Nguyên nhân lỗi:
- ADB shell có thể trả về lỗi transient (`not result.ok` với returncode != 0 hoặc stderr), hoặc ném `ADBError` (timeout/device busy).
- Nếu không có retry loop bao quát cả `not result.ok` và exception, lệnh sẽ lập tức trả về `False`, khiến caller ghi nhận fail `reason: feed swipe command failed` và dừng session.

### Quy tắc Retry chuẩn trong `_perform_feed_swipe`:
- Thiết lập `max_attempts = 3` (hoặc tối đa 2-3 lần).
- Bao quát cả 3 nhánh lỗi:
  - `not result.ok` (stderr/non-zero returncode)
  - `ADBError` (timeout, disconnect tạm thời)
  - Exception transient ngoài ý muốn
- Ghi log retry: `action="feed_swipe", result="retry", error=f"attempt {attempt}/{max_attempts} failed: {last_error}"`
- Chờ `time.sleep(1.0)` giữa các lần thử.
- Chỉ khi tất cả `max_attempts` thất bại mới ghi log `result=ExitStatus.FAIL.value` và trả về `False`.

## 2. Kiểm tra cú pháp sau khi sửa
Trước khi chạy test, luôn biên dịch kiểm tra cú pháp:
```bash
python -m py_compile "D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py"
```

## 3. Lệnh Canary Test nhanh trên 1 máy
Chạy canary test trên máy đơn (ví dụ máy 32) với RecoveryTestSwipes nhỏ và bỏ qua sync workbook để kiểm tra nhanh luồng chạy:
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 32 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```

### Tiêu chí nghiệm thu Canary:
- Exit code: 0
- Log kết thúc: `multi-machine-feed-session completed`, `Status: success`
- File `summary.txt` trong run artifacts:
  - `final_status: success`
  - `swipes_completed: N / N`
  - `blocker category counts: 0`
