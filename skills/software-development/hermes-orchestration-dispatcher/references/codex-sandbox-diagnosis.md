# Codex Windows Sandbox Diagnosis

## Quick check

```bash
# 1. Kiểm tra codex trong PATH có sandbox helper không
ls -la "$(dirname "$(which codex)")"/codex-windows-sandbox-setup.exe 2>&1

# 2. Tìm tất cả bản codex đã cài
find "C:/Users/$USER/AppData/Local/OpenAI/Codex/bin" -name "codex.exe" -type f
find "C:/Users/$USER/AppData/Local/Programs/OpenAI/Codex/bin" -name "codex.exe" -type f

# 3. Tìm sandbox helper trong các bản
find "C:/Users/$USER/AppData/Local/OpenAI/Codex" -name "codex-windows-sandbox-setup.exe" -type f

# 4. Đọc log sandbox gần nhất
cat "$(ls -t ~/.codex/.sandbox/sandbox.*.log | head -1)" | tail -30

# 5. Kiểm tra PATH có stale codex entries không
echo "$PATH" | tr ':' '\n' | grep -i codex
```

## Log file location

Codex ghi sandbox log vào:
```
C:\Users\<user>\.codex\.sandbox\sandbox.YYYY-MM-DD.log
```

Mỗi ngày một file. Key patterns:
- `spawning codex-windows-sandbox-setup.exe (cwd=...)` — tìm thấy helper
- `spawning C:\...\<hash>\codex-windows-sandbox-setup.exe (cwd=...)` — tìm thấy qua full path (tốt)
- `setup refresh failed ... error=program not found` — KHÔNG tìm thấy helper
- `setup binary completed` — sandbox init thành công
- `runner: unsupported protocol version 4` — version mismatch (xem bên dưới)

## Root Cause: Split Installation

Sau khi Codex auto-update (thường qua `codex update` hoặc background update), có thể tồn tại 2 thư mục bin:

| Vị trí | Vai trò | Ngày |
|--------|---------|------|
| `C:\Users\<user>\AppData\Local\Programs\OpenAI\Codex\bin\` | Trong PATH (chạy khi gõ `codex`) | Cũ hơn |
| `C:\Users\<user>\AppData\Local\OpenAI\Codex\bin\<hash>\` | Bản mới (auto-update) | Mới hơn |

Bản cũ trong PATH **không có** `codex-windows-sandbox-setup.exe` và `codex-command-runner.exe`.

### Tại sao MCP node_repl vẫn hoạt động?

Codex có 2 code path để resolve sandbox helper:
- **Exec tool** (pwsh commands): resolve từ thư mục của `codex.exe` đang chạy → thư mục bản cũ → KHÔNG TÌM THẤY
- **MCP tool** (node_repl): resolve từ runtime path đã cache → thư mục bản mới → TÌM THẤY

Log pattern xác nhận:
```
# Exec attempt → FAIL
spawning codex-windows-sandbox-setup.exe (cwd=...)
setup refresh failed ... error=program not found

# MCP attempt → SUCCESS  
spawning C:\Users\...\69066b736e1e17a4\codex-windows-sandbox-setup.exe (cwd=...)
setup binary completed
```

### Fix

Copy 2 file thiếu từ bản mới sang bản cũ:

```bash
NEW_BIN=$(find "C:/Users/$USER/AppData/Local/OpenAI/Codex/bin" -name "codex-windows-sandbox-setup.exe" -type f | head -1 | xargs dirname)
OLD_BIN=$(dirname "$(which codex)")

