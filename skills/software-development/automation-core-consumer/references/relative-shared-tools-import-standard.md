# Chuẩn Hóa Import Path Cho Shared Tools Và Cross-Repo Modules

## 1. Vấn Đề (Problem Statement)
Trong các consumer repos (ví dụ `Tiktok_Reg`, `tiktok-luot nuoi acc`, `Tiktok-video`), việc import các công cụ dùng chung từ thư mục `tools` (hoặc các repo lân cận) nếu dùng đường dẫn tuyệt đối dạng:
```python
sys.path.insert(0, r"D:/Taadaa/tools")
```
sẽ gây ra các vấn đề nghiêm trọng:
1. **Mất tính khả chuyển (Portability):** Khi repo được chạy trên máy tính khác, hoặc khi chuyển ổ đĩa (ví dụ từ `D:` sang `C:` hoặc `E:`), hoặc chạy trong worktree / CI container, đường dẫn hardcode tuyệt đối sẽ bị vỡ.
2. **Không đồng bộ giữa script thực thi và unit test:** Test runner (pytest) khi chạy ở thư mục khác có thể giải quyết import theo cách khác với script thực tế, dẫn đến test pass nhưng production fail hoặc ngược lại.

## 2. Quy Tắc Chuẩn (Relative Import Invariant)
Luôn định vị thư mục gốc của project/repo (`PROJECT_ROOT` hoặc `REPO_ROOT`) bằng `pathlib.Path(__file__).resolve()` và resolve các thư mục dùng chung (như `tools`) tương đối từ đó:

### 2.1. Trong Script Production / Runner
```python
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
# Trỏ đến sibling directory 'tools' cùng cấp với repo
sys.path.insert(0, str(PROJECT_ROOT.parent / "tools"))

from check_gmail_live_fast import check_gmail_live_batch
from remove_device_google_account import remove_device_account_fast
```

### 2.2. Trong File Unit Test (tests/)
Thư mục tests thường nằm sâu hơn 1 cấp so với root của repo:
```python
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT.parent / "tools"))
```

## 3. Anti-Patterns Cần Tránh
- ❌ `sys.path.insert(0, r"D:/Taadaa/tools")` (hardcode tuyệt đối ổ đĩa và đường dẫn cố định).
- ❌ Hardcode chuỗi đường dẫn trong các hàm con thay vì chuẩn hóa từ biến root ở đầu module.
- ❌ Khác biệt giữa cách import trong test file và production file.
