# -*- coding: utf-8 -*-
"""m26 CHAY LAI TU DAU theo yeu cau user:
1. Force-stop TikTok -> mo lai -> Ho so -> Cai dat -> Tai khoan -> Mat khau
2. Man Xac minh danh tinh: email da duoc chon san (radio do) -> bam Tiep
3. Doc OTP Gmail app -> quay lai
4. O man nhap 6 so: thu tung vi tri tap + keyevent tung so
   - Test bang MA SAI truoc (000000): neu bao loi => phim vao that
5. Bao cao trang thai tung buoc"""
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")
sys.path.insert(0, r"D:\Taadaa\Tiktok_Reg")

from automation_core.device_lock import acquire_device_lock

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
KEYCODE = {c: 7 + i for i, c in enumerate("0123456789")}
machine, serial = 26, "ce081608c4e3ed1e05"
mail_acc = "tranthimy150820011508@gmail.com"


def sh(*args, timeout=120):
    return subprocess.run([ADB, "-s", serial, "shell"] + list(args), capture_output=True, timeout=timeout).stdout.decode("utf-8", errors="ignore")


def tap(x, y):
    sh("input", "tap", str(x), str(y))


def dump_xml():
    x = ""
    for _i in range(5):
        sh("uiautomator", "dump", "/sdcard/m26.xml", timeout=40)
        x = sh("cat", "/sdcard/m26.xml", timeout=40)
        if len(x) > 500:
            return x
        time.sleep(4)
    return x


def texts_of(x):
    return sorted(set(re.findall(r'text="([^"]{2,90})"', x)))


def center(mm):
    return (int(mm.group(1)) + int(mm.group(3))) // 2, (int(mm.group(2)) + int(mm.group(4))) // 2


lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    # ===== BUOC 1: khoi dong lai tu dau =====
    sh("am", "force-stop", "com.ss.android.ugc.trill")
    time.sleep(3)
    sh("monkey", "-p", "com.ss.android.ugc.trill", "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(22)
    x = dump_xml()
    print("[m26] KHOI DONG:", texts_of(x)[:6])

    # Ho so neu chua o do
    if "Hồ sơ" not in x and "@quachtrang203" not in x:
        tap(972, 1883)
        time.sleep(3)
    # Menu ba cham -> Cai dat
    tap(980, 155)
    time.sleep(3.5)
    tap(623, 1248)   # Cai dat va quyen rieng tu
    time.sleep(3.5)
    x = dump_xml()
    mm = [m for m in re.finditer(r'content-desc="Tài khoản"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x)]
    if mm:
        cx, cy = center(mm[-1])
        tap(cx, cy)
    else:
        tap(540, 1791)
    time.sleep(3.5)
    # Mat khau
    x = dump_xml()
    mm = re.search(r'text="Mật khẩu"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x)
    if mm:
        cx, cy = center(mm)
        tap(cx, cy)
    else:
        tap(540, 480)
    time.sleep(4.5)
    x = dump_xml()
    print("[m26] MAN XKDT:", [t for t in texts_of(x) if len(t) < 45][:8])

    # ===== BUOC 2: Tiep (email da chon san - radio do theo anh user) =====
    if "Tiếp" in x:
        mm = re.search(r'text="Tiếp"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x)
        cx, cy = center(mm)
        tap(cx, cy)
        print(f"[m26] bam Tiep ({cx},{cy})")
        time.sleep(6)

    # ===== BUOC 3: doc OTP =====
    from social_reg_v1 import _try_get_otp_gmail_app
    nb = datetime.now() - timedelta(minutes=3)
    try:
        code = _try_get_otp_gmail_app(serial, mail_acc, not_before=nb)
    except Exception as e:
        print(f"[m26] gmail exc: {type(e).__name__}")
        code = None
    print(f"[m26] OTP: {'CO' if code else 'KHONG'}")

    sh("am", "force-stop", "com.google.android.gm")
    time.sleep(2)
    sh("monkey", "-p", "com.ss.android.ugc.trill", "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(14)

    x = dump_xml()
    print("[m26] MAN HIEN TAI:", [t for t in texts_of(x) if len(t) < 50][:8])

    if not any("6 chữ số" in t for t in texts_of(x)):
        print("[m26] khong o man OTP - stop")
        raise SystemExit

    # ===== BUOC 4: thu nhap MA SAI 000000 de xem phim co an khong =====
    test_positions = [(540, 620), (540, 560), (540, 700), (540, 480), (540, 780)]
    verdict = None
    for cx, cy in test_positions:
        tap(cx, cy)
        time.sleep(1.6)
        for kc in ("0", "0", "0", "0", "0", "0"):
            sh("input", "keyevent", str(KEYCODE[kc]))
            time.sleep(0.4)
        time.sleep(3)
        x = dump_xml()
        ts = texts_of(x)
        err = [t for t in ts if "không" in t.lower() or "chính xác" in t.lower() or "hết hạn" in t.lower()]
        still = any("6 chữ số" in t for t in ts)
        print(f"[m26] y={cy}: man_otp={still}, err={err[:1]}")
        if err:
            verdict = f"PHIM AN THAT (bao loi ma sai) tai ({cx},{cy})"
            break
        if not still:
            verdict = f"MAN CHUYEN HUONG sau khi nhap 000000 tai ({cx},{cy}): {ts[:6]}"
            break
    print("[m26] KET LUAN:", verdict or "KHONG thay doi nao - phim van khong an")
finally:
    lock.release()
