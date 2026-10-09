"""Watchdog automatically closes Xiaowei when user is idle (no mouse/keyboard input).

Prevents continuous 80-stream USB bus saturation and exclusive I/O handle locks
after operators finish viewing farm screens and leave the PC idle.
"""

import ctypes
import os
import subprocess
import sys
import time
from typing import Optional


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_user_idle_seconds() -> float:
    """Returns seconds since last user input (mouse move/click or keyboard press)."""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return max(0.0, millis / 1000.0)
    return 0.0


def is_process_running(proc_name: str = "xiaowei.exe") -> bool:
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", f"IMAGENAME eq {proc_name}", "/NH"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return proc_name.lower() in out.lower()
    except Exception:
        return False


def terminate_process(proc_name: str = "xiaowei.exe") -> bool:
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", proc_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return True
    except Exception:
        return False


def check_and_auto_close_xiaowei(
    idle_threshold_seconds: float = 600.0,
    proc_name: str = "xiaowei.exe",
) -> Optional[dict]:
    """Inspects idle time and terminates Xiaowei if idle threshold exceeded."""
    if not is_process_running(proc_name):
        return None

    idle_sec = get_user_idle_seconds()
    if idle_sec >= idle_threshold_seconds:
        killed = terminate_process(proc_name)
        return {
            "action": "closed",
            "process": proc_name,
            "idle_seconds": round(idle_sec, 1),
            "threshold_seconds": idle_threshold_seconds,
            "killed": killed,
        }

    return {
        "action": "active",
        "process": proc_name,
        "idle_seconds": round(idle_sec, 1),
        "threshold_seconds": idle_threshold_seconds,
    }


if __name__ == "__main__":
    threshold = float(sys.argv[1]) if len(sys.argv) > 1 else 600.0
    res = check_and_auto_close_xiaowei(threshold)
    if res:
        print(f"[XIAOWEI_IDLE_WATCHDOG] action={res['action']} idle_sec={res['idle_seconds']} threshold_sec={res['threshold_seconds']}")
    else:
        print("[XIAOWEI_IDLE_WATCHDOG] xiaowei.exe is not running.")
