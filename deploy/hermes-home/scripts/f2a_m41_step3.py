# -*- coding: utf-8 -*-
"""m41: BACK lac ve man 'Hoàn tất hồ sơ'. Lam lai tu dau bang uiautomator dump:
profile -> menu -> Cai dat -> Bao mat & quyen (scroll xuong sau Tài khoản) -> Xac minh 2 buoc."""
import re
import subprocess
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")

from automation_core.device_lock import acquire_device_lock

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
machine, serial = 41, "ce031823f9b1903c01"


def sh(*args):
    return subprocess.run([ADB, "-s", serial, "shell"] + list(args), capture_output=True, timeout=30).stdout.decode("utf-8", errors="ignore")


def tap(x, y):
    sh("input", "tap", str(x), str(y))


def dump_xml():
    sh("uiautomator", "dump", "/sdcard/m41.xml")
    return sh("cat", "/sdcard/m41.xml")


def find_y(xml_text, text):
    candidates = [text]
    if "&" in text:
        candidates.append(text.replace("&", "&amp;"))
    for cand in candidates:
        for mm in re.finditer(r'text="' + re.escape(cand) + r'"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml_text):
            yy = (int(mm.group(2)) + int(mm.group(4))) // 2
            if 250 < yy < 1800:
                return ((int(mm.group(1)) + int(mm.group(3))) // 2, yy)
    return None


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    # 1. Ve profile: bam tab Ho so o bottom bar (y~1883)
    tap(972, 1883)
    time.sleep(2.5)

    # 2. Menu 3 gach
    tap(980, 155)
    time.sleep(2.5)

    # 3. Cai dat va quyen rieng tu
    xml_text = dump_xml()
    cd = find_y(xml_text, "Cài đặt và quyền riêng tư")
    if not cd:
        raise SystemExit("[m41] khong thay Cai dat")
    print(f"[m41] Cai dat {cd}")
    tap(*cd)
    time.sleep(3)

    # 4. Scroll XUONG tim Bảo mật & quyền (nam duoi Tài khoản)
    target = None
    for i in range(6):
        xml_text = dump_xml()
        target = find_y(xml_text, "Bảo mật & quyền")
        if target and 300 < target[1] < 1750:
            break
        target = None
        sh("input", "swipe", "540", "1500", "540", "1000", "350")
        time.sleep(1.6)
    if not target:
        raise SystemExit("[m41] khong thay Bao mat & quyen sau scroll")
    print(f"[m41] Bao mat & quyen {target}")
    tap(*target)
    time.sleep(3)

    # 5. Xac minh 2 bước
    xv = None
    for i in range(4):
        xml_text = dump_xml()
        xv = find_y(xml_text, "Xác minh 2 bước")
        if xv:
            break
        sh("input", "swipe", "540", "1400", "540", "800", "350")
        time.sleep(1.6)
    if not xv:
        raise SystemExit("[m41] khong thay Xac minh 2 buoc")
    print(f"[m41] Xac minh 2 buoc {xv}")
    tap(*xv)
    time.sleep(3)

    xml_text = dump_xml()
    texts = sorted(set(re.findall(r'text="([^"]{2,55})"', xml_text)))
    print(f"[m41] MAN XAC MINH 2 BUOC: {[t for t in texts if not t.startswith(('14:', '89%', 'Chuông', 'Thông', 'Đang', 'Tín'))][:18]}")
finally:
    lock.release()
