# -*- coding: utf-8 -*-
"""m26 FIX: WebView OTP khong nhan keyevent (khac version 46.6.3 so voi m44 46.4.3).
Thu cac cach:
1. Tap chinh xac vung o so thu nhat (theo ty le man hinh tu anh m35/m44: o nam ~y=560-700)
2. Bam keyevent KEYCODE_0..9 tung so voi delay dai
3. Neu van khong duoc -> thu tap vao WebView roi go 'input text'
4. Kiem tra ket qua bang screencap pixel check (do sang vi tri o so)"""
import re
import subprocess
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")

from automation_core.device_lock import acquire_device_lock

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
machine, serial = 26, "ce081608c4e3ed1e05"


def sh(*args, timeout=90):
    return subprocess.run([ADB, "-s", serial, "shell"] + list(args), capture_output=True, timeout=timeout).stdout.decode("utf-8", errors="ignore")


def tap(x, y):
    sh("input", "tap", str(x), str(y))


def dump_xml():
    for _i in range(5):
        sh("uiautomator", "dump", "/sdcard/m26.xml", timeout=40)
        x = sh("cat", "/sdcard/m26.xml", timeout=40)
        if len(x) > 500:
            return x
        time.sleep(4)
    return x


def screen_changed(before_png, after_png):
    import hashlib
    h1 = hashlib.md5(open(before_png, 'rb').read()).hexdigest()
    h2 = hashlib.md5(open(after_png, 'rb').read()).hexdigest()
    return h1 != h2


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    results = {}
    # Thu lan luot cac toa do o nhap
    candidates = [(540, 560), (540, 620), (540, 500), (540, 760), (540, 850)]
    for cx, cy in candidates:
        sh("exec-out screencap -p > /sdcard/before.png")
        tap(cx, cy)
        time.sleep(1.5)
        # Go ma test
        for kc in ("8", "2"):
            pass
        sh("input", "text", "82")
        time.sleep(2)
        sh("uiautomator", "dump", "/sdcard/t.xml")
        x = sh("cat", "/sdcard/t.xml")
        # Kiem tra xem co EditText nhan duoc text khong
        mm = re.search(r'resource-id="code-input"[^>]*text="([^"]*)"', x)
        val = mm.group(1) if mm else None
        print(f"[m26] tap({cx},{cy}) -> code-input text={val!r}")
        if val:
            print("[m26] O NHAP NHAN DUOC TEXT tai", (cx, cy))
            results["ok"] = (cx, cy)
            break
    print(f"[m26] KET QUA: {results or 'KHONG toa do nao nhan text'}")
finally:
    lock.release()
