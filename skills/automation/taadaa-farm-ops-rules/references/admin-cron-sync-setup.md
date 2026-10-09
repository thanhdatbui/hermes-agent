# Admin Cron Sync Setup (11/09/2026)

## Goal
Admin machine receives same TikTok feed session reports as Kibe via Telegram, using same watchdog logic but reading from admin's own runtime.

## Setup Package
Created: `D:\Taadaa\deploy\admin_cron_setup.bat`

## What the Script Does
1. Creates admin runtime directories: `D:\Taadaa\runtime\admin\cron-state`, `cron-source`
2. Copies `feed_session_watchdog.py` to admin's `%LOCALAPPDATA%\hermes\scripts\`
3. Installs Python deps: `psutil`, `pyyaml`
4. Generates `cron-source/hermes_cron_source_config.json` with admin workbook path
5. Outputs the exact `jobs.json` entry to add manually

## Required Admin Environment Variables
```bash
TAADAA_HOST_CONFIG=D:\Taadaa\machine-config\admin.yaml
HERMES_CRON_STATE_ROOT=D:\Taadaa\runtime\admin\cron-state
HERMES_CRON_SOURCE_CONFIG=D:\Taadaa\runtime\admin\cron-source\hermes_cron_source_config.json
HERMES_CRON_OFFLINE_ROOT=D:\Taadaa\runtime\admin
```

## Hermes Cron Job Entry (add to admin's jobs.json)
```json
{
  "job_id": "admin-tiktok-feed-session-watchdog",
  "name": "admin-tiktok-feed-session-watchdog",
  "prompt": "Watchdog: Report TikTok feed sessions per Ca (admin machine)",
  "schedule": {"kind": "cron", "expr": "*/5 * * * *", "display": "*/5 * * * *"},
  "model": null,
  "provider": null,
  "base_url": null,
  "repeat": "forever",
  "deliver": "telegram:-5139245637",
  "script": "feed_session_watchdog.py",
  "no_agent": true,
  "workdir": "D:\\Taadaa\\tiktok-luot nuoi acc",
  "enabled_toolsets": ["terminal", "file"],
  "enabled": true,
  "env": {
    "TAADAA_HOST_CONFIG": "D:\\Taadaa\\machine-config\\admin.yaml",
    "HERMES_CRON_STATE_ROOT": "D:\\Taadaa\\runtime\\admin\\cron-state",
    "HERMES_CRON_SOURCE_CONFIG": "D:\\Taadaa\\runtime\\admin\\cron-source\\hermes_cron_source_config.json",
    "HERMES_CRON_OFFLINE_ROOT": "D:\\Taadaa\\runtime\\admin"
  }
}
```

## Post-Setup Steps on Admin
1. Add job entry to `%LOCALAPPDATA%\hermes\cron\jobs.json`
2. Restart hermes: `net stop hermes && net start hermes`
3. Verify: check `D:\Taadaa\runtime\admin\cron-state\` for state files, Telegram for reports

## Key Differences from Kibe
- Workbook: `D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx`
- Host config: `D:\Taadaa\machine-config\admin.yaml`
- Runtime root: `D:\Taadaa\runtime\admin`
- Same watchdog script, same Telegram delivery target

## Watchdog Logic (Same as Kibe)
- Runs every 5 min
- Reports when a Ca completes (4 Ca/day: 00h, 06h, 12h, 18h)
- Reports Feed + Follow + Upload stats
- Sends RED ALERT if error rate > 30%