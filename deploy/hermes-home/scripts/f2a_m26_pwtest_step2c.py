# -*- coding: utf-8 -*-
"""m26: doc OTP truc tiep tu XML Gmail inbox (ma 568165 da thay trong preview).
Doc file dump gmail_refresh_2_after de lay ma, roi nhap vao TikTok."""
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


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    # Bam mo email OTP (bounds [24,1013][1056,1286] tu log truoc - nhung inbox co the da doi)
    from social_reg_v1 import _try_get_otp_gmail_app
    nb = datetime.now() - timedelta(minutes=2)
    try:
        code = _try_get_otp_gmail_app(serial, mail_acc, not_before=nb)
        print(f"[m26] OTP qua ham chuan: {'CO' if code else 'KHONG'}")
    except Exception as e:
        print(f"[m26] exc: {e}")
        code = None

    if not code:
        # Doc preview tu dump moi nhat: mo Gmail, refresh, doc ma tu text node 'XXXXXX la ma...'
        sh("monkey", "-p", "com.google.android.gm", "-c", "android.intent.category.LAUNCHER", "1")
        time.sleep(8)
        sh("input", "swipe", "540", "700", "540", "1400", "400")
        time.sleep(4)
        sh("uiautomator", "dump", "/sdcard/gm.xml")
        xml = sh("cat", "/sdcard/gm.xml")
        m6 = re.findall(r"(\d{6})\s*la\s*ma", xml.replace("\\n", " "))
        if not m6:
            m6 = re.findall(r"text=\"(\d{6})\"", xml)
        print(f"[m26] ma trong preview: {m6[:3]}")
        code = m6[0] if m6 else None

    if not code:
        raise SystemExit("[m26] het cach doc OTP")

    # Ve TikTok nhap ma
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

    import json
    Path_ = r"D:\Taadaa\runtime\kibe\artifacts\ui_dumps"
    with open(Path_ + r"\m26_otp_code.json", "w") as f:
        json.dump({"code": code}, f)
finally:
    lock.release()
