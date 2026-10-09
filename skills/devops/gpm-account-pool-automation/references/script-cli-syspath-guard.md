# GPM Auto Script CLI Execution & sys.path Guard

## Problem
Khi thực thi trực tiếp các script tự động hóa trong `D:\Taadaa\GPM auto\scripts\*.py` từ terminal hoặc cron (ví dụ:
`python "D:\Taadaa\GPM auto\scripts\chatgpt_gpm_direct_reg.py" --provider hotmail --dry-run`
), Python mặc định đặt thư mục chứa script (`D:\Taadaa\GPM auto\scripts`) làm `sys.path[0]`, chứ KHÔNG phải root repository (`D:\Taadaa\GPM auto`).

Khi script import các module từ gói nội bộ như `src` (ví dụ `from src.cdp_auth import save_password_prompt`):
```text
ModuleNotFoundError: No module named 'src'
```

## Solution Pattern
Luôn khởi tạo `BASE_DIR` và thêm vào `sys.path` TRƯỚC khi import bất kỳ module nào thuộc `src`:

```python
import os
import sys
from pathlib import Path

# Paths
BASE_DIR = Path(r"D:\Taadaa\GPM auto")
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Safe to import from src now
from src.cdp_auth import save_password_prompt
```

## CLI Dry-Run Testing Pattern
Khi kiểm thử candidate matching cho script:
- Lưu ý tham số `--limit` có thể có default (ví dụ `default=2`).
- Nếu muốn quét toàn bộ ứng viên đang có trong database (ví dụ 5 tài khoản Hotmail đã có đủ credentials và pass ChatGPT), truyền `--limit 5` hoặc giá trị lớn hơn tương ứng.
