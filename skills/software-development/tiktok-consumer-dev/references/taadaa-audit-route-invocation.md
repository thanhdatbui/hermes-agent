# Taadaa audit-route invocation — quirks thực tế (verified 2026-08-09)

Ladder audit trước commit+push (theo `D:\Taadaa\AGENTS.md`): **OpenCode →
Command Code → fresh read-only Codex**. Claude chỉ khi user nhắc. Khi 1 route
fail → `AUDIT_ROUTE_SWITCH` + đi tiếp; tất cả fail → `AUDIT_ALL_ROUTES_FAILED`.

## 1. OpenCode — `D:\Taadaa\tools\invoke-opencode-audit.ps1`

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\tools\invoke-opencode-audit.ps1" \
  -RepoRoot "D:\Taadaa\<repo>" -Prompt "<prompt>" \
  -OutputDirectory "D:\Taadaa\<repo>\.ai-runs\audit-<topic>" -Model "opencode/deepseek-v4-flash-free"
```

- Tham số: `-RepoRoot`, `-Prompt`, `-OutputDirectory` (optional), `-Model`.
- **Quirk:** 9router (http://127.0.0.1:20128/v1) có thể sống (`/v1/models` → 200)
  nhưng route audit vẫn `NINEROUTER_NO_USABLE_VERDICT` → script tự fallback sang
  opencode CLI → nếu CLI cũng fail: `AUDIT_ALL_ROUTES_FAILED: OPENCODE_CLI_NONZERO_EXIT`.
  Kết quả này là hợp lệ để đi route kế — không retry mù.

## 2. Command Code — `D:\Taadaa\tools\invoke-command-code-9router-audit.ps1`

```bash
"C:\Users\Kibe\AppData\Local\Microsoft\WindowsApps\pwsh.exe" -NoProfile -ExecutionPolicy Bypass \
  -File "D:\Taadaa\tools\invoke-command-code-9router-audit.ps1" \
  -RepoPath "D:\Taadaa\<repo>" -Prompt "<prompt>" \
  -ContextText "$(cat 'C:\Users\Kibe\AppData\Local\Temp\audit-prompt.txt')"
```

- **BẮT BUỘC PowerShell 7** (`#requires -Version 7.0`). `powershell.exe` = 5.1 → fail
  `ScriptRequiresUnmatchedPSVersion`. `C:\Users\Kibe\.codex\shell\pwsh.exe` CŨNG là 5.1!
  **pwsh 7 thật nằm ở `C:\Users\Kibe\AppData\Local\Microsoft\WindowsApps\pwsh.exe`** (7.6.x).
- **Tham số KHÁC OpenCode:** `-RepoPath` (KHÔNG phải RepoRoot), **không có
  `-OutputDirectory`**; dùng `-ContextFile` (string[] paths) hoặc `-ContextText`
  (string nội dung prompt dài) + `-Prompt` ngắn. `-Endpoint` default
  `http://127.0.0.1:20128/v1`, `-Model` default `cmc/deepseek/deepseek-v4-flash`.
- Output JSON: `{"status": "COMMAND_CODE_RUNTIME_UNAVAILABLE", "reason": "9ROUTER_HTTP_UNAVAILABLE", ...}`
  — kể cả khi `/v1/models` ping 200; đây là lỗi 9router thật, đi route kế.

## 3. Fallback — fresh read-only Codex CLI (CODEX_FALLBACK_AUDIT)

```bash
codex exec --sandbox read-only --model "gpt-5.6-luna" --full-auto --skip-git-repo-check \
  --cd "D:\Taadaa\<repo>" "<audit prompt, kết thúc bằng VERDICT: APPROVED|MINOR_FIXES|REJECT + 1 đoạn reasoning>"
```

- **Model BẮT BUỘC đúng pin `gpt-5.6-luna`** (worker model của repo). `deepseek-v4-flash`
  qua codex local → `404: 模型 deepseek-v4-flash 不在当前 API Key 的可用模型范围内`.
- Prompt nên trỏ diff: ghi `git diff <files> > /tmp/hermes-audit-diff.txt` và bảo auditor
  đọc file (context nặng → model tự đọc file, không dán cả diff vào prompt).
- **Audit là vòng 2 chiều:** verdict `MINOR_FIXES` = phải sửa + thêm/bổ sung test rồi
  **RE-AUDIT cùng model** (fresh session) tới khi `APPROVED`. Ghi label đúng:
  `CODEX_FALLBACK_AUDIT` (không được báo fallback thành "Claude approved").

## Prompt template (đã dùng OK)

```
Audit implementation change in repo <path> (read-only review, do NOT modify files).
SCOPE: <files> (diff via git diff, attached).
CONTEXT: <vấn đề + fix + hành vi fail-closed + an toàn + thứ tự bắt buộc>.
TESTS: <số test pass + live-verify nếu có>.
VERDICT FORMAT (exactly one line at end): VERDICT: APPROVED | MINOR_FIXES | REJECT
Follow with one short paragraph of reasoning.
```
