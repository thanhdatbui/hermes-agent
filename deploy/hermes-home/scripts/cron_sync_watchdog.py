#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cron_sync_watchdog.py
Tự động đồng bộ jobs.json và scripts giữa Kibe runtime, Git deploy và OneDrive Shared.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

KIBE_JOBS = Path(os.path.expanduser(r"~\AppData\Local\hermes\cron\jobs.json"))
DEPLOY_JOBS = Path(r"D:\Taadaa\Hermes\deploy\hermes-home\cron\jobs.json")
ONEDRIVE_JOBS = Path(r"D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\jobs.json")

KIBE_SCRIPTS = Path(os.path.expanduser(r"~\AppData\Local\hermes\scripts"))
DEPLOY_SCRIPTS = Path(r"D:\Taadaa\Hermes\deploy\hermes-home\scripts")
ONEDRIVE_SCRIPTS = Path(r"D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts")


def sync_jobs(force: bool = False) -> bool:
    if not KIBE_JOBS.exists():
        return False
    try:
        src_bytes = KIBE_JOBS.read_bytes()
        changed = False
        for dst in [DEPLOY_JOBS, ONEDRIVE_JOBS]:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if force or not dst.exists() or dst.read_bytes() != src_bytes:
                tmp = dst.with_suffix(".tmp")
                tmp.write_bytes(src_bytes)
                tmp.replace(dst)
                changed = True
                print(f"[SYNC] Updated jobs.json -> {dst}")
        return changed
    except Exception as e:
        sys.stderr.write(f"[SYNC ERROR] jobs.json: {e}\n")
        return False


def sync_scripts(force: bool = False) -> int:
    synced_count = 0
    ONEDRIVE_SCRIPTS.mkdir(parents=True, exist_ok=True)
    DEPLOY_SCRIPTS.mkdir(parents=True, exist_ok=True)

    if not KIBE_SCRIPTS.exists():
        return 0

    for f in KIBE_SCRIPTS.iterdir():
        if f.is_file() and f.suffix in (".py", ".ps1", ".json", ".yaml", ".yml"):
            dst_deploy = DEPLOY_SCRIPTS / f.name
            if force or not dst_deploy.exists() or f.stat().st_mtime > dst_deploy.stat().st_mtime:
                try:
                    shutil.copy2(f, dst_deploy)
                    synced_count += 1
                except Exception:
                    pass

            dst_onedrive = ONEDRIVE_SCRIPTS / f.name
            if force or not dst_onedrive.exists() or f.stat().st_mtime > dst_onedrive.stat().st_mtime:
                try:
                    shutil.copy2(f, dst_onedrive)
                    synced_count += 1
                except Exception:
                    pass

    return synced_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Watchdog tự động đồng bộ cron và scripts toàn farm")
    parser.add_argument("--force", action="store_true", help="Buộc đồng bộ toàn bộ ngay lập tức")
    args = parser.parse_args()

    jobs_changed = sync_jobs(force=args.force)
    scripts_synced = sync_scripts(force=args.force)

    if jobs_changed or scripts_synced > 0 or args.force:
        print(f"[CRON-SYNC] Hoàn tất đồng bộ: jobs_changed={jobs_changed}, scripts_synced={scripts_synced}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
