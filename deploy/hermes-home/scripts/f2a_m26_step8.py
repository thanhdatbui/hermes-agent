# -*- coding: utf-8 -*-
"""m26: TikTok doi NHAP EMAIL de nhan ma (man 'Nhập email').
Go email cua nick -> Tiep -> OTP ve Gmail app -> doc -> nhap."""
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
from f2a_otp_gmail_flow import type_escaped

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
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
            out.append((int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), t))
    return out


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    adb = AdbClient(adb_path=ADB, serial=serial)

    # Tap o nhap email (thuong o tren, y ~600-800). Thu tap vung 'Nhập email'
    nodes = dump(adb)
    target = None
    for x1, y1, x2, y2, t in nodes:
        if "Nhập email" in t:
            target = ((x1 + x2) // 2, (y1 + y2) // 2)
            break
    if not target:
        print(f"[m26] khong thay Nhập email: {[t for *_ , t in nodes[:10]]}")
        raise SystemExit(1)
    adb.shell(["input", "tap", str(target[0]), str(target[1])])
    time.sleep(1.5)
    type_escaped(adb, mail_acc)
    time.sleep(1.5)
    # Bam Tiep / Tiep theo (nut o duoi man hoac ban phim)
    nodes = dump(adb)
    pressed = False
    for kw in ("Tiếp theo", "Tiếp tục", "Tiếp"):
        for x1, y1, x2, y2, t in nodes:
            if t.startswith(kw):
                adb.shell(["input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2)])
                print(f"[m26] bam {t!r}")
                pressed = True
                break
        if pressed:
            break
    if not pressed:
        adb.shell(["input", "keyevent", "66"])  # Enter
        print("[m26] bam Enter")
    time.sleep(4)
    nodes = dump(adb)
    labels = sorted({t for *_, t in nodes if t and len(t) < 60})
    print(f"[m26] MAN SAU NHAP EMAIL: {labels[:16]}")
finally:
    lock.release()
