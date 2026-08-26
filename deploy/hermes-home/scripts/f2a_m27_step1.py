# -*- coding: utf-8 -*-
"""m27 (skitektfs@hotmail.com): Outlook app da co account trong may (legacyimap).
1. Vao TikTok: Bảo mật -> Xác minh 2 bước -> BAT -> bo qua dien thoai
2. Chon Email -> TikTok gui OTP vao hotmail
3. Dung read_tiktok_otp_from_outlook_app doc ma tu Outlook app
4. Quay lai TikTok nhap ma."""
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")
sys.path.insert(0, r"D:\Taadaa\Hotmail")

from automation_core.device_lock import acquire_device_lock

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
KEYCODE = {c: 7 + i for i, c in enumerate("0123456789")}
machine, serial = 27, "ce031823912ae0d20c"
mail_acc = "skitektts@hotmail.com"


def sh(*args, timeout=60):
    return subprocess.run([ADB, "-s", serial, "shell"] + list(args), capture_output=True, timeout=timeout).stdout.decode("utf-8", errors="ignore")


def tap(x, y):
    sh("input", "tap", str(x), str(y))


def dump_xml():
    sh("uiautomator", "dump", "/sdcard/m27.xml")
    return sh("cat", "/sdcard/m27.xml")


def find_any(xml_text, text):
    esc = text.replace("&", "&amp;")
    for cand in (text, esc):
        for attr in ("text", "content-desc"):
            for mm in re.finditer(attr + '="' + re.escape(cand) + r'"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml_text):
                yy = (int(mm.group(2)) + int(mm.group(4))) // 2
                if 150 < yy < 1850:
                    return ((int(mm.group(1)) + int(mm.group(3))) // 2, yy)
    return None


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    # 1. Mo TikTok
    sh("am", "force-stop", "com.ss.android.ugc.trill")
    time.sleep(2)
    sh("monkey", "-p", "com.ss.android.ugc.trill", "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(10)

    tap(972, 1883)  # Ho so
    time.sleep(2.5)
    tap(980, 155)   # menu
    time.sleep(3)
    x = dump_xml()
    cd = find_any(x, "Cài đặt và quyền riêng tư")
    if not cd:
        raise SystemExit(f"[m27] khong thay Cai dat")
    print(f"[m27] Cai dat {cd}")
    tap(*cd)
    time.sleep(3)

    target = None
    for _i in range(7):
        x = dump_xml()
        target = find_any(x, "Bảo mật & quyền")
        if target and 300 < target[1] < 1750:
            break
        target = None
        sh("input", "swipe", "540", "1500", "540", "1000", "350")
        time.sleep(1.6)
    if not target:
        raise SystemExit("[m27] khong thay Bao mat & quyen")
    print(f"[m27] Bao mat & quyen {target}")
    tap(*target)
    time.sleep(3)

    xv = find_any(dump_xml(), "Xác minh 2 bước")
    if not xv:
        raise SystemExit("[m27] khong thay Xac minh 2 buoc")
    print(f"[m27] Xac minh 2 buoc {xv}")
    tap(*xv)
    time.sleep(3)

    x = dump_xml()
    bat = None
    for mm in re.finditer(r'text="Bật"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x):
        cy = (int(mm.group(2)) + int(mm.group(4))) // 2
        if cy > 1500:
            bat = (540, cy)
            break
    if not bat:
        texts = sorted(set(re.findall(r'text="([^"]{2,50})"', x)))
        raise SystemExit(f"[m27] khong thay nut BAT (da bat roi?): {texts[:10]}")
    print(f"[m27] bam BAT {bat}")
    tap(*bat)
    time.sleep(3)

    # Bo qua them dien thoai
    x = dump_xml()
    skip = find_any(x, "Bỏ qua")
    if skip:
        print(f"[m27] bo qua dien thoai {skip}")
        tap(*skip)
        time.sleep(3)
        x = dump_xml()
        skip2 = find_any(x, "Bỏ qua")  # dialog thiet bi tin cay
        if skip2:
            print(f"[m27] bo qua thiet bi tin cay {skip2}")
            tap(*skip2)
            time.sleep(3)
            x = dump_xml()

    texts = sorted(set(re.findall(r'text="([^"]{2,55})"', x)))
    print(f"[m27] MAN SAU BAT: {texts[:16]}")
finally:
    lock.release()
