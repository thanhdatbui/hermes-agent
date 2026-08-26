# -*- coding: utf-8 -*-
"""m44: man OTP khong co EditText trong XML -> cac o nhap la WebView.
Thu: tap truc tiep vung o nhap (duoi tieu de), roi go so bang keyevent (so 0-9)."""
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")

from automation_core.adb import AdbClient
from automation_core.device_lock import acquire_device_lock
from automation_core.persistent_ui import capture_atx_session_ui
import xml.etree.ElementTree as ET

sys.path.insert(0, r"C:\Users\Kibe\AppData\Local\hermes\scripts")
from f2a_otp_gmail_flow import tap_text, texts_of, bounds_center  # noqa: E402

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
KEYCODE = {c: 7 + i for i, c in enumerate("0123456789")}

machine, serial, code = 44, "ce041604e3517c0a05", "241605"
lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    adb = AdbClient(adb_path=ADB, serial=serial)
    # Dump ky hon: tim moi thu co bounds nam giua title (~500) va nut Gui lai
    xml = capture_atx_session_ui(adb, timeout=15).xml
    root = ET.fromstring(xml)
    print("Cac node clickable / EditText:")
    for n in root.iter("node"):
        a = n.attrib
        cls = a.get("class", "")
        b = a.get("bounds", "")
        if not b:
            continue
        m = __import__("re").match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
        y1 = int(m.group(2))
        if a.get("clickable") == "true" or "EditText" in cls:
            print(f"  {cls.split('.')[-1]} clk={a.get('clickable')} focus={a.get('focused')} text={(a.get('text') or '')[:20]!r} desc={(a.get('content-desc') or '')[:30]!r} y={y1} b={b}")
finally:
    lock.release()
