# -*- coding: utf-8 -*-
"""m35: van o man nhap OTP. Bam 'Gui lai ma' -> dung _try_get_otp_gmail_app lay ma moi
-> force-stop Gmail -> mo TikTok -> tap vung nhap (540,700) -> go ma bang keyevent."""
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

from datetime import datetime, timedelta  # noqa: E402

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
KEYCODE = {c: 7 + i for i, c in enumerate("0123456789")}
machine, serial = 35, "ce061606c3322c1603"
mail_acc = "buithanhtruc010120010101@gmail.com"


def texts_of(xml_text):
    root = ET.fromstring(xml_text)
    return [n.attrib.get("text", "") for n in root.iter("node") if n.attrib.get("text", "")]


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    adb = AdbClient(adb_path=ADB, serial=serial)

    # Load social_reg_v1 de dung Gmail app reader
    sys.path.insert(0, r"D:\Taadaa\Tiktok_Reg")
    import importlib.util
    spec = importlib.util.spec_from_file_location("social_reg_v1", r"D:\Taadaa\Tiktok_Reg\social_reg_v1.py")
    social = importlib.util.module_from_spec(spec)
    sys.modules["social_reg_v1"] = social
    try:
        spec.loader.exec_module(social)
    except SystemExit:
        pass

    not_before_dt = datetime.now() - timedelta(seconds=30)

    # 1. Bam Gui lai ma (o y~741)
    adb.shell(["input", "tap", "540", "790"])
    print("[m35] bam Gui lai ma, doi mail...")
    time.sleep(8)

    # 2. Doc ma qua Gmail app
    code = social._try_get_otp_gmail_app(serial, mail_acc, not_before=not_before_dt)
    if not code:
        print("[m35] KHONG lay duoc ma moi")
        raise SystemExit(1)
    print(f"[m35] co ma moi (len={len(code)})")

    # 3. Thoat Gmail bang force-stop, mo TikTok
    adb.shell(["am", "force-stop", "com.google.android.gm"])
    time.sleep(1.5)
    adb.shell(["am", "start", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", "-p", "com.ss.android.ugc.trill", "--activity-brought-to-front"])
    time.sleep(4)

    xml = capture_atx_session_ui(adb, timeout=15).xml
    ts = texts_of(xml)
    if not any("Nhập mã gồm 6 chữ số" in t for t in ts):
        print(f"[m35] khong con man OTP? Man: {ts[:6]}")
        raise SystemExit(1)

    # 4. Tap vung o nhap + go bang keyevent
    adb.shell(["input", "tap", "540", "700"])
    time.sleep(1.5)
    for ch in code:
        adb.shell(["input", "keyevent", str(KEYCODE[ch])])
        time.sleep(0.35)
    time.sleep(1.5)

    xml = capture_atx_session_ui(adb, timeout=15).xml
    root = ET.fromstring(xml)
    out = []
    for n in root.iter("node"):
        t = n.attrib.get("text", "") or ""
        b = n.attrib.get("bounds", "")
        if t:
            m = re.match(r"\[(\d+),(\d+)\]", b)
            if m and int(m.group(2)) > 150:
                out.append((int(m.group(2)), t[:50]))
    print("[m35] sau khi go ma:")
    for y, t in sorted(out)[:10]:
        print(f"  y={y}: {t!r}")
finally:
    lock.release()
