# -*- coding: utf-8 -*-
"""Ket luan verify OTP cho m35 + m44: bam 'Khong' dong popup spam, kiem tra man hien tai
co phai da qua xac minh (ve man bao mat / thong tin tai khoan) khong."""
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

for machine, serial in [(35, "ce061606c3322c1603"), (44, "ce041604e3517c0a05")]:
    lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
    try:
        adb = AdbClient(adb_path=ADB, serial=serial)
        xml = capture_atx_session_ui(adb, timeout=15).xml
        ts = texts_of(xml)
        if any("thư rác" in t for t in ts):
            tap_text(adb, xml, "Không")
            time.sleep(2)
        out = texts_of(capture_atx_session_ui(adb, timeout=15).xml)
        print(f"[m{machine}] man hien tai: {out[:8]}")
        # BACK de ve TikTok neu con o Gmail
        if any("Gmail" in t for t in out) or any("Inbox" in t for t in out):
            adb.shell(["input", "keyevent", "4"])
            time.sleep(2)
    finally:
        lock.release()
