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

def _get_workbook_paths() -> tuple[str, str]:
    cfg_path = os.environ.get("TAADAA_HOST_CONFIG", r"D:\Taadaa\machine-config\kibe.yaml")
    wb_root = r"D:\OneDrive\TaadaaData\kibe"
    if os.path.exists(cfg_path):
        try:
            import yaml
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                if "workbook_root" in data:
                    wb_root = data["workbook_root"]
        except Exception:
            pass
    dat = os.path.join(wb_root, "taikhoan_dat_v2_updated .xlsx")
    safe = os.path.join(wb_root, "taikhoan_run_safe.xlsx")
    return dat, safe


def main() -> int:
    env = dict(os.environ)
    dat_path, safe_path = _get_workbook_paths()
    env["TIKTOK_TRACKING_WORKBOOK"] = dat_path
    env["TIKTOK_SAFE_WORKBOOK_ONEDRIVE"] = safe_path
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
