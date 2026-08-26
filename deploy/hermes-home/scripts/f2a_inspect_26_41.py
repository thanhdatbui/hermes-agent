# -*- coding: utf-8 -*-
"""Inspect trang thai Xac minh 2 buoc cua m26, m41 (va m22): vao Bao mat -> dump."""
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

MACHINES = {
    26: "ce081608c4e3ed1e05",
    41: "ce031823f9b1903c01",
}


def dump_texts(adb):
    cap = capture_atx_session_ui(adb, timeout=20)
    xml_text = getattr(cap, "xml", None) or (cap.get("xml") if isinstance(cap, dict) else None)
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
        y1, y2 = int(m.group(2)), int(m.group(4))
        clk = n.attrib.get("clickable")
        out.append((y1, y2, t[:55], clk))
    return out


def find_row(nodes, label):
    for y1, y2, t, _clk in nodes:
        if label in t and y1 > 250:
            return (y1 + y2) // 2
    return None


for machine, serial in MACHINES.items():
    lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
    try:
        adb = AdbClient(adb_path=ADB, serial=serial)
        # Ve Home truoc
        for _ in range(3):
            adb.shell(["input", "keyevent", "4"])
            time.sleep(0.8)
        # Mo menu 3 gach tu profile: bam Home truoc de chac o tab profile
        adb.shell(["input", "keyevent", "3"])
        time.sleep(1.5)
        adb.shell(["am", "start", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", "-p", "com.ss.android.ugc.trill", "--activity-brought-to-front"])
        time.sleep(5)

        nodes = dump_texts(adb)
        # Neu khong phai profile -> tim tab Profile o menu duoi
        prof_y = None
        for y1, y2, t, _clk in nodes:
            if t == "Hồ sơ":
                prof_y = (y1 + y2) // 2
                break
        if prof_y:
            adb.shell(["input", "tap", str(prof_y), str(1850)])
            time.sleep(2.5)
        # Menu 3 gach goc tren phai
        adb.shell(["input", "tap", "980", "155"])
        time.sleep(2.5)
        nodes = dump_texts(adb)
        cy = find_row(nodes, "Cài đặt và quyền riêng tư")
        if not cy:
            print(f"[m{machine}] KHONG thay Cai dat: {[(t) for _,_,t,_ in nodes[:10]]}")
            continue
        adb.shell(["input", "tap", "540", str(cy)])
        time.sleep(3)
        # Tim Bảo mật & quyền qua scroll
        target = None
        for _i in range(6):
            nodes = dump_texts(adb)
            target = find_row(nodes, "Bảo mật & quyền")
            if target:
                break
            adb.shell(["input", "swipe", "540", "1500", "540", "900", "350"])
            time.sleep(1.5)
        if not target:
            print(f"[m{machine}] KHONG thay Bao mat & quyen sau scroll")
            continue
        adb.shell(["input", "tap", "540", str(target)])
        time.sleep(3)
        nodes = dump_texts(adb)
        cy2 = find_row(nodes, "Xác minh 2 bước")
        if not cy2:
            print(f"[m{machine}] man Bao mat khong co Xac minh 2 buoc: {sorted([(y,t) for y,_,t,_ in nodes])[:10]}")
            continue
        adb.shell(["input", "tap", "540", str(cy2)])
        time.sleep(3)
        nodes = dump_texts(adb)
        labels = sorted({t for y1, _y2, t, _clk in nodes if t and len(t) < 40})
        print(f"[m{machine}] MAN 2-BUOC: {labels}")
    finally:
        lock.release()
