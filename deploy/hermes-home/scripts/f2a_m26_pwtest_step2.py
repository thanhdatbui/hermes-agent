# -*- coding: utf-8 -*-
"""m26: doc OTP tu Gmail app tren may (dung ham social_reg_v1._try_get_otp_gmail_app)
roi nhap vao man 'Nhập mã gồm 6 chữ số' bang keyevent."""
import re
import subprocess
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")
sys.path.insert(0, r"D:\Taadaa\Tiktok_Reg")

from automation_core.device_lock import acquire_device_lock

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
KEYCODE = {c: 7 + i for i, c in enumerate("0123456789")}
machine, serial = 26, "ce081608c4e3ed1e05"
mail_acc = "tranthimy150820011508@gmail.com"  # cot GMAIL cua m26 (q***3@gmail.com)


def sh(*args, timeout=120):
    return subprocess.run([ADB, "-s", serial, "shell"] + list(args), capture_output=True, timeout=timeout).stdout.decode("utf-8", errors="ignore")


def tap(x, y):
    sh("input", "tap", str(x), str(y))


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    from social_reg_v1 import _try_get_otp_gmail_app
    code = _try_get_otp_gmail_app(ADB, serial, mail_acc)
    print(f"[m26] OTP len={len(code) if code else 0}")
    if not code:
        raise SystemExit("[m26] khong doc duoc OTP tu Gmail app")

    # Quay lai TikTok
    sh("am", "force-stop", "com.google.android.gm")
    time.sleep(2)
    sh("monkey", "-p", "com.ss.android.ugc.trill", "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(10)

    def dump_xml():
        for _i in range(4):
            sh("uiautomator", "dump", "/sdcard/m26.xml", timeout=40)
            x = sh("cat", "/sdcard/m26.xml", timeout=40)
            if len(x) > 500:
                return x
            time.sleep(3)
        return x

    x = dump_xml()
    texts = sorted(set(re.findall(r'text="([^"]{2,60})"', x)))
    print(f"[m26] MAN QUAY LAI: {texts[:8]}")

    if any(("6 chữ số" in t or "nhập mã" in t.lower()) for t in texts):
        tap(540, 700)
        time.sleep(1.5)
        for ch in code:
            sh("input", "keyevent", str(KEYCODE[ch]))
            time.sleep(0.35)
        time.sleep(4)

    x = dump_xml()
    texts = sorted(set(re.findall(r'text="([^"]{2,70})"', x)))
    print(f"[m26] SAU OTP: {texts[:14]}")
finally:
    lock.release()
