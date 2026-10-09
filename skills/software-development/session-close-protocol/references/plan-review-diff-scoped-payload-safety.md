# Plan-Review Diff-Scoped Payload and Socket Timeout Safety

## Problem & Pitfall
When closing a session and sending the candidate diff to 9Router (`:20128`) for Gate 1 Plan-Review (`plan-review` or `plan-review-hard`):
1. **Full Repo Diff Context Exhaustion & Timeout**:
   Using `git diff <base>` across a large multi-commit range or including thousands of lines of unrelated mock/fixture boilerplate (`test_*.py` fixture files with massive XML dumps) overwhelms model context windows (100k+ tokens) or causes proxy/upstream socket timeouts (`timed out` after 60s/120s).
2. **Socket Layer Timeout Safety**:
   Python `urllib.request.urlopen` or `requests` calls without an explicit bounded socket timeout (`timeout=45` / `timeout=60`) can hang the terminal execution indefinitely if 9Router or the upstream provider stalls.

## Canonical Fix Pattern
1. **Diff-Scoped Allowlist**:
   Always scope the `git diff` to the exact modified production files, case documentation, and relevant new/modified test files:
   ```bash
   git diff <base> -- <production_files> <docs/farm-automation-cases.md> <test_files>
   ```
2. **Strict Socket Timeout**:
   Enforce `timeout=60` on the HTTP request.
3. **OmniRoute / Fallback Priority**:
   If 9Router (`:20128`) experiences high load or stalls, OmniRoute (`:20129`) provides Ordered Concurrency Spillover across accounts.

## Hard Lessons From Case 80 (Máy 34, 04/09/2026) — Truncated Payload Causes False REJECT

4. **NEVER Truncate Diff Mid-Hunk (`diff[:20000]`)**:
   A review script sliced the unified diff to the first 20000 chars to fit context. The tail hunks (idempotency `run_id` scoping, Post selector expansion `sox/soz/sp7/sh8/shd/rbp`, LIVE→ĐĂNG tab switch, `_auto_advance_verified_videos` path sync, test renames) were cut off. The reviewer then correctly reported "3/4 mục tiêu vắng mặt" + "diff truncated / syntax error" and returned `DECISION: REJECTED` three times in a row — a false rejection caused by the sender, not the code. `py_compile` passed and `git diff --stat` showed all 3 files changed, proving the code was complete.
   Rule: if `len(diff)` exceeds the model budget, DO NOT `diff[:N]`. Instead: (a) split into 2+ sequential review calls per file/hunk range, or (b) raise the budget / use a reasoning model with larger context, or (c) send `git diff --stat` + per-file diffs. Always log `Total diff len` and `@@ hunk count` before sending so truncation is detectable.
5. **Verify Reviewer's "MISSING" Claim Against Local Diff Before Accepting REJECT**:
   When a reviewer claims hunks are absent, grep the local worktree (`git diff <file> | grep -c "<symbol>"`, `grep -n "<func>" <file>`) to confirm whether the code exists locally. In Case 80 the claimed-missing symbols (`current_run_id and receipt_run_id`, ` Phát LIVE`, `view_bg2.*timeout=30`, `machine_7_account_`) were all present in the working tree — the REJECT was a payload artifact. Record this verification in the closeout report; do not start a remediation loop for a false-missing finding.
6. **9Router Timeout / HTTP 401 Token Revoked → OmniRoute Fallback Is Proven**:
   Khi `plan-review` / `plan-review-hard` qua 9Router `:20128` bị timeout (`TimeoutError` sau 45–60s) hoặc gặp lỗi HTTP 401 (`token_revoked` / `invalidated oauth token`), lập tức failover sang OmniRoute `:20129` (port 20129, lấy `OMNIROUTE_API_KEY` từ `C:/Users/Kibe/AppData/Local/hermes/.env`).
   Dùng `model: no-think/antigravity/claude-sonnet-4-6` hoặc `antigravity/claude-sonnet-4-6` hoặc `ag-claude`, cùng cấu hình `tools: []` + `tool_choice: "none"` envelope và `timeout=45`. Route này trả về kết quả `VERDICT: APPROVED/REJECTED` chuẩn xác trong vài giây mà không bị treo socket. Ghi rõ route hiệu dụng trong báo cáo chốt phiên (`OmniRoute no-think/antigravity/claude-sonnet-4-6`).

7. **CẤM Inline Bash String Interpolation (`python -c` / Heredoc) Khi Gửi Diff Lớn (2026-09-05)**:
   Khi gửi candidate diff sang 9Router/OmniRoute trong Git-Bash / MSYS trên Windows, TUYỆT ĐỐI CẤM nhúng chuỗi diff trực tiếp vào lệnh terminal `python -c "..."` hoặc bash heredoc `python << 'PYEOF'`. Bash sẽ tự động evaluate và bóc tách các ký tự `\n`, backtick (```), dấu `{diff}`, dấu nháy kép `"` hoặc `<N>` bên trong nội dung diff hoặc prompt, dẫn đến lỗi cú pháp shell (`diff: missing operand after diff`, `{diff}: command not found`) hoặc gửi payload diff rỗng khiến Plan-Review lập tức trả về `VERDICT: REJECT` giả.
   **Chuẩn bắt buộc:** Dùng tool `write_file` tạo file script Python tạm thời (ví dụ `C:/Users/Kibe/run_plan_review.py`), trong script dùng `subprocess.run(['git', 'diff', ...], capture_output=True, text=True, encoding='utf-8')` để lấy diff trực tiếp vào bộ nhớ, gửi request bằng `urllib.request` với `timeout=90`, in kết quả ra console và xóa file tạm sau khi hoàn tất.
