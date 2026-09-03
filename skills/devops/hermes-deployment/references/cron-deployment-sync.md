# Cron Configuration and Scripts Deployment (Multi-Machine)

## Architecture & Storage

- **Repository Source (Shared)**:
  - `D:\Taadaa\Hermes\deploy\hermes-home\cron\jobs.json`: Canonical definitions for recurring jobs (feed runners, watchdogs, lock reapers, render monitors).
  - `D:\Taadaa\Hermes\deploy\hermes-home\scripts\`: All Python scripts invoked by cron jobs.
  - `D:\Taadaa\Hermes\deploy\CRON_DEPLOYMENT_GUIDE.md`: Deployment guide.

- **Local Machine Runtime**:
  - `%LOCALAPPDATA%\hermes\cron\jobs.json`: Active cron job configuration.
  - `%LOCALAPPDATA%\hermes\scripts\`: Active script executables.
  - `%LOCALAPPDATA%\hermes\cron\executions.db`: Local SQLite execution history (machine-local, NOT committed).

## Synchronization Workflow

1. **Bootstrap on New / Admin Machine**:
   - Running `.\deploy\setup-admin.ps1` automatically copies missing `jobs.json` and syncs `scripts/*.py` via robocopy.

2. **Cron Scheduling Rule**:
   - Use fixed 5-field cron format (e.g. `*/15 * * * *`) rather than loose interval strings (`every 30m`) for critical maintenance tasks like `reap-dead-owner-locks` to avoid ticker clock drift over long sessions.

3. **Lock File Schema Compatibility**:
   - Devices locks across different repos may use either `machine`/`project`/`serial` or `stt`/`owner`/`device_id`.
   - Watchdogs and parsers must support both schemas and regex fallback from filename `machine_(\d+).lock.json` to prevent `Máy None` / `unknown` false alerts.
