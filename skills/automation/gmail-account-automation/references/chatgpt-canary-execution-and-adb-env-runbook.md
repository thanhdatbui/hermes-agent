# ChatGPT Account Linking Canary Execution Pattern

> ⚠️ **DEPRECATED (2026-09-30)**: Luồng đăng ký/liên kết ChatGPT trực tiếp trên thiết bị Samsung S7 **ĐÃ DỪNG VĨNH VIỄN** theo chỉ thị Operator. Toàn bộ luồng đăng ký ChatGPT được chuyển sang GPMLogin trên PC sau khi tài khoản Gmail đã ngâm đủ ngày ($\ge 7$d). Tham khảo chi tiết tại `references/s7-gmail-result-classification-and-chatgpt-decommission.md`.

## Context & Environment
- **Repo**: `D:/Taadaa/register gmail`
- **Scripts**: `D:/Taadaa/register gmail/scripts/hook_chatgpt_register.py`
- **Python Runtime**: `D:/Taadaa/python-envs/automation/Scripts/python.exe`
- **Automation Core**: `D:/Taadaa/automation-core/src`

## Key Pitfall: ADB CLI vs Internal Resolver
- In git-bash / terminal, `adb` is often not exported to standard `$PATH` (`adb: command not found`).
- Do **not** spend tool calls searching the drive for `adb.exe` (which can time out or consume iteration budget).
- `gmail_reg_v10.py` and `hook_chatgpt_register.py` already embed their own device shell / ADB detection (`.GemPhoneFarm/app/adb-tool/adb.exe` / xiaowei).
- Invoking via the venv python directly executes `shell()` commands reliably.

## Direct Canary Invocation Template
To execute canary linking on any farm device (e.g. Máy 6 - serial `9885e64c484c544d32`) without exhausting tool calls:

```python
import sys
sys.path.insert(0, r"D:/Taadaa/automation-core/src")
sys.path.insert(0, r"D:/Taadaa/register gmail")
sys.path.insert(0, r"D:/Taadaa/register gmail/scripts")

from automation_core.device_lock import DeviceContext
from hook_chatgpt_register import register_chatgpt_on_device

serial = "<DEVICE_SERIAL>"
machine_id = <MACHINE_NUM>

with DeviceContext(serial=serial, machine=machine_id, project="canary_chatgpt", user_authorized=True):
    res = register_chatgpt_on_device(
        device_id=serial,
        email="<EMAIL>",
        password="<PASSWORD>",
        dob="<DOB_YYYY-MM-DD>",
        timeout=180,
        check_live=False  # Skip checkmail.live for newly registered / known live accounts
    )
    print("CANARY_RESULT:", res)
```
- Results and screenshots are recorded in `res` and stored under `C:/Users/Kibe/AppData/Local/register-gmail/screenshots/`.
