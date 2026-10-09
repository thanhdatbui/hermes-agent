# Follow Cooldown State Consistency & Test Conventions

## 1. Focused Unit Test Setup trong `python_runner/tests/`
Khi tạo unit test mới trong repo `tiktok-luot nuoi acc/python_runner/tests/`:
- **BẮT BUỘC** có `import _path_setup  # noqa: F401` ở đầu file test trước khi import bất kỳ module nào từ `flows.*` hoặc `core.*`.
- Nếu thiếu `_path_setup`, pytest sẽ báo lỗi:
  ```
  ModuleNotFoundError: No module named 'flows.feed_swipe_smoke'
  ```
  vì thư mục `python_runner` không tự động nằm trong `sys.path` của runner.

```python
from __future__ import annotations

import _path_setup  # noqa: F401

from flows.feed_swipe_smoke import is_account_in_follow_cooldown
```

## 2. Follow Cooldown State Consistency Contract (`feed_swipe_smoke.py`)
Hàm `is_account_in_follow_cooldown(ctx)` chịu trách nhiệm kiểm tra tài khoản có bị phạt do nhả follow hay không. Khi bảo trì hoặc mở rộng, bắt buộc tuân thủ 3 nguyên tắc:

1. **Không fallback machine-level:**
   - Match chính xác theo cặp `(machine, row)` tại file `follow_state_{machine}_row_{row}.json`.
   - Tuyệt đối không fallback sang `follow_state_{machine}.json` khi row không có file, nhằm tránh phạt nhầm toàn bộ các tài khoản khác trên cùng thiết bị.
   - Nếu `machine is None` hoặc `row is None`, an toàn trả về `False`.

2. **Chuẩn hóa 100% thời gian theo UTC:**
   - So sánh thời gian tuyệt đối dựa trên UTC (`datetime.now(timezone.utc)`).
   - Parse `cooldown_until_at` và chuẩn hóa timezone sang UTC (`until_dt.astimezone(timezone.utc)`), tránh lỗi so sánh lệch ngày/giờ giữa UTC và local time (GMT+7).

3. **Auto-sync expiry (Dọn dẹp Zombie State):**
   - Khi cooldown đã hết hạn (`now_utc >= until_dt`), hàm phải chủ động xóa bỏ trạng thái lỗi trên đĩa ngay lập tức:
     - `follow_failed = False`
     - `fail_streak = 0`
     - Xóa các trường `cooldown_until_at`, `cooldown_until_date`, `follow_failed_date`, `last_failed_date`, `last_failed_at`.
   - Ghi an toàn qua file tạm `.json.tmp` rồi `os.replace` để bảo đảm tính atomic, tránh corrupt file JSON nếu tiến trình bị kill giữa chừng.
