# OneDrive Cloud-Only / Dehydration Failures in Cross-Machine Automation

## Problem Overview
When managing multi-machine automation (e.g. Master Kibe + Remote Admin) using OneDrive as the shared data transport:
- Excel files (`taikhoan_run_safe.xlsx`, `taikhoan_dat_v2_updated .xlsx`) generated on node B are synced to OneDrive cloud.
- When node A (Master) accesses these files, Windows Files On-Demand (Cloud-First Sync) leaves them in a dehydrated state:
  - Windows file attribute `4199968` (hex `0x401620`):
    - `0x00400000` (`FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS`)
    - `0x00001000` (`FILE_ATTRIBUTE_OFFLINE`)
    - `0x00000400` (`FILE_ATTRIBUTE_REPARSE_POINT`)
    - `0x00000200` (`FILE_ATTRIBUTE_SPARSE_FILE`)
    - `0x00000020` (`FILE_ATTRIBUTE_ARCHIVE`)

## Error Signatures

### 1. Python `open()` or `openpyxl.load_workbook()`
```python
OSError: [Errno 22] Invalid argument
# or
zipfile.BadZipFile: File is not a zip file
```

### 2. MSYS / Linux Bash (Git Bash)
```bash
head: error reading '.../taikhoan_run_safe.xlsx': Permission denied
```

### 3. PowerShell `[System.IO.File]::ReadAllBytes()`
```powershell
Exception calling "ReadAllBytes" with "1" argument(s): "The cloud file provider exited unexpectedly. (0x8007017A)"
# or ERROR_CANT_ACCESS_FILE (0x780 / 1920)
```

## Danger to Automation Loops
In batch runners like `tiktok_runner.py`:
```python
try:
    wb = openpyxl.load_workbook(safe_path, read_only=True)
    ...
except Exception as exc:
    sys.stderr.write(f"tiktok_runner: doc safe workbook {workbook_path} that bai: {exc}\n")
    return 0
```
Generic exception catching treats hydration errors as "0 accounts available".
Result: Entire fleets (e.g., all 80 machines in the Admin cluster) are silently skipped for that window with no alerts raised.

## Remediation Checklist
1. **Force local hydration on Windows**:
   ```cmd
   attrib -u +p "D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx"
   attrib -u +p /s /d "D:\OneDrive\TaadaaData\*.*"
   ```
2. **Direct Cross-Host SCP Fallback**:
   If the local OneDrive sync engine is unresponsive or delayed:
   ```bash
   scp admin-farm:D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx
   ```
3. **Runner Preflight Hydration Check**:
   Before reading workbooks in cron jobs:
   ```python
   def ensure_file_hydrated(path: Path) -> bool:
       try:
           with open(path, "rb") as f:
               f.read(10)
           return True
       except OSError:
           # Attempt hydration via attrib or fallback copy
           return False
   ```
