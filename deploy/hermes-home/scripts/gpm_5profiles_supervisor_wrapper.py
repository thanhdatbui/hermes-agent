#!/usr/bin/env python3
import os, subprocess, sys

args = sys.argv[1:] if len(sys.argv) > 1 else ["--live"]

# 1. Farm Kibe (M1-80)
kibe_env = os.environ.copy()
kibe_env["ENABLE_CODEX_OAUTH"] = "0"
kibe_cmd = [sys.executable, r"D:\Taadaa\GPM auto\scripts\batch_gpm_5profiles_supervisor.py"] + args
res_kibe = subprocess.run(kibe_cmd, env=kibe_env, creationflags=0x08000000 if sys.platform == 'win32' else 0)

# 2. Farm Admin (M201-280) - Lấy Hotmail Admin log lên GPM ở Kibe
admin_env = os.environ.copy()
admin_env["ENABLE_CODEX_OAUTH"] = "0"
admin_env["GPM_SUPERVISOR_DATA_DIR"] = r"D:\OneDrive\TaadaaData\admin"
admin_env["GPM_SUPERVISOR_ACCOUNT_XLSX"] = r"D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx"
admin_env["GPM_SUPERVISOR_PROXY_XLSX"] = r"D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx"
admin_env["GPM_SUPERVISOR_STATE_PATH"] = r"D:\Taadaa\runtime\admin\cron-state\batch_gpm_5profiles_supervisor_state.json"
admin_cmd = [sys.executable, r"D:\Taadaa\GPM auto\scripts\batch_gpm_5profiles_supervisor.py"] + args
res_admin = subprocess.run(admin_cmd, env=admin_env, creationflags=0x08000000 if sys.platform == 'win32' else 0)

sys.exit(res_kibe.returncode if res_kibe.returncode != 0 else res_admin.returncode)
