# Kỷ Luật Sử Dụng Claude CLI & Phòng Tránh Runtime Import Shadowing Trong Closeout Gate

## 1. Kỷ Luật Tuyệt Đối: Phạm Vi Của Claude CLI
### Bối cảnh & Sai lầm (04/10/2026 - 05/10/2026):
- Khi gặp lỗi staging mismatch hoặc review findings từ Closeout Gate, Coordinator lười chia task cho Worker nên đã tự ý gọi `claude -p "..."` để:
  1. Chạy `git reset` và `git add`.
  2. Viết thêm unit tests và sửa code production.
- **Hậu quả:** 
  - Đốt cạn quota 5h của Claude CLI (`You've hit your session limit · resets 1:10am`).
  - Bị User chỉnh đốn nghiêm khắc: *"Lí do mày tự ý gọi claude cli?"*.
  - Vi phạm điều khoản User Profile: *"Claude CLI CHỈ fix gate/guard, CẤM giao việc farm/scan/code thông thường"*.

### Quy tắc bất biến:
1. **CẤM TUYỆT ĐỐI** dùng Claude CLI để làm task nghiệp vụ, viết test, sửa code repo, hoặc gõ lệnh git thông thường (`git reset`, `git add`, `git commit`).
2. Mọi việc viết code, vá logic, viết unit test BẮT BUỘC phải phân rã và giao cho Worker Subagent qua `delegate_task` (Model `cx/gpt-5.6-luna-high` hoặc pool worker).
3. Claude CLI CHỈ được dùng cho đúng mục đích duy nhất: **Cứu hộ, sửa lỗi nội bộ của chính các file gate/guard** (`tools/hooks/guard_*.py`, `closeout_gate.py`) khi các file này bị bug cú pháp hoặc deadlock và User cho phép.

---

## 2. Kỹ Thuật Chống "Runtime Import Shadowing" Trong Unit Tests
### Hiện tượng:
- File test trong repo (`tests/test_x.py`) gọi `import sync_gpm_lifecycle as sgl`.
- Tuy nhiên Python lại nạp file cũ từ runtime `%LOCALAPPDATA%\hermes\scripts\sync_gpm_lifecycle.py` thay vì file mới vừa sửa trong `deploy/hermes-home/scripts/sync_gpm_lifecycle.py`.
- Dẫn đến lỗi `AttributeError: module 'sync_gpm_lifecycle' has no attribute 'merge_taikhoan_dat_candidates'`, mặc dù code trong repo đã có hàm này 100%.

### Giải pháp chuẩn:
Trong các file test của Hermes repo, luôn nạp module deploy qua `importlib.util` để trỏ đích danh vào file trong worktree repo:
```python
import importlib.util
from pathlib import Path

REPO_SCRIPTS = Path(__file__).resolve().parent.parent / "deploy" / "hermes-home" / "scripts"
spec = importlib.util.spec_from_file_location(
    "sync_gpm_lifecycle", 
    str(REPO_SCRIPTS / "sync_gpm_lifecycle.py")
)
sgl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sgl)
```

---

## 3. Quy Tắc Đồng Bộ Staging Khi Chạy `closeout_gate.py --files`
- Khi chạy `closeout_gate.py` với tham số `--files <f1> <f2>`:
  - Nếu repo có file staged trong Git index (`git diff --cached`), script bắt buộc `set(staged) == set(targets)`.
  - Nếu có bất kỳ file nào khác bị stage dở (ví dụ các file SKILL.md, tài liệu references), gate sẽ lập tức báo lỗi và dừng:
    `Failed to extract diff: staged files [...] != --files targets [...]`
- **Cách xử lý:** 
  - Phải unstage toàn bộ các file ngoài phạm vi trước khi stage đúng tập file target `--files`.
  - Không để file vừa có thay đổi staged vừa có thay đổi unstaged (`MM`), phải `git add` trọn vẹn toàn bộ thay đổi của các target files.

---

## 4. Cạm Bẫy Truncated Diff & Chọn Model Chuẩn Trong Closeout Gate
### Hiện tượng:
- Khi diff của phiên làm việc lớn (>30 KB, gồm nhiều script và test suite), chạy `closeout_gate.py` với model mặc định `review` sẽ bị Sol Reviewer reject và trừ điểm nặng ở Finding:
  `diff bị cắt nhiều phần nên không đủ cơ sở xác minh toàn bộ nhánh xử lý...`
- Nguyên nhân: Model mặc định `review` (Sol Web) bị chặn bởi payload guard ở mức **37,952 Bytes** (tránh HTTP 413 của Nginx upstream), khiến diff bị cắt cụt.

### Giải pháp:
- Chuyển sang mô hình Claude Opus Thinking High trên pool Antigravity bằng cờ:
  `--model ag-opus-pool`
  *(Lưu ý: Tên model trong known-good list là `ag-opus-pool`, KHÔNG PHẢI `ag-opus`)*.
- Khi dùng `--model ag-opus-pool`, script sẽ tự động kích hoạt `skip_payload_guard=True`, cho phép truyền toàn bộ diff 60KB–150KB+ và test log sang reviewer mà không bị cắt xén một byte nào.

