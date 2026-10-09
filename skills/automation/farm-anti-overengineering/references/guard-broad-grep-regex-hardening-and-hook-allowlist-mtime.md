# Hard Gate #4: Guard Broad Grep Regex Hardening & Hook Allowlist Integrity (24/09/2026)

## 1. Lỗ hổng Regex trong Hard Gate Hook #4 (`guard_broad_grep.py`)

Hook `D:/Taadaa/tools/hooks/guard_broad_grep.py` chặn các lệnh quét đĩa diện rộng (recursive grep, rg, find, os.walk...) vào ổ D, thư mục `D:/Taadaa` và các thư mục runtime nhạy cảm.

### Hai lỗ hổng nguy hiểm đã phát hiện và phân tích:
1. **Lọt lệnh `os.walk` do neo kết thúc `$`**:
   - Ban đầu `DANGEROUS_TARGETS` định nghĩa: `r"D:[\\/]?$"` và `r"D:[\\/]Taadaa[\\/]?$"`.
   - Ký tự `$` buộc target phải nằm ở cuối toàn bộ chuỗi câu lệnh.
   - Khi lệnh là `python3 -c "import os; for r, d, f in os.walk('D:/Taadaa'): pass"` hoặc `python -c "import os; os.walk('D:/')"`, phía sau đường dẫn còn có dấu nháy đơn (`'`), nháy kép (`"`), hoặc dấu ngoặc (`)`), khiến regex không match và bỏ lọt lệnh quét đĩa nghiêm trọng.
   - **Khắc phục**: Thay neo `$` bằng ranh giới kết thúc an toàn: `(?:['\"`\s\)]|$)`.

2. **Lọt lệnh `grep -rn` do ranh giới từ `\b` sai vị trí**:
   - Regex kiểm tra fallback cho broad grep ban đầu:
     ```python
     re.search(r"\b(?:grep\s+(?:-[a-zA-Z]*[rR]|--recursive)|rg)\b", cmd)
     ```
   - Ranh giới từ `\b` nằm ngoài group yêu cầu word boundary ngay sau ký tự kết thúc khớp. Đối với `grep -rn`, phần `-[a-zA-Z]*[rR]` khớp với `-r`, nhưng ký tự kế tiếp là `n` (thuộc tập `\w`), khiến `\b` không match. Do đó `grep -rn` bị lọt hoàn toàn!
   - **Khắc phục**: Bỏ `\b` phụ thuộc sau cờ recursive:
     ```python
     is_broad_grep = (
         re.search(r"\bgrep\s+-[a-zA-Z]*[rR]", cmd)
         or re.search(r"\bgrep\s+--recursive", cmd)
         or re.search(r"\brg\b", cmd)
     ) and ("--exclude" not in cmd and "--include" not in cmd)
     ```

### Bộ quy tắc chuẩn cho `guard_broad_grep.py`:
```python
DANGEROUS_TARGETS = [
    r"D:[\\/](?:['\"`\s\)]|$)",
    r"D:[\\/]Taadaa(?:[\\/]|['\"`\s\)]|$)",
    r"(?:['\"`\s\(]|^)[a-zA-Z]:[\\/]?(?:['\"`\s\)]|$)",
    r"(?:['\"`\s\(]|^)[\\/](?:['\"`\s\)]|$)",
    r"D:[\\/]CodexRuntime",
    r"[\\/]\.ai-runs",
    r"runtime[\\/]kibe",
    r"python-envs",
    r"BACKUP_ALL",
    r"node_modules",
    r"__pycache__",
]

SCAN_TOOLS = [
    r"\bgrep\s+-[a-zA-Z]*[rR]",
    r"\bgrep\s+--recursive",
    r"\brg\b",
    r"\bfind\s+[\'\"]?(?:D:[\\/]|D:[\\/]Taadaa|\.)",
    r"\bfindstr\s+/[sS]",
    r"\bSelect-String\s+.*-Recurse",
    r"\b(?:Get-ChildItem|gci|ls)\s+.*-(?:Recurse|[rR])\b",
    r"\bdir\s+/[sS]",
    r"\btree\s+/[fF]",
    r"os\.walk",
    r"\.rglob\(",
    r"glob\.glob\(.*recursive\s*=\s*True",
]
```

### Bộ test benchmark chuẩn:
- `grep -rn count_active_locks D:/Taadaa/Hermes` -> **BLOCK**
- `python3 -c "import os; for r, d, f in os.walk('D:/Taadaa'): pass"` -> **BLOCK**
- `python -c "import os; os.walk('D:/')"` -> **BLOCK**
- `grep -n 'PATTERN' D:/Taadaa/file.py` -> **PASS** (Single-file grep hợp lệ O(1))

---

## 3. Nâng cấp Telemetry chuẩn Reviewer & Xử lý False Positive (24/09/2026 update)

### A. Chuẩn hóa Schema Telemetry JSON khi Gate Block
Khi kích hoạt block, hook không in plain-text thô mà phải emit JSON có cấu trúc để các harness/supervisor/logging phân tích được:
```python
def block(message, tool_name="terminal"):
    payload = {
        "action": "block",
        "rule_id": "HARD_GATE_4_BROAD_SCAN",
        "severity": "HIGH",
        "tool": tool_name,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "message": message,
    }
    print(json.dumps(payload, ensure_ascii=False))
    sys.exit(0)
