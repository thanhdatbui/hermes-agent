# Windows Path Escaping and Raw Strings Pitfall

## Symptom
When hardcoding Windows paths containing backslashes in Python scripts or regex replacements, escape sequences like `\t`, `\n`, `\r`, or `\b` can be inadvertently interpreted by Python:
- Example: `dat_path = Path("D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx")`
- `\t` in `\taikhoan` becomes a literal tab character (`\x09`), transforming the filename into `kibe\taikhoan_dat_v2_updated .xlsx` and causing file lookups (`Path.is_file()`) to silently return `False`.

## Rule & Prevention
1. **Always Use Canonical Forward Slashes**:
   `pathlib.Path` handles forward slashes seamlessly on Windows:
   ```python
   dat_path = Path("D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx")
   ```
   This prevents any string escaping, shell translation, or regex replacement bugs across Windows, MSYS bash, and Git.

2. **Caution with In-File Replacement Scripts**:
   When writing regex or string replacement scripts to patch files containing backslash escape sequences, standard string matching may fail to match if one side has evaluated `\t` to a tab and the other has not. Prefer targeted line iteration or matching the invariant substring (e.g. `taikhoan_dat_v2_updated`).
