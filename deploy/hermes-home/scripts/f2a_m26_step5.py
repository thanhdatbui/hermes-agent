# -*- coding: utf-8 -*-
"""m26: bam Bo qua lam roi ve feed. Di lai: profile -> settings -> Bao mat & quyen
-> Xac minh 2 buoc -> BAT -> Bo qua dien thoai -> chon Email -> Tiep -> OTP."""
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
    cap = capture_atx_session_ui(adb, timeout=25)
    xml_text = getattr(cap, "xml", None)
    if not xml_text:
        return []
    root = ET.fromstring(xml_text)
    out = []
    for n in root.iter("node"):
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", "") or "")
        if m:
            t = (n.attrib.get("text", "") or n.attrib.get("content-desc", ""))[:65]
            out.append((int(m.group(2)), int(m.group(4)), t))
    return out


def row_center(nodes, label, min_y=200):
    for y1, y2, t in nodes:
        if label in t and y1 > min_y and (y2 - y1) < 400:
            return (y1 + y2) // 2
    return None


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    adb = AdbClient(adb_path=ADB, serial=serial)

    # Ve profile
    adb.shell(["input", "keyevent", "4"])
    time.sleep(1.5)
    adb.shell(["input", "keyevent", "4"])
    time.sleep(1.5)
    cap = capture_atx_session_ui(adb, timeout=25)
    root = ET.fromstring(getattr(cap, "xml") or "<r/>")
    prof_xy = None
    for n in root.iter("node"):
        if (n.attrib.get("text", "") or "") == "Hồ sơ":
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", "") or "")
            if m:
                prof_xy = ((int(m.group(1)) + int(m.group(3))) // 2, (int(m.group(2)) + int(m.group(4))) // 2)
            break
    if not prof_xy:
        print("[m26] khong thay tab Ho so")
        raise SystemExit(1)
    adb.shell(["input", "tap", str(prof_xy[0]), str(prof_xy[1])])
    time.sleep(2.5)

    # Menu -> Cai dat
    adb.shell(["input", "tap", "980", "155"])
    time.sleep(2.5)
    nodes = dump(adb)
    cy = row_center(nodes, "Cài đặt và quyền riêng tư")
    if not cy:
        raise SystemExit(f"[m26] khong thay Cai dat: {[t for _,_,t in nodes[:8]]}")
    adb.shell(["input", "tap", "540", str(cy)])
    time.sleep(3)

    # Bao mat & quyen
    target = None
    for _i in range(6):
        nodes = dump(adb)
        target = row_center(nodes, "Bảo mật & quyền")
        if target:
            break
        adb.shell(["input", "swipe", "540", "1500", "540", "900", "350"])
        time.sleep(1.5)
    if not target:
        raise SystemExit("[m26] khong thay Bao mat & quyen")
    adb.shell(["input", "tap", "540", str(target)])
    time.sleep(3)

    # Xac minh 2 buoc
    nodes = dump(adb)
    xv = row_center(nodes, "Xác minh 2 bước")
    if not xv:
        raise SystemExit("[m26] khong thay Xac minh 2 buoc")
    adb.shell(["input", "tap", "540", str(xv)])
    time.sleep(3)

    # Nut BAT
    nodes = dump(adb)
    bat = row_center(nodes, "Bật", min_y=1500)
    if not bat:
        labels = sorted({t for _, _, t in nodes if t and len(t) < 50})
        raise SystemExit(f"[m26] khong thay nut BAT: {labels[:10]}")
    adb.shell(["input", "tap", "540", str(bat)])
    print("[m26] da bam BAT lan 2")
    time.sleep(3)

    # Bo qua man them dien thoai neu xuat hien
    nodes = dump(adb)
    skip = row_center(nodes, "Bỏ qua")
    if skip:
        adb.shell(["input", "tap", "540", str(skip)])
        print("[m26] bo qua them dien thoai")
        time.sleep(3)
        nodes = dump(adb)

    labels = sorted({t for _, _, t in nodes if t and len(t) < 55})
    print(f"[m26] MAN HIEN TAI: {labels[:16]}")
finally:
    lock.release()
