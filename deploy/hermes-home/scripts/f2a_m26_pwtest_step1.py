# -*- coding: utf-8 -*-
"""m26: chay het luong doi pass de TEST pass cot D.
Chon email -> Tiep -> doc OTP tu Gmail app (social_reg_v1._try_get_otp_gmail_app)
-> nhap OTP keyevent -> man 'Tao mat khau moi' NHAP PASS COT D vao ca 2 o
-> bam Tiep -> doc ket qua: thanh cong = pass DUNG, bao loi = pass SAI/khong bat buoc."""
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
    for _i in range(4):
        sh("uiautomator", "dump", "/sdcard/m26.xml", timeout=40)
        x = sh("cat", "/sdcard/m26.xml", timeout=40)
        if len(x) > 500:
            return x
        time.sleep(3)
    return x


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    x = dump_xml()
    # Neu dang o man chon phuong thuc -> bam TIEP (email da duoc chon mac dinh)
    if "Tiếp" in x and "Xác minh danh tính" in x:
        print("[m26] chon email + Tiep")
        mm = re.search(r'text="Tiếp"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x)
        if mm:
            tap((int(mm.group(1)) + int(mm.group(3))) // 2, (int(mm.group(2)) + int(mm.group(4))) // 2)
            time.sleep(5)

    x = dump_xml()
    texts = sorted(set(re.findall(r'text="([^"]{2,60})"', x)))
    print(f"[m26] MAN SAU TIEP: {texts[:10]}")
finally:
    lock.release()
