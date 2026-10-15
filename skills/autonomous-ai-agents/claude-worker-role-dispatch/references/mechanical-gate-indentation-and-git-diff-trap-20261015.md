# Mechanical Gate Indentation Bug, Regex Boundary Trap, and GIT_EXTERNAL_DIFF (15/10/2026)

## 1. Dead Code Indentation Trap in `guard_dispatch_contract.py`

### Triệu chứng & Vấn đề
Khi chèn logic HARD GATE #3 MECHANICAL BLOCK để chặn `delegate_task` cho task sửa code, đoạn code kiểm tra `has_override` bị thụt lề 4 spaces ngay sau dòng comment:
```python
# ==========================================
# 3. NHÁNH EDIT CODE (Code Surgery - BẮT BUỘC SOL PLAN / T0 BYPASS)
# ==========================================
    has_override = bool(re.search(...))
    if not has_override:
        ...
        sys.exit(0)
```
### Nguyên nhân gốc rễ
Trong Python, dòng comment `#` không tạo ra scope hay khối thụt lề mới. Do đó, 4 spaces thụt lề khiến Python gộp đoạn block này vào thân của khối `if` phía trước (`if not is_code_edit and not has_file_content:`) ngay sau câu lệnh `sys.exit(0)`.
Hậu quả: Block trở thành **dead code** hoàn toàn. Python `py_compile` vẫn hợp lệ nhưng nhánh EDIT CODE không bao giờ chạm tới block này. Khi test chạy, `test_code_edit_mechanical_block_without_override` thất bại vì hook trả về `None` thay vì `action: block`.

### Cách sửa chuẩn xác
Dedent toàn bộ block về cột 0 (root level), đặt ngay trước `if not file_match:` của Nhánh 3.

---

## 2. Regex Word Boundary Decay Trap (`\b` -> `\x08`)

### Triệu chứng
Khi chèn snippet code bằng Python string thông thường (`'''...'''`), chuỗi `\b` bị Python parser diễn giải thành ký tự ASCII Backspace (`\x08`), biến regex thành:
`r'\x08(?:ALLOW_SUBAGENT_CODE_EDIT|...)\x08'`
Hậu quả: Regex không bao giờ khớp với cờ override thực tế như `WORKER_CLI_EXHAUSTED`, khiến gate chặn cả các trường hợp có cờ override hợp lệ.

### Cách sửa chuẩn xác
BẮT BUỘC sử dụng raw string: `r'''...'''` hoặc `r'...'` cho mọi chuỗi chứa regex word boundary.

---

## 3. GIT_EXTERNAL_DIFF Environment Variable Trap

### Triệu chứng
Trên host Windows, biến môi trường `GIT_EXTERNAL_DIFF` bị gán giá trị rỗng `""`. Khi các script Python gọi `git diff` qua `subprocess.run`:
```
error: cannot spawn : No such file or directory
fatal: external diff died, stopping at <file>
```
Git cố gắng thực thi một binary rỗng `""` làm external diff engine và văng lỗi fatal.

### Cách sửa chuẩn xác
Trong mọi script Python gọi `git diff`, luôn làm sạch môi trường:
```python
git_env = os.environ.copy()
git_env.pop('GIT_EXTERNAL_DIFF', None)
subprocess.run(['git', '-C', repo, 'diff', '--no-ext-diff', ...], env=git_env)
```
Hoặc truyền cờ `--no-ext-diff` ngay sau lệnh `diff`.

---

## 4. Bằng chứng kiểm chứng thực tế (Verification Evidence)
Test suite `tests/test_guard_dispatch_contract.py` đạt **7/7 PASSED in 1.54s**:
- `test_read_only_with_code_path_goes_investigate`: PASSED
- `test_read_only_budget_above_five_blocked`: PASSED
- `test_code_edit_without_old_string_blocked`: PASSED
- `test_old_new_string_routes_to_edit`: PASSED
- `test_dispatch_audit_telemetry`: PASSED
- `test_code_edit_mechanical_block_without_override`: PASSED
- `test_code_edit_mechanical_block_with_override`: PASSED