cp "$NEW_BIN/codex-windows-sandbox-setup.exe" "$OLD_BIN/"
cp "$NEW_BIN/codex-command-runner.exe" "$OLD_BIN/"
```

Hoặc cập nhật PATH để trỏ đến bản mới (cần admin nếu PATH system-wide).

## ⚠️ PITFALL: Protocol Version Mismatch

**Triệu chứng**: Sau khi copy sandbox files, `codex exec` thất bại với:
```
runner failed during ReadSpawnRequest: runner: unsupported protocol version 4
```

**Root cause**: `codex-command-runner.exe` và `codex.exe` khác version → protocol không tương thích. Ví dụ: codex 0.144.1 dùng protocol v3, command-runner từ bản 0.146 alpha dùng protocol v4.

**Cách xác nhận**:
```bash
# Check version của codex đang chạy
codex --version

# Check version của command-runner vừa copy
# (không có flag --version riêng, dựa vào thư mục nguồn)
ls -la "$(dirname "$(which codex)")"/codex-command-runner.exe
```

**Fix đúng**:
1. Copy `codex-windows-sandbox-setup.exe` từ bản mới (file này thường backward-compatible)
2. Copy `codex-command-runner.exe` **phải khớp version với `codex.exe`**. Nếu không có bản khớp:
   - Xóa `codex-command-runner.exe` trong thư mục cũ
   - Xóa cache `~/.codex/.sandbox-bin/codex-command-runner-*.exe` cũ
   - Để codex tự resolve command-runner từ cache có sẵn

```bash
# Clean approach: chỉ copy sandbox-setup, không copy command-runner
NEW_BIN=$(find "C:/Users/$USER/AppData/Local/OpenAI/Codex/bin" -name "codex-windows-sandbox-setup.exe" -type f | head -1 | xargs dirname)
OLD_BIN=$(dirname "$(which codex)")
cp "$NEW_BIN/codex-windows-sandbox-setup.exe" "$OLD_BIN/"
# KHÔNG copy codex-command-runner.exe nếu version khác!
```

## ⚠️ PITFALL: Cached Command-Runner

Codex cache `codex-command-runner.exe` vào `~/.codex/.sandbox-bin/` với tên có version:
```
codex-command-runner-0.141.0.exe
codex-command-runner-0.144.1.exe
codex-command-runner-0.146.0-alpha.3.1.exe
```

Khi codex khởi động, nó validate và recopy command-runner từ thư mục cạnh `codex.exe`. Nếu file đó là sai version, cache sẽ bị ghi đè bằng bản sai.

**Fix cache bẩn**:
```bash
# Xóa cache để codex tự tạo lại từ đúng source
rm ~/.codex/.sandbox-bin/codex-command-runner-*.exe
```

## ⚠️ PITFALL: Alpha Version + WindowsApps pwsh.exe

Bản Codex 0.146 alpha (và có thể các alpha khác) dùng `C:\Users\<user>\AppData\Local\Microsoft\WindowsApps\pwsh.exe` làm shell. Sandbox của bản alpha **không truy cập được** WindowsApps path, gây lỗi:
```
CreateProcessAsUserW failed: 1920 (The file cannot be accessed by the system.)
```
hoặc
```
CreateProcessAsUserW failed: 5 (Access is denied.)
```

**Fix**: Không dùng bản alpha trên Windows. Quay về bản stable (0.144.x) — bản này dùng `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe` hoặc resolve được WindowsApps pwsh qua sandbox cũ.

## Stale PATH entries

Sau auto-update, PATH có thể còn entry trỏ đến thư mục đã bị xóa:
```bash
echo "$PATH" | tr ':' '\n' | grep -i codex
# Nếu có entry trỏ đến thư mục không tồn tại → stale
```

Stale entries không gây lỗi trực tiếp nhưng có thể gây nhầm lẫn khi debug.

## Alternative: Codex Sandbox Modes

```bash
# Mode workspace-write (ghi được trong workdir + /tmp)
codex exec --sandbox workspace-write "prompt"

# Bypass hoàn toàn (DANGER — chỉ dùng trong môi trường đã sandbox sẵn)
codex exec --dangerously-bypass-approvals-and-sandbox "prompt"
```

Các mode này **vẫn cần** `codex-windows-sandbox-setup.exe` để khởi tạo ACL — nên fix installation là giải pháp triệt để nhất.
