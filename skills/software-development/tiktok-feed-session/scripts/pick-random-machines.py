#!/usr/bin/env python3
"""Pick N random worker machines for a manual feed session, excluding busy ones.

Reads machine + serial + account list from taikhoan_run_safe.xlsx sheet
'Accounts' (col A = may, col B = Device ID, col C = ID — 80 machines x 6
account rows). Picks N random machines; optionally excludes machine numbers
(--exclude), filters to machines that HAVE an account at a given account row
(--row N, col C ID non-empty at that row), and/or filters to online-only via
`adb devices`.

--row is required hygiene (user correction 2026-08-11, M78): a machine whose
selected row has all-None accounts has no account to run -> it must never be
picked (runner would fail at VPN preflight or worse, silently skip).

Usage (from repo root D:\\Taadaa\\tiktok-luot nuoi acc):
  PYTHONPATH= python scripts/pick-random-machines.py --n 15 --exclude 74 --row 1 --online-only

Prints comma-separated machine numbers (sorted ascending) to stdout; logs
filter stats to stderr. Exit 2 when pool is too small.
"""
from __future__ import annotations

import argparse
import random
import re
import subprocess
import sys

DEFAULT_WORKBOOK = r"D:\Taadaa\tiktok-luot nuoi acc\data\taikhoan_run_safe.xlsx"
DEFAULT_ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"


def load_machines(workbook_path: str) -> tuple[dict[int, str], dict[int, list[str]]]:
    """Return (serial_by_machine, accounts_by_machine).

    serial_by_machine: first non-empty Device ID per machine.
    accounts_by_machine: per-machine list of col-C IDs (None = empty slot),
    index = account row - 1 (row 1 -> index 0).
    """
    import openpyxl

    wb = openpyxl.load_workbook(workbook_path, read_only=True)
    try:
        ws = wb["Accounts"]
        serials: dict[int, str] = {}
        accounts: dict[int, list[str]] = {}
        for row in ws.iter_rows(values_only=True):
            if not row or row[0] is None:
                continue
            text = str(row[0]).strip()
            if not text.isdigit():
                continue
            machine = int(text)
            serial = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
            if not serials.get(machine):
                serials[machine] = serial
            account = str(row[2]).strip() if len(row) > 2 and row[2] is not None else ""
            accounts.setdefault(machine, []).append(account or None)  # keep None for empty slots
    finally:
        wb.close()
    return serials, accounts


def online_serials(adb: str) -> set[str]:
    result = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=60)
    serials: set[str] = set()
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            serials.add(parts[0])
    return serials


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, required=True, help="number of machines to pick")
    parser.add_argument("--exclude", type=str, default="", help="comma-separated machine numbers to exclude (e.g. 74 or 15,40)")
    parser.add_argument("--row", type=int, default=None, help="only pick machines that HAVE an account (col C non-empty) at this account row (1-6)")
    parser.add_argument("--workbook", type=str, default=DEFAULT_WORKBOOK, help="safe account workbook path")
    parser.add_argument("--online-only", action="store_true", help="only pick machines whose serial is online in adb devices")
    parser.add_argument("--adb", type=str, default=DEFAULT_ADB)
    parser.add_argument("--seed", type=int, default=None, help="optional RNG seed for reproducibility")
    args = parser.parse_args()

    serials, accounts = load_machines(args.workbook)
    if not serials:
        print("no machines found in workbook", file=sys.stderr)
        return 2

    excluded = {int(x) for x in re.split(r"[,\s]+", args.exclude) if x.strip().isdigit()}
    pool = [m for m in sorted(serials) if m not in excluded]

    if args.row is not None:
        before = len(pool)
        filtered = []
        for m in pool:
            slots = accounts.get(m) or []
            # slot index = row - 1; machine qualifies only if that slot has a non-empty account
            if len(slots) >= args.row and slots[args.row - 1]:
                filtered.append(m)
        pool = filtered
        print(f"[pick] row {args.row}: {len(pool)}/{before} machines have an account at that row", file=sys.stderr)

    if args.online_only:
        online = online_serials(args.adb)
        before = len(pool)
        pool = [m for m in pool if serials.get(m) in online]
        print(f"[pick] online filter: {len(pool)}/{before} machines online", file=sys.stderr)

    if len(pool) < args.n:
        print(f"not enough machines in pool ({len(pool)} < {args.n})", file=sys.stderr)
        return 2

    rng = random.Random(args.seed)
    picked = sorted(rng.sample(pool, args.n))
    print(",".join(map(str, picked)))
    return 0


if __name__ == "__main__":
    sys.exit(main())