# Foreground Timeout Clamp Allowlist & Windows cp1252 Stdout Encoding Fix

## 1. Bối Cảnh & Hiện Tượng Sự Cố (Root Cause Analysis)

Trong các phiên làm việc điều phối tự động của Hermes Coordinator, hai lỗi kiến trúc ngầm đã cộng hưởng tạo ra tình trạng tê liệt toàn diện (freeze / deadlock / defensive paralysis):

### Lỗi 1: Foreground Timeout 60s Chặn Đứng Worker Dispatcher 300s
- **Cơ chế cũ:** Hook kiểm soát lệnh quét đĩa áp đặt một trần timeout cứng `timeout <= 60s` cho toàn bộ các lệnh terminal chạy ở foreground. Lệnh nào không có timeout hoặc timeout > 60s đều bị chặn với mã `GUARD_FOREGROUND_TIMEOUT_EXCEEDED`.
- **Mâu thuẫn kiến trúc:** Các công cụ điều phối worker (`dispatch_worker.py`, `sol_worker.py`, `ag_cli.py`, `sol_repair.py`, `claude_worker.py`), công cụ thẩm định chốt phiên (`closeout_gate.py`), và test suite lớn (`pytest`) bắt buộc cần thời gian từ 120s đến 300s để hoàn thành chu trình ReAct hoặc test toàn diện.
- **Hậu quả:** Ép Coordinator sang chạy background (`background=True`). Nhưng background lại bị `guard_cronjob_safety.py` chặn cửa sổ console (`CONSOLE_WINDOW_BLOCKED`, yêu cầu `pythonw`), trong khi `pythonw` không nằm trong allowlist của Coordinator Guard (`DEFAULT-DENY`). Coordinator rơi vào ngõ cụt 100%, dẫn tới hành vi lách luật gọi Claude Sonnet làm việc vặt hoặc bỏ cuộc, khóc lóc.

### Lỗi 2: Bug Sập Thầm Lặng Do Windows cp1252 Pipe (UnicodeEncodeError)
- **Cơ chế cũ:** Trên Windows, tiến trình con (subprocess hook) thừa hưởng stdout encoding từ console của tiến trình cha (mặc định là mã trang Windows `cp1252`).
- **Hiện tượng:** Khi hàm `block()` hoặc `deny()` của hook in JSON phản hồi chứa các thông báo lỗi có dấu tiếng Việt (UTF-8) ra stdout, Python ném ngoại lệ `UnicodeEncodeError: 'charmap' codec can't encode characters`.
- **Hậu quả:** Hook bị sập (crash) bất thường, không trả được payload JSON chuẩn cho runtime engine của Hermes. Runtime coi như lệnh terminal bị lỗi không xác định, gây ra hiện tượng "treo câm" (silent freeze) khiến Coordinator tưởng tiến trình bị đứng.

---

## 2. Giải Pháp Khắc Phục Chuẩn (Standard Mechanical Pattern)

### 2.1. Ép Chuẩn UTF-8 Cho Pipe Stdout
Trước khi gọi `print(json.dumps(...))` trong bất kỳ hàm `block()`, `deny()`, hoặc `main()` nào của hook:
```python
import sys

# Pipe của tiến trình cha có thể là cp1252 trên Windows; ép UTF-8 để không sập khi in tiếng Việt.
sys.stdout.reconfigure(encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False))
sys.exit(0)
```

### 2.2. Danh Sách Trắng Công Cụ Điều Phối (Long-Running Allowlist)
Thay vì cào bằng 60s, hook phân loại lệnh terminal dựa trên danh sách công cụ điều phối và kiểm thử hợp pháp:
```python
import re

LONG_RUNNING_ALLOWLIST = (
    "dispatch_worker.py",
    "closeout_gate.py",
    "pytest",
    "sol_worker.py",
    "ag_cli.py",
    "sol_repair.py",
    "claude_worker.py",
)

# Khớp theo từ nguyên vẹn (word-boundary), chống bypass bằng tiền tố/hậu tố giả mạo
is_long_running = any(
    re.search(rf"(?<![\w.-]){re.escape(tool)}(?![\w.-])", cmd)
    for tool in LONG_RUNNING_ALLOWLIST
)

max_allowed = 360 if is_long_running else 60

if to is None:
    block(
        "GUARD_FOREGROUND_TIMEOUT_MISSING",
        f"Lệnh terminal foreground thiếu timeout! Bắt buộc timeout <= {max_allowed}s hoặc chạy background=True.",
        tool_name=tool_name,
        target=cmd,
    )
elif to_val > max_allowed:
    block(
        "GUARD_FOREGROUND_TIMEOUT_EXCEEDED",
        f"Lệnh terminal foreground có timeout={to}s > {max_allowed}s! Hãy hạ timeout <= {max_allowed}s hoặc dùng background=True.",
        tool_name=tool_name,
        target=cmd,
    )
```

---

## 3. Bộ Kiểm Thử Xác Minh (Verification Suite)

Bắt buộc kiểm thử 3 kịch bản phân nhánh:
1. **Tool trong allowlist với timeout 300s:** `python dispatch_worker.py --scope x`, `timeout=300` $\rightarrow$ `ALLOW` (`{}`).
2. **Tool trong allowlist vượt trần 360s:** `python dispatch_worker.py --scope x`, `timeout=400` $\rightarrow$ `BLOCK` (`GUARD_FOREGROUND_TIMEOUT_EXCEEDED`).
3. **Lệnh thường vượt trần 60s:** `echo safe`, `timeout=180` $\rightarrow$ `BLOCK` (`GUARD_FOREGROUND_TIMEOUT_EXCEEDED`).
4. **Tiếng Việt trong message block:** Đảm bảo khi block một lệnh vi phạm, hook trả về chuỗi JSON chứa tiếng Việt đầy đủ mà không bị crash mã trang `cp1252`.
