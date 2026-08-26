# -*- coding: utf-8 -*-
"""m26: dang xem video (profile Khánh Hà). Ve profile cua nick -> menu -> settings
-> Bảo mật & quyền -> Xác minh 2 bước. In man 2 buoc."""
import re
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")

from automation_core.adb import AdbClient
from automation_core.device_lock import acquire_device_lock
from automation_core.persistent_ui import capture_atx_session_ui
import xml.etree.ElementTree as ET

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
machine, serial = 26, "ce081608c4e3ed1e05"


def dump(adb):
    cap = capture_atx_session_ui(adb, timeout=20)
    xml_text = getattr(cap, "xml", None)
    if not xml_text:
        return []
    root = ET.fromstring(xml_text)
    out = []
    for n in root.iter("node"):
        b = n.attrib.get("bounds", "")
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b or "")
        if not m:
            continue
        t = n.attrib.get("text", "") or n.attrib.get("content-desc", "")
        out.append((int(m.group(2)), int(m.group(4)), t[:60]))
    return out


def row_center(nodes, label, min_y=250):
    for y1, y2, t in nodes:
        if label in t and y1 > min_y and (y2 - y1) < 400:
            return (y1 + y2) // 2
    return None


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    adb = AdbClient(adb_path=ADB, serial=serial)
    # BACK thoat video ve feed/profile, roi bam tab Ho so o bottom bar (y~1850)
    adb.shell(["input", "keyevent", "4"])
    time.sleep(2)
    nodes = dump(adb)
    prof = None
    for y1, y2, t in nodes:
        if t == "Hồ sơ":
            prof = ((y1 + y2) // 2, )
            # lay x: tim bounds day du
            break
    # Tim lai voi x
    cap = capture_atx_session_ui(adb, timeout=20)
    root = ET.fromstring(getattr(cap, "xml") or "<root/>")
    prof_xy = None
    for n in root.iter("node"):
        if (n.attrib.get("text", "") or "") == "Hồ sơ":
            b = n.attrib.get("bounds", "")
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b or "")
            if m:
                prof_xy = ((int(m.group(1)) + int(m.group(3))) // 2, (int(m.group(2)) + int(m.group(4))) // 2)
            break
    if prof_xy:
        print(f"[m26] tap Ho so {prof_xy}")
        adb.shell(["input", "tap", str(prof_xy[0]), str(prof_xy[1])])
        time.sleep(2.5)
    else:
        print("[m26] khong thay tab Ho so, thu Home + mo app")
        adb.shell(["input", "keyevent", "3"])
        time.sleep(1.5)
        adb.shell(["am", "start", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", "-p", "com.ss.android.ugc.trill", "--activity-brought-to-front"])
        time.sleep(5)

    # Menu 3 gach
    adb.shell(["input", "tap", "980", "155"])
    time.sleep(2.5)
    nodes = dump(adb)
    cy = row_center(nodes, "Cài đặt và quyền riêng tư")
    if not cy:
        labels = [t for _, _, t in nodes if t]
        print(f"[m26] khong thay Cai dat: {labels[:10]}")
        raise SystemExit(1)
    adb.shell(["input", "tap", "540", str(cy)])
    time.sleep(3)

    # Scroll tim Bảo mật & quyền
    target = None
    for _i in range(6):
        nodes = dump(adb)
        target = row_center(nodes, "Bảo mật & quyền")
        if target:
            break
        adb.shell(["input", "swipe", "540", "1500", "540", "900", "350"])
        time.sleep(1.5)
    if not target:
        print("[m26] khong thay Bao mat & quyen")
        raise SystemExit(1)
    adb.shell(["input", "tap", "540", str(target)])
    time.sleep(3)

    nodes = dump(adb)
    xv = row_center(nodes, "Xác minh 2 bước")
    if not xv:
        labels = sorted({t for _, _, t in nodes if t and len(t) < 45})
        print(f"[m26] man Bao mat khong co Xac minh 2 buoc: {labels}")
        raise SystemExit(1)
    adb.shell(["input", "tap", "540", str(xv)])
    time.sleep(3)
    nodes = dump(adb)
    labels = sorted({t for _, _, t in nodes if t and len(t) < 50})
    print(f"[m26] MAN XAC MINH 2 BUOC: {labels[:16]}")
finally:
    lock.release()
