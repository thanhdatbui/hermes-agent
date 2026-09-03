#!/usr/bin/env python3
"""Remove stale device locks from a crashed Tiktok_Reg batch.

Why: if the batch orchestrator dies after acquire_device_lock() but before
lease.finish() (crash, SIGTERM killing the process tree, Hermes session
interrupt), every reserved target keeps a machine_<N>.lock.json + a
serial_<SERIAL>.lock.json with the SAME dead PID. The next batch then reports
all targets SKIPPED_DEVICE_LOCKED.

Safety rules (verified live 2026-08-03):
  * owner_active stays True after parent death -> NOT a staleness signal.
  * Only remove a lock when its pid is dead AND project is Tiktok_Reg*.
  * NEVER remove locks owned by other projects (e.g. tiktok-upload), even if
    the PID looks dead — they may be legitimately retained for recovery.

Usage:
    python clean_stale_device_locks.py [--dry-run] [--project Tiktok_Reg]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

LOCKDIR = pathlib.Path.home() / ".codex" / "device-locks"


def pid_alive(pid: int) -> bool:
    if not pid:
        return False
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        return str(pid) in out
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="list without deleting")
    ap.add_argument("--project", default="Tiktok_Reg", help="project prefix to clean (default Tiktok_Reg)")
    args = ap.parse_args()

    if not LOCKDIR.is_dir():
        print(f"lock dir not found: {LOCKDIR}", file=sys.stderr)
        return 2

    removed, kept = [], []
    for f in sorted(LOCKDIR.glob("machine_*.lock.json")) + sorted(LOCKDIR.glob("serial_*.lock.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        pid = data.get("pid")
        project = str(data.get("project", ""))
        if project.startswith(args.project) and pid and not pid_alive(pid):
            if not args.dry_run:
                f.unlink()
            removed.append(f.name)
        else:
            kept.append(f.name)

    print(f"REMOVED ({len(removed)}):")
    for n in removed:
        print(" ", n)
    print(f"KEPT ({len(kept)}):")
    for n in kept:
        print(" ", n)
    if args.dry_run:
        print("\n[DRY RUN] nothing deleted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
