# On-Device TikTok Rename Workflow & Farm Device Lock Coexistence

## Overview
When an operator provides a screenshot of a TikTok account with an unadapted or foreign/shop name (e.g. `LilyanLederhos64090`, `@lilyanzj8n1`) and requests "Đổi tên nick này", follow this complete end-to-end execution workflow.

## 1. O(1) Account Identification & Ground Truth Mapping
Never run broad disk scans or blind device searches. Query the farm database directly:
```python
import sqlite3
conn = sqlite3.connect('D:/OneDrive/TaadaaData/tiktok_tracker.db')
c = conn.cursor()
c.execute("SELECT machine_id, slot, cluster FROM farm_account_info WHERE username = ?", (target_username,))
# Yields e.g. (76, 7, 'kibe') -> Machine 76, Slot 7
```
Cross-reference with `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`:
- Match machine ID and target username to find the exact row (e.g. row 608 for M76 slot 7).

## 2. Farm Safety & Device Lock Coexistence Preflight
Before touching the device:
1. Inspect device status: `python D:/Taadaa/tools/inspect_machine.py <machine_id>`
2. Check device lock file: `C:\Users\Kibe\.codex\device-locks\serial_<SERIAL>.lock.json`
3. Check active processes: If a multi-machine feed or follow session (`run_tiktok.py --mode multi-machine-feed-session`) is running on the device, **NEVER** kill the process, steal the lock, or force ADB inputs.
4. **Coexistence Protocol**: Monitor the run log (`log.jsonl`) until the feed session finishes its final swipe and performs `close_all_apps_end`, releasing the lock cleanly.

## 3. Name Generation & Vietnamese Phonetic Mapping
Apply the phonetic adaptation rules from `account-profile-entropy`:
- Foreign prefixes: `lilyan-` -> `Ngọc Linh`, `Khánh Linh`, `Linh`
- Base64 encoding: `base64.b64encode(NEW_NAME.encode('utf-8')).decode('ascii')` (e.g. `Ngọc Linh` -> `Tmfhu41jIExpbmg=`)
- Character count: `len("Ngọc Linh") = 9` -> Counter on TikTok will be `9/30`.

## 4. State Machine OCR Rename Pattern (`do_rename_m<ID>.py`)
Construct a dedicated device runner using WinRT OCR (`tools/ocr_boxes.ps1`) and `operator_device_lock`:
- **Locking**: Wrap execution in `with operator_device_lock(machine=MACHINE_ID, serial=SERIAL, project="do_rename_m...", timeout=300):`
- **State Classification**:
  - `FEED`: Tap profile tab `(972, 1857)`.
  - `PROFILE`: Extract nickname and username. If username != target, swipe up and tap header `(500, 140)` to open Switcher. If target, tap "Sửa hồ sơ" / pencil icon `(72, 148)`.
  - `SWITCHER`: Tap the target username row. If not visible, swipe sheet up.
  - `EDIT_PROFILE`: Identify label "Tên" (must be above "Tên người dùng") and tap the row.
  - `NAME_EDIT`:
    1. Tap clear text `(960, 576)`.
    2. Broadcast `ADB_KEYBOARD_INPUT_TEXT` with base64 text.
    3. Verify text and counter (`9/30`).
    4. Tap "Lưu" `(980, 140)`.
    5. Handle confirmation dialog ("Bạn chỉ có thể thay đổi biệt danh 7 ngày 1 lần") by tapping "Xác nhận".
  - `SAVE_LOGIN_POPUP`: Dismiss automatically ("Để sau" / `(540, 1325)`).
- **Readback Verification**: Re-read the profile screen via OCR, confirming the line immediately above `@username` matches the new name.
- **Teardown**: Revert IME to the previous default if changed.

## 5. Hermetic Offline Testing
Before executing on the phone, create `tests/test_do_rename_m<ID>.py` testing pure logic:
- `norm()`: Diacritics stripping, lowercasing, whitespace collapsing.
- `compact()`: Stripping non-alphanumeric characters.
- `classify()`: Classification of all screen states including OCR distortion cases.
- `is_target()` / `is_target_user()`: Fuzzy matching tolerances.
- Run `pytest tests/test_do_rename_m<ID>.py` ensuring 100% pass (<0.5s).

## 6. Execution via Background Terminal
Adhere to farm event-driven wakeup:
- Launch via `terminal(command="python D:/Taadaa/tools/do_rename_m<ID>.py", background=True, notify_on_complete=True, timeout=300)`.
- Never poll sleep loops. Let the harness wake the agent upon completion.
- Once woken, inspect the resulting `m<ID>_<name>_nickname.png` and JSON report, verifying with OCR / vision before delivering `MEDIA:` to the operator.
