# -*- coding: utf-8 -*-
"""m41: man hien tai la launcher (TikTok chua mo). Mo TikTok -> Ho so -> menu ->
Cai dat -> Bao mat & quyen -> Xac minh 2 buoc. In trang thai."""
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
machine, serial = 41, "ce031823f9b1903c01"


def dump(adb):
    cap = capture_atx_session_ui(adb, timeout=25)
    x = getattr(cap, "xml", None)
    if not x:
        return []
    root = ET.fromstring(x)
    out = []
    for n in root.iter("node"):
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", "") or "")
        if m:
            t = (n.attrib.get("text", "") or n.attrib.get("content-desc", ""))[:60]
            out.append((int(m.group(2)), t))
    return sorted(set(out))


def row_center_y(nodes, label, min_y=250):
    for y1, y2, t in nodes:
        pass
    return None


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    adb = AdbClient(adb_path=ADB, serial=serial)

    def dump_full(adb):
        cap = capture_atx_session_ui(adb, timeout=25)
        x = getattr(cap, "xml", None)
        if not x:
            return ET.fromstring("<r/>")
        return ET.fromstring(x)

    # Mo TikTok
    adb.shell(["monkey", "-p", "com.ss.android.ugc.trill", "-c", "android.intent.category.LAUNCHER", "1"])
    time.sleep(6)

    # Tim tab Ho so o bottom bar
    root = dump_full(adb)
    prof_xy = None
    for n in root.iter("node"):
        if (n.attrib.get("text", "") or "") == "Hồ sơ":
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", "") or "")
            if m:
                prof_xy = ((int(m.group(1)) + int(m.group(3))) // 2, (int(m.group(2)) + int(m.group(4))) // 2)
            break
    if prof_xy and prof_xy[1] > 1700:
        adb.shell(["input", "tap", str(prof_xy[0]), str(prof_xy[1])])
        print(f"[m41] tap Ho so {prof_xy}")
    else:
        print("[m41] khong thay tab Ho so o bottom bar")
    time.sleep(2.5)

    # Menu 3 gach
    adb.shell(["input", "tap", "980", "155"])
    time.sleep(2.5)
    root = dump_full(adb)
    cy = None
    for n in root.iter("node"):
        t = n.attrib.get("text", "") or ""
        if "Cài đặt và quyền riêng tư" in t:
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", "") or "")
            if m:
                cy = (int(m.group(2)) + int(m.group(4))) // 2
            break
    if not cy:
        labels = [t for _, t in dump(adb) if t]
        raise SystemExit(f"[m41] khong thay Cai dat: {labels[:10]}")
    adb.shell(["input", "tap", "540", str(cy)])
    time.sleep(3)

    # Bao mat & quyen: scroll tim
    target = None
    for _i in range(6):
        root = dump_full(adb)
        for n in root.iter("node"):
            t = n.attrib.get("text", "") or ""
            if t == "Bảo mật & quyền":
                m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", "") or "")
                if m:
                    yy = (int(m.group(2)) + int(m.group(4))) // 2
                    if yy > 300:
                        target = yy
                        break
        if target:
            break
        adb.shell(["input", "swipe", "540", "1500", "540", "900", "350"])
        time.sleep(1.5)
    if not target:
        raise SystemExit("[m41] khong thay Bao mat & quyen")
    adb.shell(["input", "tap", "540", str(target)])
    time.sleep(3)

    # Xac minh 2 buoc
    xv = None
    for _i in range(4):
        root = dump_full(adb)
        for n in root.iter("node"):
            t = n.attrib.get("text", "") or ""
            if "Xác minh 2 bước" in t:
                m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", "") or "")
                if m:
                    yy = (int(m.group(2)) + int(m.group(4))) // 2
                    if yy > 300:
                        xv = yy
                        break
        if xv:
            break
        adb.shell(["input", "swipe", "540", "1400", "540", "800", "350"])
        time.sleep(1.5)
    if not xv:
        raise SystemExit("[m41] khong thay Xac minh 2 buoc")
    adb.shell(["input", "tap", "540", str(xv)])
    time.sleep(3)

    nodes = dump(adb)
    labels = [t for _, t in nodes if t and len(t) < 50]
    print(f"[m41] MAN XAC MINH 2 BUOC: {sorted(set(labels))[:16]}")
finally:
    lock.release()
