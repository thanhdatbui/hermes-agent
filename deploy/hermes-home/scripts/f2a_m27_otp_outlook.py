# -*- coding: utf-8 -*-
"""m27: doc OTP tu Outlook app (da login san skitektts@hotmail.com) roi nhap lai TikTok."""
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")
sys.path.insert(0, r"D:\Taadaa\Hotmail")
from flows.hotmail_login import read_tiktok_otp_from_outlook_app, LoginBlocked

from automation_core.device_lock import acquire_device_lock

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
KEYCODE = {c: 7 + i for i, c in enumerate("0123456789")}
machine, serial = 27, "ce031823912ae0d20c"
mail_acc = "skitektfs@hotmail.com"

lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    code = read_tiktok_otp_from_outlook_app(
        ADB,
        serial,
        mail_acc,
        Path(r"D:\Taadaa\runtime\kibe\artifacts\ui_dumps"),
        timeout=150,
    )
    if not code:
        raise SystemExit("[m27] khong doc duoc ma tu Outlook")
    print(f"[m27] DOC DUOC MA (len={len(code)})")

    # Quay lai TikTok
    sh = lambda *a: subprocess.run([ADB, "-s", serial, "shell"] + list(a), capture_output=True, timeout=60).stdout.decode("utf-8", errors="ignore")
    sh("am", "force-stop", "com.microsoft.office.outlook")
    time.sleep(2)
    sh("monkey", "-p", "com.ss.android.ugc.trill", "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(12)

    def tap(x, y):
        sh("input", "tap", str(x), str(y))

    def dump_xml():
        sh("uiautomator", "dump", "/sdcard/m27.xml")
        return sh("cat", "/sdcard/m27.xml")

    x = dump_xml()
    texts = sorted(set(re.findall(r'text="([^"]{2,60})"', x)))
    print(f"[m27] man quay lai: {texts[:10]}")

    # Man nhap ma -> tap vung nhap + go keyevent
    if any(("nhập mã" in t.lower() or "mã gồm" in t.lower() or "xác minh email" in t.lower()) for t in texts):
        tap(540, 700)
        time.sleep(1.5)
        for ch in code:
            sh("input", "keyevent", str(KEYCODE[ch]))
            time.sleep(0.35)
        time.sleep(2)
        x = dump_xml()
        texts2 = sorted(set(re.findall(r'text="([^"]{2,60})"', x)))
        print(f"[m27] SAU NHAP MA: {texts2[:14]}")
finally:
    lock.release()
