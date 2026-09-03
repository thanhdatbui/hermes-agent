# User-Requested Device Lock Release Pattern

Use this procedure whenever the user explicitly commands to unlock/release specific farm machines (e.g. `Gỡ lock 34 54 75 ra`).

## Core Rules

1. **User Explicit Command Only**: Never automatically delete or unlock retained locks on other machines without the user's explicit command.
2. **Dual-File Aliases**: In Taadaa device lock architecture, each machine has two lock alias files:
   - `machine_<ID>.lock.json`
   - `serial_<SERIAL>.lock.json`
   Both are located in `C:\Users\Kibe\.codex\device-locks\`. Both must be addressed together.
3. **Backup Before Deletion**: Before removing any lock file, create a timestamped backup directory in `C:\Users\Kibe\.codex\device-locks\backup_user_unlock_<YYYYMMDD_HHMMSS>` and copy the target lock JSON files into it.
4. **Verification**:
   - Inspect lock contents (`machine`, `serial`, `pid`, `status`) and check whether any alive process exists before deleting.
   - After deleting, list remaining lock files in root directory to ensure only specified targets were removed and remaining machines remain guarded.
5. **Concise Report**: Report exactly which machines/serials were unlocked, the backup directory path, and any remaining locked machines.
