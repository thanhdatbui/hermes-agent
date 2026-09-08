"""Hermes cron no_agent wrapper cho Avatar Post-Feed Watchdog.

Chạy định kỳ kiểm tra nhịp kết thúc Ca 3 nuôi feed để kích hoạt batch up avatar cho Row cuối ngày.
Im lặng khi ngoài khung giờ hoặc khi feed runner đang bận ([SKIP]).
"""
import subprocess
import sys

PY = r"D:\Taadaa\python-envs\automation\Scripts\python.exe"
SCRIPT = r"D:\Taadaa\Tiktok-video\scripts\avatar_post_feed_watchdog.py"

proc = subprocess.run(
    [PY, "-B", SCRIPT],
    capture_output=True,
    text=True,
    timeout=3600,
    cwd=r"D:\Taadaa\Tiktok-video",
)
out = (proc.stdout or "").strip()
err = (proc.stderr or "").strip()

if proc.returncode == 0:
    if out and not out.startswith("[SKIP]"):
        print(out)
else:
    sys.stderr.write(err or f"exit code {proc.returncode}\n")
    sys.exit(proc.returncode if proc.returncode else 1)
