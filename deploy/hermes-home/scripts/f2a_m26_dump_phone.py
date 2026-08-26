# -*- coding: utf-8 -*-
"""m26: man 'Them dien thoai' bat buoc. Bam BỎ QUA bang toa do chinh xac (nut o tren ben phai,
thuong y ~600-700 hoac canh nut Them dien thoai). Dump bounds day de biet."""
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

lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    adb = AdbClient(adb_path=ADB, serial=serial)
    cap = capture_atx_session_ui(adb, timeout=25)
    root = ET.fromstring(getattr(cap, "xml") or "<r/>")
    print("FULL NODES:")
    for n in root.iter("node"):
        t = (n.attrib.get("text", "") or n.attrib.get("content-desc", ""))
        b = n.attrib.get("bounds", "")
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b or "")
        if m and (t or n.attrib.get("clickable") == "true"):
            y1, y2 = int(m.group(2)), int(m.group(4))
            if y1 > 300:
                cx = (int(m.group(1)) + int(m.group(3))) // 2
                print(f"  ({cx},{(y1+y2)//2}) clk={n.attrib.get('clickable')}: {t[:50]!r}")
finally:
    lock.release()
