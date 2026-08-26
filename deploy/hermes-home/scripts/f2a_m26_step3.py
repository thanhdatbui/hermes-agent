# -*- coding: utf-8 -*-
"""m26: man 2 buoc hien Email + Mat khau (da du 2 method, Email ON).
Nhiem vu: TAT Email + BAT Trinh xac thuc? KHONG - muc tieu: bat XAC MINH 2 BUOC voi
Email + Mat khau la du. Kiem tra toggle hien tai roi bam nut Bat/Xong neu can."""
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


def dump_full(adb):
    cap = capture_atx_session_ui(adb, timeout=20)
    xml_text = getattr(cap, "xml", None)
    if not xml_text:
        return None
    return ET.fromstring(xml_text)


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    adb = AdbClient(adb_path=ADB, serial=serial)
    root = dump_full(adb)
    print("[m26] chi tiet node co text/checkable:")
    for n in root.iter("node"):
        t = n.attrib.get("text", "") or ""
        chk = n.attrib.get("checked", "")
        cls = n.attrib.get("class", "").split(".")[-1]
        if t and len(t) < 50 and ("Bật" in t or "Tắt" in t or "Email" in t or "Mật khẩu" in t or "Xác minh" in t):
            b = n.attrib.get("bounds", "")
            print(f"  {cls} checked={chk}: {t!r} {b}")
finally:
    lock.release()
