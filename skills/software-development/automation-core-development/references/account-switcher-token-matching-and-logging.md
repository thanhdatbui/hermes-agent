# Account Switcher Token Matching, Alias Loading, and Logging Invariants

## 1. Centralized DAT Workbook Import
- Do NOT hardcode file paths like `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx` in `automation_core/tiktok/account_switcher.py` or other submodules.
- Import `DEFAULT_DAT_WORKBOOK` from `automation_core.tiktok.account_recovery`:
  ```python
  from automation_core.tiktok.account_recovery import DEFAULT_DAT_WORKBOOK
  ```
- Always check `if dat_path and dat_path.is_file():` before loading with `openpyxl.load_workbook(..., read_only=True)`.

## 2. Token Matching Invariants (`_clean_alpha_tokens`)
- Clean alpha tokens should enforce minimum token length >= 3:
  ```python
  def _clean_alpha_tokens(s: str) -> list[str]:
      import unicodedata
      norm = unicodedata.normalize("NFKD", str(s or ""))
      clean = "".join(c for c in norm if not unicodedata.combining(c))
      return [p for p in re.split(r"[^a-zA-Z]+", clean.lower()) if len(p) >= 3]
  ```
- Filtering tokens with `len(p) >= 3` prevents false-positive fuzzy matches on common short words/particles (e.g. `an`, `to`, `la`, `le`).
- Require all tokens of length >= 3 from the display name to be present in target email alias or handle.

## 3. Module-Level Import Pitfall with Logging
- When replacing bare `except Exception: pass` with `logging.getLogger(__name__).debug(...)` in `account_switcher.py`, always check whether `logging` is imported at module level.
- Historically, `account_switcher.py` did NOT import `logging`. Adding `logging.getLogger(...)` inside an exception handler without `import logging` causes an uncaught `NameError: name 'logging' is not defined` whenever an exception is actually thrown.

## 4. Windows CRLF vs LF Replacement Pitfalls
- Files in `automation-core` on Windows are committed with CRLF line endings.
- Running inline Python script replacements like `assert old_block in text` from Git Bash can fail if Python literal triple-quoted strings use `\n` while the file contains `\r\n`.
- Handle newlines consistently: normalize `text = text.replace('\r\n', '\n')` before matching or write a CRLF-aware replacement helper.
