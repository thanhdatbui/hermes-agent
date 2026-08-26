"""Hermes cron launcher -> repo wrapper hermes_taikhoan_sync_cron.py.

Repo wrapper giu logic (commit duoc); file nay chi la cau noi vi hermes cron
yeu cau script nam trong ~/.hermes/scripts/.

Set env override kibe truoc khi goi wrapper: gateway (pythonw) giu env cu tu
luc khoi dong, nen TIKTOK_TRACKING_WORKBOOK / TIKTOK_SAFE_WORKBOOK_ONEDRIVE
co the van tro duong Tiktok_Reg/codex_gmail_debug cu -> wrapper doc env thang.
Registry HKCU\\Environment da dung kibe (2026-08-12).
"""
from __future__ import annotations

import os
import subprocess
import sys

PYTHON = r"D:\Taadaa\python-envs\automation\Scripts\python.exe"
WRAPPER = r"D:\Taadaa\tiktok-luot nuoi acc\scripts\hermes_taikhoan_sync_cron.py"

KIBE_DAT = r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx"
KIBE_SAFE = r"D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx"


def main() -> int:
    env = dict(os.environ)
    env["TIKTOK_TRACKING_WORKBOOK"] = KIBE_DAT
    env["TIKTOK_SAFE_WORKBOOK_ONEDRIVE"] = KIBE_SAFE
    completed = subprocess.run(
        [PYTHON, WRAPPER],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if completed.stdout:
        sys.stdout.write(completed.stdout)
    if completed.stderr:
        sys.stderr.write(completed.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
