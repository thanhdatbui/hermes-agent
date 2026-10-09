# Hotmail / Outlook Security CDP Automation on GPM Profiles

Runner: `D:\Taadaa\Hotmail\scripts\gpm_change_hotmail_security.py`
Unit Tests: `D:\Taadaa\Hotmail\tests\test_gpm_change_hotmail_security.py`

## Overview
Automates Hotmail password change and "Sign out everywhere" on GPM profiles matching farm machines over Playwright CDP.

## CLI Usage
```bash
python D:\Taadaa\Hotmail\scripts\gpm_change_hotmail_security.py --machine 40 --canary
python D:\Taadaa\Hotmail\scripts\gpm_change_hotmail_security.py --machine 40 --email target@hotmail.com --live
```

## Profile Matching & CDP
- Matches profile by prefix: `f"{machine:02d} - "`, `f"{machine} - "`, `f"M{machine:02d} - "`
- Prioritizes `group_id=1` or `group_id=10`.
- Starts profile via GPM API, retrieves `remote_debugging_address`, connects Playwright `connect_over_cdp`.

## Security Flow Checkpoints
1. `D:\Taadaa\runtime\artifacts\gpm_login_{safe_email}.png`
2. `D:\Taadaa\runtime\artifacts\gpm_pre_change_{safe_email}.png`
3. `D:\Taadaa\runtime\artifacts\gpm_post_change_{safe_email}.png` (when `--live`)
4. `D:\Taadaa\runtime\artifacts\gpm_signout_{safe_email}.png`
