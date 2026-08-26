# -*- coding: utf-8 -*-
"""m41: man 2 buoc dang TAT. Email (m***s@gmail.com) + Mat khau co san.
Bam nut BAT -> Bo qua dien thoai -> chon/confirm Email -> OTP qua Gmail app -> nhap."""
import re
import subprocess
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")

from automation_core.device_lock import acquire_device_lock

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
KEYCODE = {c: 7 + i for i, c in enumerate("0123456789")}
machine, serial = 41, "ce031823f9b1903c01"
mail_acc = "lethithutrang081120030811@gmail.com"


def sh(*args):
    return subprocess.run([ADB, "-s", serial, "shell"] + list(args), capture_output=True, timeout=40).stdout.decode("utf-8", errors="ignore")


def tap(x, y):
    sh("input", "tap", str(x), str(y))


def dump_xml():
    sh("uiautomator", "dump", "/sdcard/m41.xml")
    return sh("cat", "/sdcard/m41.xml")


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    # 1. Nut BAT o duoi man
    x = dump_xml()
    mm = re.search(r'text="Bật"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x)
    cy = (int(mm.group(2)) + int(mm.group(4))) // 2
    print(f"[m41] bam BAT y={cy}")
    tap(540, cy)
    time.sleep(3)

    # 2. Man them dien thoai -> Bo qua (nut o tren trai/giua)
    x = dump_xml()
    mm = re.search(r'text="Bỏ qua"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x)
    if mm:
        cy = (int(mm.group(2)) + int(mm.group(4))) // 2
        cx = (int(mm.group(1)) + int(mm.group(3))) // 2
        print(f"[m41] bo qua dien thoai ({cx},{cy})")
        tap(cx, cy)
        time.sleep(3)

    x = dump_xml()
    texts = sorted(set(re.findall(r'text="([^"]{2,60})"', x)))
    print(f"[m41] MAN SAU BAT: {[t for t in texts if not t.startswith(('14:', '89%', 'Chuông', 'Thông', 'Đang', 'Tín'))][:18]}")
finally:
    lock.release()
