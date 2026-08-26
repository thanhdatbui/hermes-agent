# -*- coding: utf-8 -*-
"""m26: tim row 'Bảo mật & quyền' bang cach scroll dan dan va dump bounds CU THÊ.
Row nay co the bi uiautomator bo qua text (nhung van co bounds + clickable).
Chien luoc: dump bounds cua TẤT CẢ node, in node nao co y trong khoang sau 'Tài khoản' header."""
import re
import subprocess
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")

from automation_core.device_lock import acquire_device_lock

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
serial = "ce081608c4e3ed1e05"
machine = 26


def sh(*args, timeout=40):
    return subprocess.run([ADB, "-s", serial, "shell"] + list(args), capture_output=True, timeout=timeout).stdout.decode("utf-8", errors="ignore")


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    # Scroll den vi tri Tài khoản hien du nhin
    sh("input", "swipe", "540", "1700", "540", "700", "500")
    time.sleep(3)
    sh("uiautomator", "dump", "/sdcard/m26.xml")
    x = sh("cat", "/sdcard/m26.xml")
    # In tat ca node co text hoac clickable kem y
    nodes = []
    for m3 in re.finditer(r'text="([^"]*)"[^>]*clickable="(true|false)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x):
        t, clk, y1, y2 = m3.group(1), m3.group(2), int(m3.group(4)), int(m3.group(6))
        if not t and clk != "true":
            continue
        nodes.append((y1, y2, t, clk))
    # thu lai voi thu tu attribute khac (bounds truoc text)
    if len(nodes) < 5:
        for m3 in re.finditer(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*text="([^"]*)"[^>]*clickable="(true|false)"', x):
            y1, y2, t, clk = int(m3.group(2)), int(m3.group(4)), m3.group(5), m3.group(6)
            if not t and clk != "true":
                continue
            nodes.append((y1, y2, t, clk))
    print("NODES:")
    for y1, y2, t, clk in sorted(set(nodes)):
        if 250 < y1 < 1850:
            print(f"  y={y1}-{y2} clk={clk}: {t[:45]!r}")
finally:
    lock.release()
