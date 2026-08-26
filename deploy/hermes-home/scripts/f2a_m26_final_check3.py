# -*- coding: utf-8 -*-
"""m26 chot: 'Bảo mật & quyền' la content-desc (khong phai text) nen regex truoc khong thay.
Tim theo content-desc, tap, vao Xác minh 2 bước, dump trang thai."""
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


def find_by_desc(xml_text, desc):
    esc = desc.replace("&", "&amp;")
    for cand in (desc, esc):
        mm = re.search(r'content-desc="' + re.escape(cand) + r'"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml_text)
        if mm:
            yy = (int(mm.group(2)) + int(mm.group(4))) // 2
            if 150 < yy < 1800:
                return ((int(mm.group(1)) + int(mm.group(3))) // 2, yy)
    return None


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    # Dang o settings chinh voi 'Bảo mật & quyền' o dinh man (content-desc, y=228-314)
    x = dump_xml()
    target = find_by_desc(x, "Bảo mật & quyền")
    print(f"[m26] Bao mat & quyen: {target}")
    if not target:
        raise SystemExit("khong tim thay")
    tap(*target)
    time.sleep(3)

    # Xac minh 2 bước co the la text hoac desc
    x = dump_xml()
    xv = None
    mm = re.search(r'(?:text|content-desc)="Xác minh 2 bước"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x)
    if mm:
        xv = (540, (int(mm.group(2)) + int(mm.group(4))) // 2)
    print(f"[m26] Xac minh 2 buoc: {xv}")
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
    print("[m26] TRANG THAI CUOI:")
    for y, t in sorted(rows):
        if t not in seen:
            seen.add(t)
            print(f"  y={y}: {t[:52]!r}")
finally:
    lock.release()
