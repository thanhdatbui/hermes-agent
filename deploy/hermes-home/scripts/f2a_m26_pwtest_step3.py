# -*- coding: utf-8 -*-
"""m26: nhap lai OTP vao man 'Nhap ma gom 6 chu so' - doc code da luu, tap dung o
(thu cac toa do), keyevent tung so, kiem tra ket qua."""
import json
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


with open(r"D:\Taadaa\runtime\kibe\artifacts\ui_dumps\m26_otp_code.json") as f:
    code = json.load(f)["code"]
print(f"[m26] OTP len={len(code)}")

lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    # Gui lai ma moi cho an toan (ma cu co the het han sau nhieu phut)
    x = dump_xml()
    if "Gửi lại mã" in x:
        mm = re.search(r'text="Gửi lại mã"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x)
        if mm:
            print("[m26] bam Gui lai ma")
            tap((int(mm.group(1)) + int(mm.group(3))) // 2, (int(mm.group(2)) + int(mm.group(4))) // 2)
            time.sleep(6)

    # Doc ma moi tu Gmail app
    sys.path.insert(0, r"D:\Taadaa\Tiktok_Reg")
    from datetime import datetime, timedelta
    from social_reg_v1 import _try_get_otp_gmail_app

    nb = datetime.now() - timedelta(minutes=2)
    try:
        code2 = _try_get_otp_gmail_app(serial, "tranthimy150820011508@gmail.com", not_before=nb)
        print(f"[m26] ma moi: {'CO' if code2 else 'khong'}")
        if code2:
            code = code2
    except Exception as e:
        print(f"[m26] exc: {type(e).__name__}")

    # Quay lai TikTok
    sh("am", "force-stop", "com.google.android.gm")
    time.sleep(2)
    sh("monkey", "-p", "com.ss.android.ugc.trill", "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(10)

    x = dump_xml()
    texts = sorted(set(re.findall(r'text="([^"]{2,60})"', x)))
    print(f"[m26] MAN: {texts[:8]}")

    if any("6 chữ số" in t for t in texts):
        # Thu tap o giua man nhap ma (cac o so nam ~ y=650-750 theo kinh nghiem m35/m44)
        for yy in (660, 720):
            tap(540, yy)
            time.sleep(1.2)
            ok = True
            for ch in code:
                sh("input", "keyevent", str(KEYCODE[ch]))
                time.sleep(0.3)
            time.sleep(3)
            x = dump_xml()
            texts = sorted(set(re.findall(r'text="([^"]{2,70})"', x)))
            print(f"[m26] SAU NHAP y={yy}: {texts[:12]}")
            if not any("6 chữ số" in t for t in texts):
                break
finally:
    lock.release()
