# -*- coding: utf-8 -*-
"""m44: da qua het OTP + doi pass. Kiem tra trang thai cuoi: vao Security & permissions
xem 2FA (Trinh xac thuc) co BAT chua, email/phone da TAT chua."""
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
    # Dang o man Thong tin tai khoan -> BACK ve Bao mat
    adb.shell(["input", "keyevent", "4"])
    time.sleep(2)
    xml = capture_atx_session_ui(adb, timeout=15).xml
    ts = texts_of(xml)
    print("[m44] sau BACK:", ts[:8])
    if any("Bảo mật" in t for t in ts):
        if tap_text(adb, xml, "Bảo mật"):
            time.sleep(2)
            xml = capture_atx_session_ui(adb, timeout=15).xml
            tap_text(adb, xml, "Xác minh hai bước", "Bảo mật và quyền riêng tư")
            time.sleep(2.5)
            out = texts_of(capture_atx_session_ui(adb, timeout=15).xml)
            print("[m44] man 2 step:", out[:12])
finally:
    lock.release()
