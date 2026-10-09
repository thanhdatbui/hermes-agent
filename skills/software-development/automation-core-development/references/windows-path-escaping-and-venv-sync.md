# Windows Path Escaping & Venv Sync Guidelines for Automation-Core

## 1. Windows Path Backslash Escaping Hazard
When embedding file paths (especially paths into user directories or OneDrive such as `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`) inside code patches or dynamic scripts:
- **Hazard**: Sequences like `\t` (e.g. in `\taikhoan`) or `\u`, `\n`, `\r` can be evaluated as escape characters (e.g., `\t` becomes tab `0x09`), causing `Path.is_file()` or file loading functions to silently fail.
- **Rule**:
  - Always use forward slashes in hardcoded/fallback paths in Python code:
    ```python
    dat_path = Path("D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx")
    ```
  - If backslashes must be used in a string literal, double-escape (`\\\\`) or ensure raw string literals (`r"..."`) are not evaluated through an intermediate `replace` / string-formatting step that strips the raw prefix.

## 2. Testing and Venv Sync Workflow
When updating `automation_core` components (such as `account_switcher.py`):
1. **Run Unit Tests**:
   ```bash
   python -m pytest D:/Taadaa/automation-core/tests/test_account_switcher_preconfirmed.py
   ```
2. **Sync to Shared Python Environment**:
   The shared runtime environment at `/d/Taadaa/python-envs/automation/Lib/site-packages/automation_core/` must be synchronized after changes:
   ```bash
   cp -rf D:/Taadaa/automation-core/src/automation_core/* /d/Taadaa/python-envs/automation/Lib/site-packages/automation_core/
   ```
3. **Live Import & Invariant Verification**:
   Execute a one-line assertion directly from python without modifying test fixtures:
   ```bash
   python -c "from automation_core.tiktok.account_switcher import matches_switcher_identity; assert matches_switcher_identity('Anh Hoang', 'hong.bo.anh83') is True"
   ```
   Verify that caches (such as `_DAT_WORKBOOK_ALIAS_CACHE`) populate with positive length and correct mappings.
