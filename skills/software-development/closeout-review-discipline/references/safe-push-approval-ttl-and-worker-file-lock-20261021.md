# Safe Push Approval Audit TTL & Worker Single-File Lock Enforcement (2026-10-21)

## 1. Safe Push Approval Audit TTL Trap (1800s / 30m)
### Triệu chứng & Mã lỗi
Khi gọi `python D:/Taadaa/tools/safe_push.py <repo> origin master` sau khi đã vượt qua `closeout_gate.py` với điểm cao (ví dụ: 88/100 STRICT_APPROVED):
```text
safe_push error: UnsafePushError('BLOCKED_GATE_NOT_APPROVED: Repository ... has no valid APPROVED closeout audit for HEAD (...). Must pass closeout_gate.py or auto_closeout.py before push.')
```

### Cơ chế & Nguyên nhân gốc
Trong `D:/Taadaa/tools/safe_push.py`:
```python
def _verify_closeout_gate_approval(repo_path: str, max_age_seconds: int = 1800) -> None:
    ...
    now_ts = datetime.now(timezone.utc).timestamp()
    ...
    if now_ts - rec_ts > max_age_seconds:
        break
```
Khác với `canary_runner` hay `done_gate` (TTL 7200s = 2h), `safe_push.py` khống chế bản ghi `APPROVED` trong `D:/Taadaa/logs/gate_audit.jsonl` có TTL tối đa chỉ **1800 giây (30 phút)**.
Nếu Coordinator sau khi pass gate còn thực hiện thêm canary test, kiểm tra ADB hiện trường, hoặc điều tra các issue phụ kéo dài quá 30 phút (`now_ts - rec_ts > 1800s`), bản ghi approval bị coi là hết hạn (expired) dù commit SHA ở `HEAD` khớp 100% với audit binding.

### Quy tắc xử lý chuẩn
Khi gặp lỗi `BLOCKED_GATE_NOT_APPROVED` trên commit đã từng pass gate:
1. Đối soát `gate_audit.jsonl`: kiểm tra `diff = now_ts - rec_ts`. Nếu `diff > 1800s`, xác nhận dính bẫy TTL.
2. Chạy lại `closeout_gate.py` với commit hiện tại:
   `python D:/Taadaa/tools/closeout_gate.py --repo <repo> --base origin/master --json-output`
3. Vì code và test đã chuẩn hóa và pass từ trước, gate sẽ pass ngay và ghi nhận entry `APPROVED` mới vào `gate_audit.jsonl`.
4. Gọi `safe_push.py` ngay sau đó (trong cửa sổ 30 phút).

---

## 2. Dispatch Worker `--file` Tool Lock Boundary Trap
### Triệu chứng
Khi Coordinator dispatch:
`python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> --file tests/test_A.py "Sửa tests/test_A.py và tests/test_B.py..."`
Worker hoàn thành exit code 0 nhưng `git diff --stat` chỉ thấy thay đổi trên `test_A.py`. `test_B.py` giữ nguyên không đổi.
Worker tự báo cáo: `This worker is limited to the single named target file, so that edit needs a separate run.`

### Cơ chế & Invariant
`dispatch_worker.py` thiết lập tool lock cứng (`tool_lock: locked`) theo giá trị `--file`. Worker subagent (Claude Haiku 5.5 CLI) tuân thủ nghiêm ngặt chỉ được phép sửa đúng file được chỉ định để ngăn ngừa scope creep và ô nhiễm diff.

### Quy tắc xử lý chuẩn
- Khi cần sửa nhiều file (ví dụ cặp file implementation + test, hoặc 2 file tests khác nhau): BẮT BUỘC tách thành các lượt dispatch độc lập, mỗi lượt gán đúng 1 `--file`.
- Coordinator BẮT BUỘC kiểm tra `git diff --stat` và `git diff --name-only` sau mỗi lượt worker để xác thực thay đổi thực tế trên đĩa trước khi nghiệm thu.
