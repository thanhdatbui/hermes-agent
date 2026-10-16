# Dual-Farm Rolling Rename & Cross-Host Admin Dispatch Architecture

## Overview

When rolling out account profile optimizations (such as natural nickname / display name renames) across a dual-host farm infrastructure (Kibe PC for Machines 1–80 and Admin PC for Machines 201–280), automation must address network separation, remote file hydration, CLI argument limits, and state isolation.

---

## 1. Dual-Host Architecture

| Cluster | Machines | Host | Primary Data Source | State & Artifacts Path |
|---|---|---|---|---|
| **Kibe Farm** | 1 – 80 | Local (Kibe PC) | `taikhoan_run_safe_combined.xlsx` / `tiktok_stats_farm.xlsx` | `D:\Taadaa\runtime\kibe\cron-state\rename_natural_state.json`<br>`D:\Taadaa\reports\` |
| **Admin Farm** | 201 – 280 | Remote (`admin-farm`, `192.168.110.119`) | `D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx` | `D:\OneDrive\TaadaaData\admin\cron-state\rename_natural_state.json`<br>`D:\OneDrive\TaadaaData\admin\rename_reports\` |

---

## 2. Key Pitfalls & Hardened Patterns

### A. Windows CLI Length Limit (8191 Characters) & Chunked Base64 Transfer
- **Problem**: When deploying code scripts (like `do_rename_canonical_runner.py` at 19KB) to `admin-farm` via `admin_ssh.py`, passing a single base64 string exceeds the Windows CLI argument buffer limit (8191 characters), triggering `The command line is too long`.
- **Solution**: Chunk files into 4000-character segments and stream via base64 decode:
  ```python
  raw_data = open(src, "rb").read()
  data_b64 = base64.b64encode(raw_data).decode("ascii")
  chunk_size = 4000
  chunks = [data_b64[i:i+chunk_size] for i in range(0, len(data_b64), chunk_size)]
  for idx, c in enumerate(chunks):
      mode = "wb" if idx == 0 else "ab"
      cmd = f'python -c "import base64; open(r\\"D:\\\\Taadaa\\\\tools\\\\{f}\\", \\"{mode}\\").write(base64.b64decode(\\"{c}\\"))"'
      subprocess.run([sys.executable, r"D:\Taadaa\tools\admin_ssh.py", cmd], check=True)
  ```

### B. OneDrive Cloud-Only (Dehydrated) File Trap (`OSError: [Errno 22]`)
- **Problem**: Accessing a shared file such as `D:\OneDrive\TaadaaData\taikhoan_run_safe_combined.xlsx` on the remote host can fail with `OSError: [Errno 22] Invalid argument` if OneDrive Smart Sync / Files On-Demand has left the file dehydrated (reparse point).
- **Solution**: Target the host-local native workbook `D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx` which is always hydrated on `Admin-PC`:
  ```python
  SAFE_XLS = (
      Path(r"D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx")
      if IS_ADMIN_HOST
      else Path("D:/OneDrive/TaadaaData/taikhoan_run_safe_combined.xlsx")
  )
  ```

### C. 2-Tier Verification for WinRT OCR in Name Input Fields (`NAME_EDIT`)
- **Problem**: In the TikTok `NAME_EDIT` field, light font colors and a blinking cursor cause WinRT OCR to distort Vietnamese diacritics (e.g. `Sơn Nấm` reads as `Sdn I\läm`, `Tươi Đậu` reads as `Tl-fdi DåU`). Whole-string fuzzy matching (`SequenceMatcher >= 0.70`) drops to ~0.44 and causes false-abort cancels.
- **Solution**: Tokenize all OCR words and match word-by-word at `ratio >= 0.6`, verified alongside the character counter:
  ```python
  words = [norm(w) for w in NEW_NAME.split() if len(w) >= 2]
  all_ocr_words = [norm(w) for l in lines for w in l.split()]
  found_word = any(
      any(difflib.SequenceMatcher(None, ow, w).ratio() >= 0.6 for ow in all_ocr_words)
      for w in words
  )
  ratio = difflib.SequenceMatcher(None, norm(" ".join(lines)), NEW_NAME_NORM).ratio()
  ok_text = (
      any(is_target(l) for l in lines)
      or NEW_NAME_NORM in norm(" ".join(lines))
      or ratio >= 0.35
      or found_word
  )
  count_match = re.search(r"(\d{1,2})\s*/\s*30", box)
  expected_len = len(NEW_NAME)
  ok_count = (count_match is not None and abs(int(count_match.group(1)) - expected_len) <= 1) or f"{expected_len}/30" in box
  if not (ok_text and ok_count):
      tap(XY_NAME_CANCEL, 2)
      raise Abort(f"OCR khong xac nhan o nhap = '{NEW_NAME}' ({expected_len}/30)")
  ```
  The strict check (`ratio >= 0.75`) is enforced on the Profile screen readback where text is rendered large and bold.

### D. Host Environment & Locking Isolation
- **Host Detection**:
  ```python
  IS_ADMIN_HOST = os.environ.get("USERNAME") == "Admin" or "admin" in os.environ.get("COMPUTERNAME", "").lower()
  u_dir = "admin" if IS_ADMIN_HOST else "kibe"
  u_user = "Admin" if IS_ADMIN_HOST else "Kibe"
  STATE_DIR = (
      Path(r"D:\OneDrive\TaadaaData\admin\cron-state")
      if IS_ADMIN_HOST
      else Path(f"D:/Taadaa/runtime/{u_dir}/cron-state")
  )
  LOCK_DIRS = [
      Path(rf"C:\Users\{u_user}\.codex\device-locks"),
      Path(rf"C:\Users\{u_user}\AppData\Local\automation-core\device-locks"),
  ]
  ```
- **Cronjob Registration on Admin**:
  Use `setup_admin_cron.py` to register `tiktok-rolling-rename-watchdog` into `%LOCALAPPDATA%\hermes\cron\jobs.json` with `deliver: "local"` and `no_agent: true`.
