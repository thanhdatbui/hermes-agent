# -*- coding: utf-8 -*-
"""m44: van o man nhap OTP -> bam 'Gửi lại mã' roi dung Gmail app doc ma moi, nhap lai.
m35: TikTok khong mo duoc (dang mac o Gmail) -> force-stop Gmail roi mo TikTok."""
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
from datetime import datetime, timedelta  # noqa: E402

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"

machine, serial, mail_acc = 44, "ce041604e3517c0a05", "vuthithao090919970909@gmail.com"
lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    adb = AdbClient(adb_path=ADB, serial=serial)
    xml = capture_atx_session_ui(adb, timeout=15).xml
    not_before_dt = datetime.now() - timedelta(seconds=30)
    if tap_text(adb, xml, "Gửi lại mã"):
        print("[m44] da bam Gui lai ma, doi mail den...")
        time.sleep(8)

    import importlib.util
    sys.path.insert(0, r"D:\Taadaa\Tiktok_Reg")
    spec = importlib.util.spec_from_file_location("social_reg_v1", r"D:\Taadaa\Tiktok_Reg\social_reg_v1.py")
    social = importlib.util.module_from_spec(spec)
    sys.modules["social_reg_v1"] = social
    try:
        spec.loader.exec_module(social)
    except SystemExit:
        pass

    code = social._try_get_otp_gmail_app(serial, mail_acc, not_before=not_before_dt)
    if code:
        print(f"[m44] co ma moi, quay lai TikTok...")
        adb.shell(["am", "start", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", "-p", "com.ss.android.ugc.trill", "--activity-brought-to-front"])
        time.sleep(3.5)
        root = ET.fromstring(capture_atx_session_ui(adb, timeout=15).xml)
        ts = texts_of(xml)
        fields = [
            n for n in root.iter("node")
            if n.attrib.get("class") == "android.widget.EditText" and n.attrib.get("enabled") != "false"
        ]
        print(f"[m44] EditText: {len(fields)} | man: {texts_of(capture_atx_session_ui(adb, timeout=12).xml)[:6]}")
        if fields:
            x, y = bounds_center(fields[0].attrib["bounds"])
            adb.shell(["input", "tap", str(x), str(y)])
            time.sleep(1.0)
            type_escaped(adb, code)
            time.sleep(1.5)
            xml2 = capture_atx_session_ui(adb, timeout=12).xml
            tap_text(adb, xml2, "Tiếp", "Xác nhận", "Tiếp tục")
            time.sleep(4)
        out = texts_of(capture_atx_session_ui(adb, timeout=15).xml)
        err = [t for t in out if "không đúng" in t.lower() or "hết hạn" in t.lower()]
        print(f"[m44] {'LOI: ' + err[0][:50] if err else 'SAU NHAP: ' + str(out[:7])}")
    else:
        print("[m44] khong lay duoc ma moi")
finally:
    lock.release()
