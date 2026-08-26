# -*- coding: utf-8 -*-
"""m22: tap vao row email trong ListView (y~657-711) xem co chuyen sang man nhap pass khong.
Gia thuy: TikTok chi goi y 1 method duy nhat (email masked) - khong co lua chon Mat khau."""
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
    # Tap trung row method (540, 680)
    adb.shell(["input", "tap", "540", "680"])
    time.sleep(1.5)
    xml = capture_atx_session_ui(adb, timeout=12).xml
    root = ET.fromstring(xml)
    ts = [n.attrib.get("text", "") for n in root.iter("node") if n.attrib.get("text", "")]
    print("Sau tap row:", ts[:10])
    fields = [n for n in root.iter("node") if n.attrib.get("class") == "android.widget.EditText"]
    print("So EditText:", len(fields))
finally:
    lock.release()
