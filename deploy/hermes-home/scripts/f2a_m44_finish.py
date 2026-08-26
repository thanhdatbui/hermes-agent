# -*- coding: utf-8 -*-
"""m44: dang con o Gmail (email mo). BACK + force-stop Gmail -> mo TikTok -> nhap OTP."""
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
from f2a_otp_gmail_flow import tap_text, texts_of, bounds_center, type_escaped  # noqa: E402

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"

machine, serial = 44, "ce041604e3517c0a05"
lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    adb = AdbClient(adb_path=ADB, serial=serial)
    # Doc ma tu email DANG MO tren man hinh (subject chua ma 6 so)
    xml = capture_atx_session_ui(adb, timeout=15).xml
    root = ET.fromstring(xml)
    all_text = " ".join(n.attrib.get("text", "") for n in root.iter("node"))
    codes = re.findall(r"(?<!\d)(\d{6})(?!\d)", all_text)
    print("[m44] ma thay trong man:", codes[:3])
    if not codes:
        raise SystemExit("khong co ma tren man")

    # Thoat Gmail: BACK x2 roi force-stop
    adb.shell(["input", "keyevent", "4"])
    time.sleep(1.5)
    adb.shell(["am", "force-stop", "com.google.android.gm"])
    time.sleep(1.5)

    # Mo TikTok
    adb.shell(["am", "start", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", "-p", "com.ss.android.ugc.trill", "--activity-brought-to-front"])
    time.sleep(4)
    xml = capture_atx_session_ui(adb, timeout=15).xml
    ts = texts_of(xml)
    print("[m44] man TikTok:", ts[:7])

    if any("Nhập mã gồm 6 chữ số" in t for t in ts):
        root = ET.fromstring(capture_atx_session_ui(adb, timeout=12).xml)
        fields = [
            n for n in root.iter("node")
            if n.attrib.get("class") == "android.widget.EditText" and n.attrib.get("enabled") != "false"
        ]
        print("[m44] so EditText:", len(fields))
        if fields:
            x, y = bounds_center(fields[0].attrib["bounds"])
            adb.shell(["input", "tap", str(x), str(y)])
            time.sleep(1.0)
            type_escaped(adb, codes[0])
            time.sleep(1.5)
            xml2 = capture_atx_session_ui(adb, timeout=12).xml
            tap_text(adb, xml2, "Tiếp", "Xác nhận", "Tiếp tục")
            time.sleep(4)
        out = texts_of(capture_atx_session_ui(adb, timeout=15).xml)
        err = [t for t in out if "không đúng" in t.lower() or "hết hạn" in t.lower()]
        print(f"[m44] {'LOI: ' + err[0][:50] if err else 'SAU NHAP: ' + str(out[:8])}")
finally:
    lock.release()
