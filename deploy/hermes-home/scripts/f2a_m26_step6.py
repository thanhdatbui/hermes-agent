# -*- coding: utf-8 -*-
"""m26: man chon method (Dien thoai TAT, Email BAT, Mat khau BAT).
Bam row EMAIL (540,1033) de chon, roi nut Tiep/Bat o duoi."""
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
    x = getattr(cap, "xml", None)
    if not x:
        return []
    root = ET.fromstring(x)
    out = []
    for n in root.iter("node"):
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", "") or "")
        if m:
            t = (n.attrib.get("text", "") or n.attrib.get("content-desc", ""))[:65]
            out.append((int(m.group(2)), int(m.group(4)), t))
    return out


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    adb = AdbClient(adb_path=ADB, serial=serial)
    # Bam row Email
    adb.shell(["input", "tap", "540", "1033"])
    time.sleep(2)
    nodes = dump(adb)
    labels = sorted({t for _, _, t in nodes if t and len(t) < 60})
    print("[m26] sau khi bam Email:", labels[:14])
    # Tim nut Tiep / Bat / Xac nhan o duoi man
    for kw in ("Tiếp", "Bật", "Xác nhận"):
        for y1, y2, t in nodes:
            if t.startswith(kw) and y1 > 1600:
                cy = (y1 + y2) // 2
                adb.shell(["input", "tap", "540", str(cy)])
                print(f"[m26] bam {t!r} y={cy}")
                time.sleep(3)
                nodes = dump(adb)
                labels2 = sorted({t for _, _, t in nodes if t and len(t) < 60})
                print(f"[m26] MAN SAU: {labels2[:16]}")
                raise SystemExit
finally:
    lock.release()