```

### B. Fix False Positive: Thứ tự ưu tiên `is_single_file_target`
- **Vấn đề**: Các lệnh như `rg pattern D:/Taadaa/Hermes/config.py` hay `grep -n count_active_locks D:/Taadaa/Hermes/config.py` có chứa chuỗi `d:/taadaa`. Nếu hàm `contains_dangerous_root(cmd)` chạy trước, lệnh single-file này sẽ bị block nhầm (false positive).
- **Giải pháp**: Kiểm tra `is_single_file_target(cmd)` và thoát ngay (`sys.exit(0)`) TRƯỚC khi gọi `contains_dangerous_root(cmd)`.
  ```python
  def is_single_file_target(cmd: str) -> bool:
      tokens = cmd.strip().split()
      if not tokens:
          return False
      last = tokens[-1].strip("''\"\"")
      has_ext = bool(re.search(r"\.[a-zA-Z0-9_-]{1,10}$", last))
      has_wildcard = any(w in cmd for w in ["*", "?", ".."])
      return has_ext and not has_wildcard
  ```

### C. Fix False Positive: Substring Match trên `/` và `//`
- **Vấn đề**: Nếu đưa `/` và `//` vào `DANGEROUS_ROOTS` và dùng `root in normalized`, MỌI đường dẫn có chứa dấu gạch chéo `/` (ví dụ `C:/Users/Kibe/my_project`) đều bị nhận diện nhầm là root nguy hiểm!
- **Giải pháp**: Phân tách kiểm tra `/` và `//` thành boundary regex hoặc exact match, không dùng substring `in`:
  ```python
  def contains_dangerous_root(cmd: str) -> bool:
      normalized = normalize(cmd)
      for root in DANGEROUS_ROOTS:
          if root in ["/", "//"]:
              if normalized in ["/", "//"] or re.search(r"(?:^|[\s\"'])//?(?:[\s\"']|$)", normalized):
                  return True
          elif root in normalized:
              return True
      return False
  ```

### D. Mở rộng Test Suite `test_guard_broad_grep.py` đạt chuẩn Reviewer
Bộ 6 test cases chuẩn trong `D:/Taadaa/tools/tests/test_guard_broad_grep.py`:
1. `test_guard_blocks_recursive_grep`: Khóa grep -rn, grep -R, grep --recursive.
2. `test_guard_blocks_broad_rg`: Khóa rg không chỉ định file, rg quét thư mục root.
3. `test_guard_allows_single_file_grep_and_rg`: Cho phép grep -n và rg trên 1 file cụ thể kể cả khi path nằm trong D:/Taadaa.
4. `test_guard_blocks_python_walkers`: Khóa os.walk, Path.rglob, glob(recursive=True).
5. `test_guard_blocks_search_files_on_dangerous_roots`: Khóa search_files content trên D:/Taadaa.
6. `test_guard_allows_search_files_on_safe_subfolder`: Cho phép search_files content trên subfolder người dùng an toàn (`C:/Users/Kibe/...`).

---

## 2. Quản lý tính toàn vẹn Hook qua `shell-hooks-allowlist.json`

Hermes Agent bảo vệ an toàn cho hệ thống bằng cơ chế hash/mtime allowlist:
- File allowlist: `C:/Users/Kibe/AppData/Local/hermes/shell-hooks-allowlist.json`
- Cấu trúc:
  ```json
  {
    "approvals": [
      {
        "approved_at": "...",
        "command": "python D:/Taadaa/tools/hooks/guard_broad_grep.py",
        "event": "pre_tool_call",
        "script_mtime_at_approval": "2026-09-17T14:18:31.226613Z"
      }
    ]
  }
  ```

### Quy tắc bất biến khi sửa bất kỳ hook nào:
1. Khi file hook (`.py`) được chỉnh sửa, timestamp `mtime` của file trên đĩa sẽ thay đổi.
2. Nếu `script_mtime_at_approval` không khớp với `mtime` thực tế, Hermes sẽ chặn thực thi hoặc chuyển sang chế độ hỏi xác nhận thủ công (interactive approval prompt), làm gián đoạn các workflow tự động.
3. **Quy trình chuẩn**:
   - Sau khi vá hook file, lấy mtime UTC của file (`stat.st_mtime` định dạng `%Y-%m-%dT%H:%M:%S.%fZ`).
   - Cập nhật trường `script_mtime_at_approval` trong `C:/Users/Kibe/AppData/Local/hermes/shell-hooks-allowlist.json`.
   - Chạy `hermes hooks doctor` để đảm bảo tất cả hook đều ở trạng thái `✓ allowlisted`.
