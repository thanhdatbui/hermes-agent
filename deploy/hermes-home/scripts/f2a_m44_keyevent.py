# -*- coding: utf-8 -*-
"""m44: man OTP chi co Button BACK trong XML (WebView khong expose).
Chien luoc: tap vung giua man (o nhap OTP thuong nam y ~600-800) -> ban phim so mo
-> go ma bang keyevent KEYCODE_NUM. Sau do tim nut Tiep."""
import re
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
KEYCODE = {c: 7 + i for i, c in enumerate("0123456789")}

machine, serial, code = 44, "ce041604e3517c0a05", "241605"
lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    adb = AdbClient(adb_path=ADB, serial=serial)
    # 1. Tap vung o nhap (giua title va nut Gui lai): thu (540, 700)
    adb.shell(["input", "tap", "540", "700"])
    time.sleep(1.5)
    # 2. Go ma bang keyevent (hoat dong ca khi WebView)
    for ch in code:
        adb.shell(["input", "keyevent", str(KEYCODE[ch])])
        time.sleep(0.35)
    time.sleep(1.5)
    # 3. Dump lai xem trang thai
    xml = capture_atx_session_ui(adb, timeout=15).xml
    ts = texts_of(xml)
    print("[m44] sau khi go:", ts[:8])
    # 4. Bam Tiep neu xuat hien
    if not tap_text(adb, xml, "Tiếp"):
        # nut Tiep co the la WebView -> tap vung duoi cung (540, ~1500)
        adb.shell(["input", "tap", "540", "1500"])
        time.sleep(3)
        xml = capture_atx_session_ui(adb, timeout=15).xml
        ts = texts_of(xml)
        print("[m44] sau tap Tiep-fallback:", ts[:8])
    out = texts_of(capture_atx_session_ui(adb, timeout=15).xml)
    err = [t for t in out if "không đúng" in t.lower() or "hết hạn" in t.lower()]
    print(f"[m44] {'LOI: ' + err[0][:50] if err else 'KET QUA: ' + str(out[:8])}")
finally:
    lock.release()
