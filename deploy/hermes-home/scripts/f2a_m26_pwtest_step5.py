# -*- coding: utf-8 -*-
"""m26: nhap ma OTP vua gui (man 'Nhap ma gom 6 chu so') bang keyevent sau khi
doc tu Gmail app. Sau do man 'Tao mat khau moi' se hien - NHAP PASS COT D."""
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
    # Doc OTP moi (ma vua bam resend o buoc truoc)
    from social_reg_v1 import _try_get_otp_gmail_app
    nb = datetime.now() - timedelta(minutes=3)
    try:
        code = _try_get_otp_gmail_app(serial, mail_acc, not_before=nb)
    except Exception as e:
        print(f"[m26] gmail exc: {type(e).__name__}")
        code = None
    print(f"[m26] OTP: {'CO' if code else 'KHONG'}")
    if not code:
        raise SystemExit("[m26] STOP - khong co OTP")

    # Ve TikTok
    sh("am", "force-stop", "com.google.android.gm")
    time.sleep(2)
    sh("monkey", "-p", "com.ss.android.ugc.trill", "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(14)

    x = dump_xml()
    texts = sorted(set(re.findall(r'text="([^"]{2,60})"', x)))
    print(f"[m26] MAN: {texts[:8]}")

    if any("6 chữ số" in t for t in texts):
        tap(540, 660)
        time.sleep(2)
        for ch in code:
            sh("input", "keyevent", str(KEYCODE[ch]))
            time.sleep(0.35)
        time.sleep(6)

    x = dump_xml()
    texts = sorted(set(re.findall(r'text="([^"]{2,80})"', x)))
    print(f"[m26] SAU OTP: {texts[:16]}")

    with open(r"D:\Taadaa\runtime\kibe\artifacts\ui_dumps\m26_state.json", "w") as f:
        json.dump({"otp": bool(code), "after": texts}, f, ensure_ascii=False)
finally:
    lock.release()
