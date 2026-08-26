# -*- coding: utf-8 -*-
"""m41: secret Authenticator = STDLRCO4SUSHDLVXO32E6ZEZBAEWIXQX.
Tiep -> nhap TOTP -> luu secret vao cot E workbook."""
import base64
import hashlib
import hmac
import re
import struct
import subprocess
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")

from automation_core.device_lock import acquire_device_lock

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
KEYCODE = {c: 7 + i for i, c in enumerate("0123456789")}
machine, serial = 41, "ce031823f9b1903c01"
SECRET = "STDLRCO4SUSHDLVXO32E6ZEZBAEWIXQX"


def sh(*args):
    return subprocess.run([ADB, "-s", serial, "shell"] + list(args), capture_output=True, timeout=40).stdout.decode("utf-8", errors="ignore")


def tap(x, y):
    sh("input", "tap", str(x), str(y))


def dump_xml():
    sh("uiautomator", "dump", "/sdcard/m41.xml")
    return sh("cat", "/sdcard/m41.xml")


def totp_now(secret_b32):
    key = base64.b32decode(secret_b32 + "=" * (-len(secret_b32) % 8))
    counter = int(time.time()) // 30
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    off = digest[-1] & 0x0F
    return f"{(struct.unpack('>I', digest[off:off+4])[0] & 0x7FFFFFFF) % 1000000:06d}"


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    # Scroll xuong nut Tiếp (o duoi)
    sh("input", "swipe", "540", "1500", "540", "700", "400")
    time.sleep(1.5)
    x = dump_xml()
    mm = re.search(r'text="Tiếp"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x)
    if mm:
        cy = (int(mm.group(2)) + int(mm.group(4))) // 2
        print(f"[m41] bam TIEP y={cy}")
        tap(540, cy)
        time.sleep(3)

    # Man nhap ma: cho dau chu ky de ma con han lau
    wait = 30 - (int(time.time()) % 30)
    if wait < 10:
        time.sleep(wait)
    code = totp_now(SECRET)
    print(f"[m41] TOTP len={len(code)}")
    tap(540, 700)
    time.sleep(1.5)
    for ch in code:
        sh("input", "keyevent", str(KEYCODE[ch]))
        time.sleep(0.35)
    time.sleep(2)

    x = dump_xml()
    texts = sorted(set(re.findall(r'text="([^"]{2,60})"', x)))
    print(f"[m41] SAU NHAP MA AUTH: {[t for t in texts if not t.startswith(('14:', '89%', 'Chuông', 'Thông', 'Đang', 'Tín'))][:16]}")
finally:
    lock.release()
