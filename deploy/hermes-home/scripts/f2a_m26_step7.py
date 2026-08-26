# -*- coding: utf-8 -*-
"""m26: sau khi bam Email, TikTok da mo man nhap OTP (thong bao Gmail 2 thu moi).
Man hien tai co the la man OTP. Dump ky roi doc ma qua Gmail app + nhap."""
import re
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")

from automation_core.adb import AdbClient
from automation_core.device_lock import acquire_device_lock
from automation_core.persistent_ui import capture_atx_session_ui
import xml.etree.ElementTree as ET

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
KEYCODE = {c: 7 + i for i, c in enumerate("0123456789")}
machine, serial = 26, "ce081608c4e3ed1e05"
mail_acc = "tranthimy150820011508@gmail.com"


def dump(adb):
    cap = capture_atx_session_ui(adb, timeout=25)
    x = getattr(cap, "xml", None)
    if not x:
        return []
    root = ET.fromstring(x)
    out = []
    for n in root.iter("node"):
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", "") or "")
        if m:
            t = (n.attrib.get("text", "") or n.attrib.get("content-desc", ""))[:70]
            out.append((int(m.group(2)), int(m.group(4)), t))
    return out


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    adb = AdbClient(adb_path=ADB, serial=serial)

    # Load social_reg_v1
    sys.path.insert(0, r"D:\Taadaa\Tiktok_Reg")
    import importlib.util
    spec = importlib.util.spec_from_file_location("social_reg_v1", r"D:\Taadaa\Tiktok_Reg\social_reg_v1.py")
    social = importlib.util.module_from_spec(spec)
    sys.modules["social_reg_v1"] = social
    try:
        spec.loader.exec_module(social)
    except SystemExit:
        pass
    from datetime import datetime, timedelta
    nb = datetime.now() - timedelta(seconds=45)

    # Doc ma qua Gmail app tren may
    code = social._try_get_otp_gmail_app(serial, mail_acc, not_before=nb)
    if not code:
        print("[m26] KHONG lay duoc ma tu Gmail app")
        raise SystemExit(1)
    print(f"[m26] co ma (len={len(code)})")

    # Quay lai TikTok
    adb.shell(["am", "force-stop", "com.google.android.gm"])
    time.sleep(1.5)
    adb.shell(["am", "start", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", "-p", "com.ss.android.ugc.trill", "--activity-brought-to-front"])
    time.sleep(4)

    nodes = dump(adb)
    labels = [t for _, _, t in nodes if t]
    print(f"[m26] man quay lai: {labels[:8]}")

    # Neu van o man chon method -> bam row email + nut Tiep duoi cung
    if any("Phương thức xác minh" in t for t in labels):
        adb.shell(["input", "tap", "540", "1033"])  # row Email
        time.sleep(2)
        nodes = dump(adb)
        for y1, y2, t in nodes:
            if t.startswith(("Tiếp", "Bật")) and y1 > 1700:
                adb.shell(["input", "tap", "540", str((y1 + y2) // 2)])
                break
        time.sleep(3)
        nodes = dump(adb)
        labels = [t for _, _, t in nodes if t]
        print(f"[m26] man sau bam Tiep: {labels[:8]}")

    # Neu o man nhap OTP -> tap vung nhap + go keyevent
    if any("Nhập mã" in t or "mã gồm" in t for t in labels):
        adb.shell(["input", "tap", "540", "700"])
        time.sleep(1.5)
        for ch in code:
            adb.shell(["input", "keyevent", str(KEYCODE[ch])])
            time.sleep(0.35)
        time.sleep(2)
        nodes = dump(adb)
        labels = sorted({t for _, _, t in nodes if t and len(t) < 60})
        print(f"[m26] SAU NHAP MA: {labels[:14]}")
finally:
    lock.release()
