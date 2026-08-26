# -*- coding: utf-8 -*-
"""m26: dang o man Giải phóng dung lượng -> BACK ve settings chinh -> Bảo mật & quyền
-> Xác minh 2 bước -> Bật -> chọn method email -> Tiếp -> OTP Gmail app."""
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
KEYCODE = {c: 7 + i for i, c in enumerate("0123456789")}
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


def row_center(nodes, label):
    for y1, y2, t in nodes:
        if label in t and y1 > 250 and (y2 - y1) < 400:
            return (y1 + y2) // 2
    return None


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    adb = AdbClient(adb_path=ADB, serial=serial)
    # 1. BACK tu Giải phóng dung lượng
    adb.shell(["input", "keyevent", "4"])
    time.sleep(2)
    nodes = dump(adb)
    labels = [t for _, _, t in nodes if t]
    print("[m26] sau BACK:", labels[:6])

    # 2. Neu khong phai settings chinh thi tim Bảo mật & quyền ngay / scroll
    target = None
    for i in range(5):
        nodes = dump(adb)
        target = row_center(nodes, "Bảo mật & quyền")
        if target:
            break
        # co the dang o man con -> thu tim Xác minh 2 bước truc tiep
        xv = row_center(nodes, "Xác minh 2 bước")
        if xv:
            print("[m26] da thay Xac minh 2 buoc truc tiep")
            adb.shell(["input", "tap", "540", str(xv)])
            time.sleep(3)
            break
        adb.shell(["input", "swipe", "540", "1500", "540", "900", "350"])
        time.sleep(1.5)

    if target:
        print(f"[m26] Bao mat & quyen y={target}")
        adb.shell(["input", "tap", "540", str(target)])
        time.sleep(3)
        nodes = dump(adb)
        xv = row_center(nodes, "Xác minh 2 bước")
        if xv:
            adb.shell(["input", "tap", "540", str(xv)])
            time.sleep(3)
    elif not any("Xác minh" in t for _, _, t in dump(adb)):
        print("[m26] khong dinh vi duoc man Bao mat")
        raise SystemExit(1)

    nodes = dump(adb)
    labels = sorted({t for _, _, t in nodes if t and len(t) < 45})
    print(f"[m26] MAN HIEN TAI: {labels[:14]}")
finally:
    lock.release()
