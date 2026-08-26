# -*- coding: utf-8 -*-
"""Dump XML các máy EditText count=0 để xem màn hình thực tế (keyboard che?)."""
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")

from automation_core.adb import AdbClient
from automation_core.device_lock import acquire_device_lock
from automation_core.persistent_ui import capture_atx_session_ui
import xml.etree.ElementTree as ET

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"

MACHINES = [
    (22, "ce02182210b8607b0c"),
    (27, "ce031823912ae0d20c"),
    (44, "ce041604e3517c0a05"),
]

for machine, serial in MACHINES:
    adb = AdbClient(adb_path=ADB, serial=serial)
    lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
    try:
        xml = capture_atx_session_ui(adb, timeout=12).xml
        root = ET.fromstring(xml)
        nodes = list(root.iter("node"))
        print(f"=== m{machine} ({serial}) ===")
        for n in nodes:
            a = n.attrib
            cls = a.get("class", "")
            txt = (a.get("text") or "").strip()
            desc = (a.get("content-desc") or "").strip()
            if txt or desc or "EditText" in cls or "Button" in cls:
                pwd_flag = " [PWD]" if a.get("password") == "true" else ""
                focused = " [FOCUSED]" if a.get("focused") == "true" else ""
                print(f"  {cls}{pwd_flag}{focused}: text={txt!r} desc={desc!r} bounds={a.get('bounds')}")
    finally:
        lock.release()
