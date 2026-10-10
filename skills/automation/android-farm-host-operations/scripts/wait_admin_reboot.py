#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wait_admin_reboot.py — Theo doi chu ky reboot Admin PC va doi soat lai danh sach thiet bi ADB.

Cach dung:
    python wait_admin_reboot.py [--skip-shutdown]

Quy trinh:
1. Gui lenh shutdown /r /t 2 toi Admin PC qua SSH (neu khong co --skip-shutdown).
2. Cho 35s cho Admin PC tat hoan toan va buoc vao giai doan BIOS POST.
3. Cho Admin PC boot lai Windows va mo lai port SSH (polling whoami toi da 90s).
4. Cho 15s de Task Scheduler 'Taadaa_ADB_User_Remote' khoi dong ADB server va portproxy 5037.
5. Chay D:/Taadaa/tools/inspect_machine.py de lay hien truong thuc te.
"""

from __future__ import annotations

import subprocess
import sys
import time

ADMIN_SSH = "admin-farm"


def run_ssh(cmd: str, timeout: int = 10) -> tuple[int, str, str]:
    try:
        r = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", ADMIN_SSH, cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as exc:
        return -1, "", str(exc)


def main() -> int:
    skip_shutdown = "--skip-shutdown" in sys.argv

    if not skip_shutdown:
        print("[1/4] Gui lenh shutdown /r /t 2 toi Admin PC qua SSH...")
        code, out, err = run_ssh("shutdown /r /t 2")
        print(f"Lenh shutdown: returncode={code}, out={out}, err={err}")
        print("[2/4] Cho 35s cho Admin PC tat va buoc vao BIOS...")
        time.sleep(35)
    else:
        print("[1/2] Bo qua buoc shutdown, bat dau cho Admin PC online...")

    print("[3/4] Cho Admin PC khoi dong lai va mo lai port SSH...")
    start_wait = time.time()
    reconnected = False
    while time.time() - start_wait < 120:
        code, out, _ = run_ssh("whoami", timeout=5)
        if code == 0 and "admin" in out.lower():
            elapsed = time.time() - start_wait
            print(f"Admin PC da online tro lai sau {elapsed:.1f}s!")
            reconnected = True
            break
        time.sleep(5)

    if not reconnected:
        print("[ERROR] Timeout cho Admin PC online tro lai sau 120s!")
        return 1

    print("[4/4] Cho 15s cho Task Scheduler khoi tao ADB server...")
    time.sleep(15)

    try:
        p = subprocess.run(
            ["python", "D:/Taadaa/tools/inspect_machine.py"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        print("=== KET QUA HIEN TRUONG ADB SAU REBOOT ===")
        for line in p.stdout.splitlines():
            if (
                "ADMIN REMOTE" in line
                or "\tdevice" in line
                or "\toffline" in line
                or "\tunauthorized" in line
            ):
                print(line)
        return 0
    except Exception as exc:
        print(f"[ERROR] inspect_machine.py loi: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
