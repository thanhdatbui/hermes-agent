# -*- coding: utf-8 -*-
"""m26: TikTok bi tre o SplashActivity. Restart app roi vao lai man Phuong thuc xac minh de chot."""
import re
import subprocess
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")

from automation_core.device_lock import acquire_device_lock

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
serial = "ce081608c4e3ed1e05"
machine = 26


def sh(*args, timeout=40):
    return subprocess.run([ADB, "-s", serial, "shell"] + list(args), capture_output=True, timeout=timeout).stdout.decode("utf-8", errors="ignore")


def tap(x, y):
    sh("input", "tap", str(x), str(y))


def dump_xml():
    sh("uiautomator", "dump", "/sdcard/m26.xml")
    return sh("cat", "/sdcard/m26.xml")


def find_y(xml_text, text):
    esc = text.replace("&", "&amp;")
    for cand in (text, esc):
        mm = re.search(r'text="' + re.escape(cand) + r'"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml_text)
        if mm:
            yy = (int(mm.group(2)) + int(mm.group(4))) // 2
            if 250 < yy < 1800:
                return ((int(mm.group(1)) + int(mm.group(3))) // 2, yy)
    return None


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
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
    cd = find_y(x, "Cài đặt và quyền riêng tư")
    print(f"[m26] Cai dat: {cd}")
    if cd:
        tap(*cd)
        time.sleep(3)
        # Bảo mật & quyền
        target = None
        for _i in range(6):
            x = dump_xml()
            target = find_y(x, "Bảo mật & quyền")
            if target and 300 < target[1] < 1750:
                break
            target = None
            sh("input", "swipe", "540", "1500", "540", "1000", "350")
            time.sleep(1.6)
        print(f"[m26] Bao mat & quyen: {target}")
        if target:
            tap(*target)
            time.sleep(3)
            # Xác minh 2 bước
            xv = find_y(dump_xml(), "Xác minh 2 bước")
            print(f"[m26] Xac minh 2 buoc: {xv}")
            if xv:
                tap(*xv)
                time.sleep(3)
                x = dump_xml()
                rows = []
                for m3 in re.finditer(r'text="([^"]{1,55})"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x):
                    t, y1 = m3.group(1), int(m3.group(3))
                    if 300 < y1 < 1750 and t:
                        rows.append((y1, t))
                seen = set()
                print("[m26] TRANG THAI CUOI:")
                for y, t in sorted(rows):
                    if t not in seen:
                        seen.add(t)
                        print(f"  y={y}: {t[:50]!r}")
finally:
    lock.release()
