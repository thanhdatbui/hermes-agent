#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cron_sync_watchdog.py
Tự động đồng bộ jobs.json và scripts giữa Kibe runtime, Git deploy và OneDrive Shared.
"""

from __future__ import annotations

import argparse
import filecmp
import json
import os
import shutil
import sys
import time
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
    changed = False
    try:
        for dst in [DEPLOY_JOBS, ONEDRIVE_JOBS]:
            res = sync_file(KIBE_JOBS, dst, force=force)
            if res == "copied":
                changed = True
                print(f"[SYNC] Updated jobs.json -> {dst}")
        return changed
    except Exception as e:
        sys.stderr.write(f"[SYNC ERROR] jobs.json: {e}\n")
        return False


SCRIPT_SUFFIXES = (".py", ".ps1", ".json", ".yaml", ".yml")
# Dung sai mtime (giây): OneDrive/FAT làm tròn mtime, tránh coi lệch làm tròn là "mới hơn"
MTIME_TOLERANCE_S = 2.0


def _same_content(src: Path, dst: Path) -> bool:
    try:
        s_st, d_st = src.stat(), dst.stat()
        if s_st.st_size != d_st.st_size:
            return False
        return filecmp.cmp(src, dst, shallow=False)
    except OSError:
        return False


def _atomic_copy(src: Path, dst: Path) -> None:
    tmp = dst.with_name(f".{dst.name}.sync.{os.getpid()}.tmp")
    try:
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def sync_file(src: Path, dst: Path, force: bool = False) -> str:
    """Đồng bộ 1 file src -> dst an toàn. Trả về: copied | skipped | conflict | error.

    - dst chưa có -> copy.
    - Nội dung giống hệt (size + bytes) -> skip.
    - src mới hơn dst (vượt dung sai) -> copy (atomic).
    - dst mới hơn src -> skip (kể cả force): không bao giờ để bản cũ đè bản mới;
      chiều đồng bộ ngược sẽ mang bản mới về.
    - mtime ngang nhau nhưng nội dung khác -> conflict, KHÔNG ghi đè.
      Với force: backup dst thành *.conflict-<ts>.bak rồi mới ghi đè.
    """
    try:
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            _atomic_copy(src, dst)
            return "copied"
        if _same_content(src, dst):
            return "skipped"
        src_mtime = src.stat().st_mtime
        dst_mtime = dst.stat().st_mtime
        if src_mtime > dst_mtime + MTIME_TOLERANCE_S:
            _atomic_copy(src, dst)
            return "copied"
        if dst_mtime > src_mtime + MTIME_TOLERANCE_S:
            return "skipped"
        if not force:
            sys.stderr.write(f"[SYNC CONFLICT] {src} vs {dst}: mtime ngang nhau nhưng nội dung khác, bỏ qua\n")
            return "conflict"
        backup = dst.with_name(f"{dst.name}.conflict-{int(time.time())}.bak")
        shutil.copy2(dst, backup)
        _atomic_copy(src, dst)
        sys.stderr.write(f"[SYNC FORCE] Ghi đè {dst} (backup: {backup.name})\n")
        return "copied"
    except Exception as e:
        sys.stderr.write(f"[SYNC ERROR] {src} -> {dst}: {e}\n")
        return "error"


def _iter_script_files(directory: Path):
    if not directory.exists():
        return []
    return sorted(f for f in directory.iterdir() if f.is_file() and f.suffix in SCRIPT_SUFFIXES)


def sync_scripts(force: bool = False) -> int:
    synced_count = 0
    for d in (ONEDRIVE_SCRIPTS, DEPLOY_SCRIPTS):
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            sys.stderr.write(f"[SYNC ERROR] mkdir {d}: {e}\n")

    # DEPLOY -> KIBE / OneDrive: copy only through sync_file's mtime/content conflict guard.
    # Equal-mtime content conflicts are skipped unless explicit --force creates a backup.
    for f in _iter_script_files(DEPLOY_SCRIPTS):
        targets = [ONEDRIVE_SCRIPTS / f.name]
        if KIBE_SCRIPTS.exists():
            targets.insert(0, KIBE_SCRIPTS / f.name)
        for dst in targets:
            result = sync_file(f, dst, force=force)
            if result == "copied":
                synced_count += 1
                print(f"[SYNC] {f.name} -> {dst.parent}")
            elif result == "conflict":
                print(f"[SYNC CONFLICT] Skipped {f.name} -> {dst.parent}")

    # KIBE -> DEPLOY / OneDrive: runtime sửa nóng mới hơn thì đẩy ngược về
    for f in _iter_script_files(KIBE_SCRIPTS):
        for dst in (DEPLOY_SCRIPTS / f.name, ONEDRIVE_SCRIPTS / f.name):
            if sync_file(f, dst, force=force) == "copied":
                synced_count += 1
                print(f"[SYNC] {f.name} -> {dst.parent}")

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
