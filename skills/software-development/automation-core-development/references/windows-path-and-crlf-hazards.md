# Windows Path and CRLF Hazards in automation-core Development

## 1. Search Tool Drive Paths vs. MSYS Bash Paths
- In MSYS bash (Git Bash), POSIX paths like `/d/Taadaa/...` work with shell builtins, `python`, `grep`, `file`, etc.
- However, native Windows binaries and tools like `search_files` (ripgrep) will fail with OS error 3 (`The system cannot find the path specified`) if fed `/d/...` paths.
- Always supply `D:\Taadaa\...` or standard Windows paths when using native agent file search tools (`search_files`, `read_file`). Note that `search_files` internally normalizes `D:/...` to `/d/...` on this host and still triggers ripgrep OS error 3; use `grep -rn` via `terminal` instead.

## 2. CRLF Preservation and Patch Tool Guard
- All source files under `D:\Taadaa\automation-core\src` use CRLF (`\r\n`) line endings.
- When patching or modifying, ensure line endings remain consistent to avoid git diff pollution or fuzzy matching failures in automated patch tooling.
- If files are restored or touched via git (`git checkout`, `git restore`), always call `read_file` immediately before `patch` to refresh the session file cache and avoid `was modified since you last read it on disk (external edit or unrecorded writer)` warnings.
- Always verify with `file <path>` or run git diff check after editing.
