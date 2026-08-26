# -*- coding: utf-8 -*-
"""m26 FIX LAN CUOI: sau pm clear uiautomator, thu lai toan bo chuoi OTP.
1. Chon email + Tiep -> man nhap 6 so
2. Doc OTP Gmail app
3. Quay lai TikTok, THU TUNG Y (560/620/700) tap + keyevent tung so rieng (khong input text)
4. Sau moi lan thu dump kiem tra 'code-input' text thay doi hoac man chuyen."""
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")
sys.path.insert(0, r"D:\Taadaa\Tiktok_Reg")

from automation_core.device_lock import acquire_device_lock

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
KEYCODE = {c: 7 + i for i, c in enumerate("0123456789")}
machine, serial = 26, "ce081608c4e3ed1e05"
mail_acc = "tranthimy150820011508@gmail.com"


def sh(*args, timeout=120):
    return subprocess.run([ADB, "-s", serial, "shell"] + list(args), capture_output=True, timeout=timeout).stdout.decode("utf-8", errors="ignore")


def tap(x, y):
    sh("input", "tap", str(x), str(y))


def dump_xml():
    for _i in range(5):
        sh("uiautomator", "dump", "/sdcard/m26.xml", timeout=40)
        x = sh("cat", "/sdcard/m26.xml", timeout=40)
        if len(x) > 500:
            return x
        time.sleep(4)
    return x


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    # Dang o man chon phuong thuc -> Tiep
    x = dump_xml()
    if "Tiếp" in x and "Xác minh danh tính" in x:
        mm = re.search(r'text="Tiếp"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x)
        tap((int(mm.group(1)) + int(mm.group(3))) // 2, (int(mm.group(2)) + int(mm.group(4))) // 2)
        print("[m26] bam Tiep")
        time.sleep(5)

    # Doc OTP
    from social_reg_v1 import _try_get_otp_gmail_app
    nb = datetime.now() - timedelta(minutes=3)
    try:
        code = _try_get_otp_gmail_app(serial, mail_acc, not_before=nb)
    except Exception as e:
        print(f"[m26] gmail exc: {type(e).__name__}")
        code = None
    print(f"[m26] OTP: {'CO' if code else 'KHONG'}")
    if not code:
        raise SystemExit("[m26] stop")

    sh("am", "force-stop", "com.google.android.gm")
    time.sleep(2)
    sh("monkey", "-p", "com.ss.android.ugc.trill", "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(14)

    x = dump_xml()
    ok = False
    for cy in (620, 560, 700):
        tap(540, cy)
        time.sleep(1.5)
        for ch in code:
            sh("input", "keyevent", str(KEYCODE[ch]))
            time.sleep(0.4)
        time.sleep(3)
        x = dump_xml()
        texts = sorted(set(re.findall(r'text="([^"]{2,80})"', x)))
        still_otp = any("6 chữ số" in t for t in texts)
        print(f"[m26] y={cy} -> otp_man={still_otp}, texts={texts[:6]}")
        if not still_otp:
            ok = True
            break

    print(f"[m26] SAU OTP {'OK' if ok else 'VAN KET'}")
    texts = sorted(set(re.findall(r'text="([^"]{2,90})"', x)))
    print(f"[m26] MAN CUOI: {texts[:16]}")
finally:
    lock.release()
