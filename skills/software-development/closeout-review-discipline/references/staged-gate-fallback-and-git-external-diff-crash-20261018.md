# Staged Gate Fallback & Git External Diff Environment Sanitization

## 1. Hiện tượng & Triệu chứng Lỗi
Trong môi trường Hermes Coordinator / sandbox runner trên Windows, khi tiến hành commit thay đổi:
```bash
git commit -m "..."
```
Pre-commit hook (`SELECTOR_GUARD` hoặc các hook kiểm tra layout) có thể bị crash đột ngột với thông báo:
```
error: cannot spawn : No such file or directory
fatal: external diff died, stopping at <file>
SELECTOR_GUARD REJECT: GIT_ERROR: Git diff -U0 failed for <file>
❌ COMMIT BLOCKED: Vi pham selector hoac anti-skip guard!
```

## 2. Căn nguyên Kỹ thuật
Khi Coordinator chạy lệnh qua shell MSYS / Git Bash, sandbox runner tự động inject một tập hợp biến môi trường:
- `GIT_EXTERNAL_DIFF=""` (giá trị rỗng)
- `GIT_CONFIG_PARAMETERS='core.attributesfile=/dev/null' 'diff.noprefix=false'`

Khi hook pre-commit gọi lệnh `git diff -U0 <file>`, Git phát hiện có biến `GIT_EXTERNAL_DIFF` nên cố gắng thực thi binary diff theo giá trị của biến. Vì chuỗi rỗng `""`, hệ điều hành báo lỗi không thể tạo process (`cannot spawn : No such file or directory`), dẫn tới việc commit bị chặn đứng dù code và test hoàn toàn hợp lệ!

## 3. Quy trình Khắc phục Chuẩn Mực (Staged-Gate Remediation)
1. **Tuyệt đối CẤM:**
   - Cấm dùng cờ cấm `git commit --no-verify` (vi phạm guard an toàn).
   - Cấm dùng `git -c diff.external=false` (bị Coordinator Guard chặn cờ `-c`).
   - Cấm chạy lệnh `unset GIT_EXTERNAL_DIFF` nếu shell không nằm trong allowlist.

2. **Giải pháp chuẩn qua Staged Index & Closeout Gate:**
   - Đưa các file cần thẩm định vào staging index:
     ```bash
     git add <file_1> <file_2> <file_test>
     ```
   - Chạy trực tiếp `closeout_gate.py` với base `HEAD`:
     ```bash
     python D:/Taadaa/tools/closeout_gate.py --repo "<path_to_repo>" --base HEAD --json-output
     ```
   - `closeout_gate.py` bóc tách staged diff trực tiếp bằng engine nội bộ với cờ `--no-ext-diff` chuẩn mực, chạy bộ test suite và gửi sang Sol Reviewer để thẩm định `APPROVED` mà không bị phụ thuộc vào pre-commit hook crash.
