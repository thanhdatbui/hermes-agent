# -*- coding: utf-8 -*-
"""Kiem tra mail LIVE cua m26 (tranthimy150820011508@gmail.com) va m27 (skitektfs@hotmail.com).
- Gmail m26: doc qua app Gmail tren may 26 (da biet account login san) -> live
- Hotmail m27: thu doc qua Graph token / Outlook app tren may 27"""
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")
sys.path.insert(0, r"D:\Taadaa\Tiktok_Reg")
sys.path.insert(0, r"D:\Taadaa\Hotmail")

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"


def sh(serial, *args, timeout=90):
    return subprocess.run([ADB, "-s", serial, "shell"] + list(args), capture_output=True, timeout=timeout).stdout.decode("utf-8", errors="ignore")


# ============ M26: Gmail live check ============
serial26 = "ce081608c4e3ed1e05"
mail26 = "tranthimy150820011508@gmail.com"
print("=== M26 -", mail26, "===")
try:
    from social_reg_v1 import _try_get_otp_gmail_app
    nb = datetime.now() - timedelta(minutes=30)
    code = _try_get_otp_gmail_app(serial26, mail26, not_before=nb)
    print("[m26] GMAIL LIVE - doc duoc OTP TikTok:", "CO" if code else "KHONG (inbox mo duoc nhung khong co mail moi trong 30p)")
except Exception as e:
    print(f"[m26] Gmail flow exception: {type(e).__name__}: {str(e)[:120]}")
