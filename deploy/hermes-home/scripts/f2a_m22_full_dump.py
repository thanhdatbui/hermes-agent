# -*- coding: utf-8 -*-
"""Dump FULL XML node tree (mọi class) cho m22 để thấy method rows bị ẩn ở đâu."""
import sys

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")

from automation_core.adb import AdbClient
from automation_core.device_lock import acquire_device_lock
from automation_core.persistent_ui import capture_atx_session_ui
import xml.etree.ElementTree as ET

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"

machine, serial = 22, "ce02182210b8607b0c"
adb = AdbClient(adb_path=ADB, serial=serial)
lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    xml = capture_atx_session_ui(adb, timeout=15).xml
    # luu file de xem nguyen van
    with open(r"C:\Users\Kibe\AppData\Local\hermes\scripts\f2a_m22_verify_dump.xml", "w", encoding="utf-8") as f:
        f.write(xml)
    root = ET.fromstring(xml)
    print("Tong so node:", len(list(root.iter("node"))))
    for n in root.iter("node"):
        a = n.attrib
        cls = (a.get("class") or "").split(".")[-1]
        txt = a.get("text", "")
        desc = a.get("content-desc", "")
        res = a.get("resource-id", "")
        clickable = a.get("clickable")
        if txt or desc or clickable == "true":
            print(f"{cls} clk={clickable}: t={txt!r} d={desc!r} rid={res} b={a.get('bounds')}")
finally:
    lock.release()
