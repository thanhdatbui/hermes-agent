# -*- coding: utf-8 -*-
"""m26: 2FA dang TAT, co Email + Mat khau. Bam BAT -> chon Email (neu hoi) -> Tiep
-> OTP ve Gmail app -> doc -> nhap."""
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
from datetime import datetime, timedelta

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
KEYCODE = {c: 7 + i for i, c in enumerate("0123456789")}
machine, serial = 26, "ce081608c4e3ed1e05"
mail_acc = "tranthimy150820011508@gmail.com"


def dump(adb):
    cap = capture_atx_session_ui(adb, timeout=20)
    xml_text = getattr(cap, "xml", None)
    if not xml_text:
        return []
    root = ET.fromstring(xml_text)
    out = []
    for n in root.iter("node"):
        b = n.attrib.get("bounds", "")
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b or "")
        if not m:
            continue
        t = n.attrib.get("text", "") or n.attrib.get("content-desc", "")
        out.append((int(m.group(2)), int(m.group(4)), t[:70]))
    return out


def row_center(nodes, label):
    for y1, y2, t in nodes:
        if label in t and y1 > 200:
            return (y1 + y2) // 2
    return None


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

    # 1. Bam nut BAT (y 1752-1908 center ~1830)
    adb.shell(["input", "tap", "540", "1830"])
    print("[m26] da bam BAT")
    time.sleep(3)
    nodes = dump(adb)
    labels = sorted({t for _, _, t in nodes if t and len(t) < 55})
    print(f"[m26] man sau BAT: {labels[:16]}")
finally:
    lock.release()
