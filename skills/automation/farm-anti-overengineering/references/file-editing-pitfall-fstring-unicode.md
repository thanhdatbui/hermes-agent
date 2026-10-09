# File Editing Pitfall: patch() + f-string + Vietnamese Unicode = Catastrophic Corruption

## Incident (11/09/2026)
Agent used `patch()` tool 10+ times consecutively on `D:/Taadaa/Tiktok_Reg/scripts/run_night_chain_pipeline.py`.
The file contained f-strings with `\n` escapes and Vietnamese diacritics (BẮT ĐẦU, CHUỖI ĐÊM).
Result: duplicate code blocks, broken string literals (`sys.stderr.write(msg + "` split across lines), 
indentation errors, file bloated from 1093→2031 lines. User was extremely frustrated.

## Root Cause
1. `patch()` uses fuzzy matching — when file has `\r\n` vs `\n` mismatch or escaped characters,
   it replaces at wrong positions
2. Each failed patch cascaded into the next, creating duplicate function bodies
3. The f-string `\n` literal was interpreted as actual newline during replacement

## Rules (Effective Immediately)
1. **1-2 line simple edit** → `patch()` is OK
2. **Edit >5 lines or replace a function** → MUST use `execute_code` with Python file I/O 
   (`open/read/write`) for precise replacement
3. **Edit main() or large function** → restore from git first (`git checkout -- file`), 
   then `execute_code` in ONE pass
4. **NEVER patch() 5+ times consecutively on same file** — if patch fails on 2nd attempt, 
   STOP patching and switch to execute_code
5. **After any multi-edit**: always run `python -m py_compile` to verify syntax before proceeding

## Recovery Pattern
```bash
git checkout -- <mangled-file>  # restore clean
# Then use execute_code with Python I/O to make ALL changes in one shot
```

## Why execute_code is safer
- Python file I/O is exact string matching (no fuzzy)
- You can read the entire file, make all replacements in memory, write once
- No cascade risk from partial/broken replacements
