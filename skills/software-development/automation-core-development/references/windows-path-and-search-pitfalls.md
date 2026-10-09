# Path Handling & Search Fallbacks in Taadaa Windows Environment

## Pitfall: Windows Drive Letter Path Resolution in Ripgrep / search_files
On this Windows host with git-bash / MSYS:
- The built-in `search_files` tool invokes ripgrep (`rg`) with MSYS-style path conversion (e.g. converting `D:/Taadaa/...` to `/d/Taadaa/...` or vice versa).
- When passing a full Windows path like `D:/Taadaa/automation-core/...` or `D:\Taadaa\...` directly into `search_files(path=...)`, `rg` may fail with:
  `IO error for operation on /d/Taadaa/...: The system cannot find the path specified. (os error 3)`.

## Safe Pattern & Immediate Fallback
1. **Never retry failing `search_files` multiple times** on the same path if it reports `os error 3`. This triggers the tool loop detector and burns tool iteration budget.
2. **Fallback to python or bash inspection**:
   - Use `terminal` with `python -c "..."` to read, search, or verify presence of substrings/regexes in specific files.
   - Use `patch(mode='replace', ...)` directly with forward slashes (e.g. `path="D:/Taadaa/automation-core/..."`) or native Windows slashes. The `patch` tool resolves paths correctly via Python standard file I/O.
3. **Preserve Iteration Budget**:
   - When given an explicit Patch Contract, verify the anchor strings via a quick one-line Python script or `read_file` before patching.
   - Run tests immediately via `terminal` using explicit virtualenv python paths rather than searching for test files through `search_files`.
