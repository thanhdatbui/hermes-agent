# -*- coding: utf-8 -*-
"""BACK m22 ve man chon method (dang o man nhap OTP 6 so) - de tranh kich hoat ma that su."""
import sys
import time

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
    adb.shell(["input", "keyevent", "4"])
    time.sleep(2.5)
    xml = capture_atx_session_ui(adb, timeout=12).xml
    root = ET.fromstring(xml)
    ts = [n.attrib.get("text", "") for n in root.iter("node") if n.attrib.get("text", "")]
    print("Sau Back:", ts[:10])
finally:
    lock.release()
