# AG Audit trực tiếp qua 9router (thay wrapper — 2026-08-10)

Pipeline chuẩn thay thế `invoke-ag-audit.ps1` (treo `Invoke-RestMethod` trên PowerShell 5.1: log 0 bytes, process sống quá cả `-TimeoutSeconds`, trong khi curl/python cùng endpoint xong 4–5s → timeout wrapper không trigger, đừng đợi, kill sau 3 quan sát 30s).

## Scripts (đã smoke-test)

| File | Vai trò |
|---|---|
| `D:/Taadaa/reports/ag-audit/ag_audit_direct.py` (cũng copy ở `scripts/ag-audit-direct.py` trong skill) | POST `/v1/chat/completions` tới `http://127.0.0.1:20128`, key `NINEROUTER_API_KEY`, body: model + `reasoning_effort: high` + `max_tokens: 6000` + `stream: false` + **`tools: [], "tool_choice": "none"`** (BẮT BUỘC). In `AG_AUDIT_ELAPSED`, content, `AG_AUDIT_VERDICT` (parse dòng đầu non-empty) |
| `D:/Taadaa/reports/ag-audit/run-ag-audit.sh` | 1 lệnh chuẩn: `bash run-ag-audit.sh <repo> <commit> [model] [timeout]`. Tự `git show <commit>` nhúng toàn diff vào prompt giữa `=== BEGIN/END DIFF ===` + boilerplate (verdict dòng đầu, CẤM suy đoán "nếu..."), lưu prompt/log/response theo stamp `audit-<commit>-<ts>-*` |

Artifact mẫu: `D:/Taadaa/reports/ag-audit/audit-e89ffdd-20260810-201939-{prompt,log,response}.txt`.

## Model behavior qua OpenAI-compatible API KHÔNG có tool registry

- **AG Claude (ag/claude-sonnet-4-6, ag/claude-opus-4-6-thinking) + GPT (v4-pro) + họ hàng agentic-tuned: tự phát minh `<tool_call>` giả + hallucinate** khi prompt gợi ý hành động ("chạy git show", "đọc file"). Hit thật: opus v1 viết `<tool_call>{"name":"terminal"...}` rồi **bịa cả test file không tồn tại** trong repo; sonnet trả REJECT với findings speculative "Nếu code dùng falsy check..." không locator thật.
- **Claude CLI (`claude -p` + `--allowedTools`): KHÔNG bị** — có tool thật, đọc file thật.
- **Phòng (2 mảnh, thiếu 1 là hỏng):** (1) `"tools": [], "tool_choice": "none"` trong body; (2) NHÚNG diff/context inline vào prompt — auditor qua API không đọc được repo.
- Vòng đầu UNPARSEABLE vì thiếu 1 trong 2 mảnh → retry với prompt v2, không coi là fail upstream.

## Verdict parse & đối chiếu

- Verdict = dòng đầu non-empty của content (`APPROVED|MINOR_FIXES|REJECT`); regex wrapper cho phép prefix `VERDICT:`.
- Findings hypothetical ("Nếu.../Cần xác nhận..."), không locator file:dòng thật → KHÔNG dispatch worker fix. Đối chiếu với source thật (đọc code + test hiện có) trước. Case study: sonnet REJECT 9 MAJOR → đối chiếu = 0 MAJOR thật (gate fail-closed đóng ở dòng khác, test đã cover; atomic write transaction có sẵn).
- MINOR thật (locator hợp lệ) → fix + test + re-audit. Loop hoàn chỉnh session 2026-08-10: e89ffdd MINOR_FIXES (2 MINOR: trailing newline, continuation prose fail-open) → 2fed56c MINOR_FIXES (1 MINOR style) → ee48746 APPROVED. Opus 15–35s/lượt.
- Opus có thể tự rút lại finding trong cùng response ("→ Rút lại: không phải MAJOR") — đọc hết findings trước khi kết luận.

## Pitfalls hỗ trợ pipeline

- **PYTHONPATH:** `PYTHONPATH='D:/Taadaa/<repo>/src'` (forward-slash). `/d/Taadaa/...` bị MSYS convert thành `D:\d\Taadaa\...` → pytest im lặng import nhầm bản site-packages cũ → fail/pass oan.
- **JSON escape heredoc:** qua terminal tool, `\\n` → shell `\n` → python source `\n` = newline thật (SyntaxError khi ghi file). Ghi literal `\n` vào file: `chr(92) + "n"` (an toàn tuyệt đối) hoặc 4 backslash. Grep file sau khi ghi trước khi pytest.
- **EOL CRLF:** file CRLF (AGENTS.md, tools/check_ui_compatibility.py...) — append trailing newline bằng `open(f,'wb').write(b + b"\r\n")`; python string replace phải thử variant `old.replace("\n","\r\n")`.
- **Test fail ngoài scope:** verify pre-existing bằng `git stash -q` → chạy lại → vẫn fail = pre-existing → `git stash pop -q` (hit thật: test_startup.py).
- **Skill junction:** skill này là junction vào `D:/Taadaa/Hermes/skills/` — patch skill = sửa file trong repo; push qua remote `fork` (origin = NousResearch upstream không có quyền); cron `sync-hermes-skills-to-git` (30') tự commit+push staged.