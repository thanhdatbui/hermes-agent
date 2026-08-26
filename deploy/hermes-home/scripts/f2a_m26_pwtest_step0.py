# -*- coding: utf-8 -*-
"""m26: xac minh danh tinh (email OTP) de vao man DOI MAT KHAU.
1. Chon email -> Tiep -> man nhap 6 so
2. Doc OTP tu Gmail app (dung ham social_reg_v1._try_get_otp_gmail_app)
3. Nhap OTP bang keyevent
4. Man doi mat khau: nhap pass cot D vao 'mat khau hien tai' (neu co) + mat khau moi
5. Xem TikTok chap nhan khong => kiem tra pass excel DUNG/SAI."""
import re
import subprocess
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")

from automation_core.device_lock import acquire_device_lock

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
KEYCODE = {c: 7 + i for i, c in enumerate("0123456789")}
machine, serial = 26, "ce081608c4e3ed1e05"


def sh(*args, timeout=90):
    return subprocess.run([ADB, "-s", serial, "shell"] + list(args), capture_output=True, timeout=timeout).stdout.decode("utf-8", errors="ignore")


def tap(x, y):
    sh("input", "tap", str(x), str(y))


def dump_xml():
    for _i in range(3):
        sh("uiautomator", "dump", "/sdcard/m26.xml", timeout=40)
        x = sh("cat", "/sdcard/m26.xml", timeout=40)
        if len(x) > 500:
            return x
        time.sleep(3)
    return x


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    x = dump_xml()
    texts = sorted(set(re.findall(r'text="([^"]{2,60})"', x)))
    print(f"[m26] MAN HIEN TAI: {texts[:10]}")
    # Neu van o man chon phuong thuc -> tiep tuc; neu da o man nhap ma -> skip
finally:
    lock.release()
