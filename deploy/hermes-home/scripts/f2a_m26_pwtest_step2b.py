# -*- coding: utf-8 -*-
"""m26: doc OTP tu Gmail app bang cach goi truc tiep voi not_before moi.
Luu y: log 'Non-Gmail' truoc do co the den tu ban ghi cu trong log file (append mode).
Chay lai va in log ra stdout."""
import re
import subprocess
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")
sys.path.insert(0, r"D:\Taadaa\Tiktok_Reg")

from automation_core.device_lock import acquire_device_lock

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
KEYCODE = {c: 7 + i for i, c in enumerate("0123456789")}
machine, serial = 26, "ce081608c4e3ed1e05"
mail_acc = "tranthimy150820011508@gmail.com"

from datetime import datetime

lock = acquire_device_lock(machine=machine, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    from social_reg_v1 import _try_get_otp_gmail_app
    nb = datetime.now() - __import__("datetime").timedelta(minutes=3)
    code = None
    try:
        code = _try_get_otp_gmail_app(serial, mail_acc, not_before=nb)
    except Exception as e:
        print(f"[m26] Gmail app flow exception: {type(e).__name__}: {e}")
    print(f"[m26] OTP len={len(code) if code else 0}")
finally:
    lock.release()
