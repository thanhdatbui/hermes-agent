# -*- coding: utf-8 -*-
"""m26 ket luan: 2FA DA BAT (Email + Mat khau). Trinh xac thuc con TAT -> bat them
Trinh xac thuc (y=1228) de chuan hoa theo quy trinh: Authenticator ON, Email OFF, SMS OFF.
Luu secret vao cot E neu sinh moi."""
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
    # Bam row Trình xác thực
    adb.shell(["input", "tap", "540", "1290"])
    print("[m26] bam Trình xác thực")
    time.sleep(3)
    cap = capture_atx_session_ui(adb, timeout=25)
    root = ET.fromstring(getattr(cap, "xml") or "<r/>")
    labels = []
    for n in root.iter("node"):
        t = (n.attrib.get("text", "") or n.attrib.get("content-desc", ""))
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", "") or "")
        if t and m and len(t) < 60:
            labels.append((int(m.group(2)), t))
    for y, t in sorted(set(labels))[:16]:
        print(f"  y={y}: {t!r}")
finally:
    lock.release()
