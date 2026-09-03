# Test Pattern: Mocking `_ensure_outlook_app_mailbox_selected` (2026-09-03)

When testing `read_tiktok_otp_from_outlook_app` or `read_tiktok_magic_link_from_outlook_app` with `unittest.mock.patch`, the new function `_ensure_outlook_app_mailbox_selected` must be mocked to return `True` (mailbox already active) or `False` (mailbox not found) depending on the test case.

## Pattern

```python
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

# In test setup, add this patch:
with patch.object(hotmail_login, "_ensure_outlook_app_mailbox_selected", return_value=True):
    result = hotmail_login.read_tiktok_otp_from_outlook_app(
        "adb", "serial-38", TARGET, Path(temp_dir), timeout=1
    )
```

## Test Cases Affected

All existing tests in `test_outlook_app_reader.py` that call `read_tiktok_otp_from_outlook_app` need this additional patch:

1. `test_reader_moves_archive_to_inbox_before_accepting_otp`
2. `test_reader_moves_persisted_non_inbox_folder_to_inbox_before_otp`
3. `test_reader_requires_exact_verified_mailbox_before_reading` → mock `return_value=False`
4. `test_reader_returns_preview_otp_only_after_verified_inbox`
5. `test_reader_handles_drawer_already_open_on_launch_without_toolbar`

## Note

The old `_outlook_app_account_present` mock can be removed or kept for backward compatibility, but the new function is now the primary gate for mailbox verification before OTP reading.