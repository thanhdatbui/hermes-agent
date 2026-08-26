# -*- coding: utf-8 -*-
"""Probe màn 'Xác minh danh tính' variant method-choice: thử scroll + dump lại xem có row Mật khẩu không."""
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")

from automation_core.adb import AdbClient
from automation_core.device_lock import acquire_device_lock
from automation_core.persistent_ui import capture_atx_session_ui
import xml.etree.ElementTree as ET

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"


def texts_of(xml_text):
    root = ET.fromstring(xml_text)
    return [(n.attrib.get("text", "") or n.attrib.get("content-desc", "")) for n in root.iter("node")]


MACHINES = [
    (22, "ce02182210b8607b0c"),
    (27, "ce031823912ae0d20c"),
    (44, "ce041604e3517c0a05"),
]

for machine, serial in MACHINES:
    adb = AdbClient(adb_path=ADB, serial=serial)
    lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
    try:
        # Thu 1: cho dai hon roi dump lai (co the list chua load)
        time.sleep(2)
        ts = texts_of(capture_atx_session_ui(adb, timeout=12).xml)
        has_method = any(t == "Mật khẩu" for t in ts)
        print(f"[m{machine}] sau khi cho: co row 'Mat khau'? {has_method} | texts={ts[:12]}")

        if not has_method:
            # Thu 2: vuot len nhe trong vung list de load lazy
            adb.shell(["input", "swipe", "540", "1400", "540", "800", "400"])
            time.sleep(2)
            ts = texts_of(capture_atx_session_ui(adb, timeout=12).xml)
            has_method = any(t == "Mật khẩu" for t in ts)
            print(f"[m{machine}] sau vuot: co row 'Mat khau'? {has_method} | texts={ts[:14]}")

        if not has_method:
            # Thu 3: bam Back de an ban phim neu dang mo roi dump
            adb.shell(["input", "keyevent", "4"])
            time.sleep(1.5)
            ts = texts_of(capture_atx_session_ui(adb, timeout=12).xml)
            has_method = any(t == "Mật khẩu" for t in ts)
            print(f"[m{machine}] sau Back: co row 'Mat khau'? {has_method} | texts={ts[:14]}")
    finally:
        lock.release()
