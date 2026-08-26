# -*- coding: utf-8 -*-
"""m27 sau reboot: mo TikTok -> Ho so -> menu -> Cai dat -> Bao mat & quyen ->
Xac minh 2 buoc (dang o trang thai 'cho nhap OTP' tu luong truoc? kiem tra)."""
import re
import subprocess
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")

from automation_core.device_lock import acquire_device_lock

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
serial = "ce031823912ae0d20c"
machine = 27


def sh(*args, timeout=60):
    return subprocess.run([ADB, "-s", serial, "shell"] + list(args), capture_output=True, timeout=timeout).stdout.decode("utf-8", errors="ignore")


def tap(x, y):
    sh("input", "tap", str(x), str(y))


def dump_xml():
    sh("uiautomator", "dump", "/sdcard/m27.xml")
    return sh("cat", "/sdcard/m27.xml")


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    sh("monkey", "-p", "com.ss.android.ugc.trill", "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(15)
    x = dump_xml()
    texts = sorted(set(re.findall(r'text="([^"]{2,55})"', x)))
    print(f"[m27] man hien tai: {texts[:14]}")
finally:
    lock.release()
