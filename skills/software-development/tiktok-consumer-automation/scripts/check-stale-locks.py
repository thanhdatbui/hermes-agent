"""Liệt kê device locks + PID aliveness (wmic — tasklist silent-fail trên git-bash).

Usage:
    python check-stale-locks.py [lock_dir]

Mặc định lock_dir = ~/.codex/device-locks. In bảng máy | project | status | pid | alive,
kèm tổng lock thật vs stale. Chạy TRƯỚC batch upload để biết máy nào eligible.
Chỉ đọc — không sửa lock. Dọn lock stale thì move vào
D:\\CodexRuntime\\tiktok-video\\stale-lock-archive\\<ts>_m<machine> (cả machine_X lẫn serial_<serial>).
"""
import json
import glob
import os
import subprocess
import sys

LOCK_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(r'~\.codex\device-locks')


def pid_alive(pid):
    try:
        r = subprocess.run(['wmic', 'process', 'where', f'ProcessId={pid}', 'get', 'ProcessId'],
                           capture_output=True, text=True, timeout=20)
        return any(line.strip() == str(pid) for line in r.stdout.splitlines() if line.strip().isdigit())
    except Exception:
        return '?'


rows = []
for f in sorted(glob.glob(os.path.join(LOCK_DIR, 'machine_*.lock.json'))):
    try:
        m = int(os.path.basename(f).split('_')[1].split('.')[0])
        d = json.load(open(f, encoding='utf-8'))
    except Exception:
        continue
    pid = d.get('pid')
    rows.append((m, d.get('project', '?'), d.get('status', '?'), pid, pid_alive(pid)))

print(f"{'Máy':>4} | {'project':30s} | {'status':10s} | {'pid':>7} | alive")
for m, proj, st, pid, alive in sorted(rows):
    print(f"{m:>4} | {proj:30s} | {st:10s} | {pid:>7} | {'YES' if alive else 'no '}")

alive_n = sum(1 for r in rows if r[4] is True)
print(f"\nTổng lock: {len(rows)} | lock thật (pid sống): {alive_n} | stale: {len(rows) - alive_n}")
print("Máy lock thật:", sorted(r[0] for r in rows if r[4] is True))
