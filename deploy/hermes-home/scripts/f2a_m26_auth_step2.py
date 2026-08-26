# -*- coding: utf-8 -*-
"""m26: man nhap ma Authenticator. Sinh TOTP tu secret, nhap bang keyevent (WebView)."""
import base64
import hashlib
import hmac
import re
import struct
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
SECRET = "YVMBCRZ2UEZTRGD632KGNF66RBIQRDJE"


def totp_now(secret_b32: str) -> str:
    key = base64.b32decode(secret_b32 + "=" * (-len(secret_b32) % 8))
    counter = int(time.time()) // 30
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1000000
    return f"{code_int:06d}"


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
    # cho den giua chu ky 30s de ma con han dai
    wait = 30 - (int(time.time()) % 30)
    if wait < 10:
        time.sleep(wait)
    code = totp_now(SECRET)
    print(f"[m26] TOTP sinh: len={len(code)}")
    adb.shell(["input", "tap", "540", "700"])
    time.sleep(1.5)
    for ch in code:
        adb.shell(["input", "keyevent", str(KEYCODE[ch])])
        time.sleep(0.35)
    time.sleep(2)
    nodes = dump(adb)
    labels = sorted({t for _, _, t in nodes if t and len(t) < 60})
    print(f"[m26] SAU NHAP MA AUTH: {labels[:14]}")
finally:
    lock.release()
