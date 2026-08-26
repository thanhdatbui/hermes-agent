# -*- coding: utf-8 -*-
"""m44: vao Tài khoản -> Bao mat -> Xac minh hai buoc de xem trang thai 2FA."""
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")

from automation_core.adb import AdbClient
from automation_core.device_lock import acquire_device_lock
from automation_core.persistent_ui import capture_atx_session_ui
import xml.etree.ElementTree as ET

sys.path.insert(0, r"C:\Users\Kibe\AppData\Local\hermes\scripts")
from f2a_otp_gmail_flow import tap_text, texts_of  # noqa: E402

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"

machine, serial = 44, "ce041604e3517c0a05"
lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    adb = AdbClient(adb_path=ADB, serial=serial)
    xml = capture_atx_session_ui(adb, timeout=15).xml
    if not tap_text(adb, xml, "Tài khoản"):
        print("[m44] khong thay Tai khoan")
        raise SystemExit
    time.sleep(2.5)
    xml = capture_atx_session_ui(adb, timeout=15).xml
    ts = texts_of(xml)
    print("[m44] man Tai khoan:", ts[:10])
    # Bao mat thuong o day
    if tap_text(adb, xml, "Bảo mật"):
        time.sleep(2.5)
        xml = capture_atx_session_ui(adb, timeout=15).xml
        ts2 = texts_of(xml)
        print("[m44] man Bao mat:", ts2[:12])
        if tap_text(adb, xml, "Xác minh hai bước", "Xác minh 2 bước"):
            time.sleep(2.5)
            out = texts_of(capture_atx_session_ui(adb, timeout=15).xml)
            print("[m44] man 2 step:", out[:12])
finally:
    lock.release()
