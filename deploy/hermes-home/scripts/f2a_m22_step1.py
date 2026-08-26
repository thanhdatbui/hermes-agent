# -*- coding: utf-8 -*-
"""m22: TikTok bi thoat ve launcher. Mo lai -> Ho so -> menu -> Cai dat -> Bao mat & quyen
-> Xac minh 2 buoc -> kiem tra trang thai (secret I3JGG5... da co trong cot E tu truoc)."""
import re
import subprocess
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")

from automation_core.device_lock import acquire_device_lock

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
serial = "ce02182210b8607b0c"
machine = 22


def sh(*args, timeout=40):
    return subprocess.run([ADB, "-s", serial, "shell"] + list(args), capture_output=True, timeout=timeout).stdout.decode("utf-8", errors="ignore")


def tap(x, y):
    sh("input", "tap", str(x), str(y))


def dump_xml():
    sh("uiautomator", "dump", "/sdcard/m22.xml")
    return sh("cat", "/sdcard/m22.xml")


def find_any(xml_text, text):
    esc = text.replace("&", "&amp;")
    for cand in (text, esc):
        for attr in ("text", "content-desc"):
            mm = re.search(attr + '="' + re.escape(cand) + r'"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml_text)
            if mm:
                yy = (int(mm.group(2)) + int(mm.group(4))) // 2
                if 150 < yy < 1850:
                    return ((int(mm.group(1)) + int(mm.group(3))) // 2, yy)
    return None


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    # Mo TikTok
    sh("am", "force-stop", "com.ss.android.ugc.trill")
    time.sleep(2)
    sh("monkey", "-p", "com.ss.android.ugc.trill", "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(10)

    # Profile -> menu -> Cai dat
    tap(972, 1883)
    time.sleep(2.5)
    tap(980, 155)
    time.sleep(3)
    x = dump_xml()
    cd = find_any(x, "Cài đặt và quyền riêng tư")
    print(f"[m22] Cai dat: {cd}")
    if not cd:
        texts = sorted(set(re.findall(r'text="([^"]{2,45})"', x)))
        print(f"[m22] man hien tai: {texts[:12]}")
        raise SystemExit(1)
    tap(*cd)
    time.sleep(3)

    # Bảo mật & quyền (scroll tim, text hoac desc)
    target = None
    for _i in range(7):
        x = dump_xml()
        target = find_any(x, "Bảo mật & quyền")
        if target and 300 < target[1] < 1750:
            break
        target = None
        sh("input", "swipe", "540", "1500", "540", "1000", "350")
        time.sleep(1.6)
    print(f"[m22] Bao mat & quyen: {target}")
    if not target:
        raise SystemExit(1)
    tap(*target)
    time.sleep(3)

    xv = find_any(dump_xml(), "Xác minh 2 bước")
    print(f"[m22] Xac minh 2 buoc: {xv}")
    if xv:
        tap(*xv)
        time.sleep(3)

    x = dump_xml()
    rows = []
    for m3 in re.finditer(r'text="([^"]{1,55})"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x):
        t, y1 = m3.group(1), int(m3.group(3))
        if 300 < y1 < 1800 and t:
            rows.append((y1, t))
    seen = set()
    print("[m22] MAN XAC MINH 2 BUOC:")
    for y, t in sorted(rows):
        if t not in seen:
            seen.add(t)
            print(f"  y={y}: {t[:52]!r}")
finally:
    lock.release()
