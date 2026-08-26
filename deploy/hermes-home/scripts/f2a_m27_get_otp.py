# -*- coding: utf-8 -*-
"""Đọc OTP Hotmail cho m27 qua Outlook app và nhập vào màn Xác minh email."""
import sys, os, time, subprocess
from datetime import datetime, timedelta

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\Hotmail")

from flows.hotmail_login import read_tiktok_otp_from_outlook_app
from automation_core.device_lock import acquire_device_lock

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
serial = "ce031823912ae0d20c"
email = "skitektts@hotmail.com"
artifact_dir = r"D:\Taadaa\runtime\kibe\artifacts\runs\f2a_m27"
os.makedirs(artifact_dir, exist_ok=True)

lock = acquire_device_lock(machine=27, serial=serial, project="tiktok-add-bao-mat-f2a", user_authorized=True)
try:
    print(f"[m27] Bắt đầu đọc OTP cho {email}...")
    otp = read_tiktok_otp_from_outlook_app(ADB, serial, email, artifact_dir, timeout=120)
    print(f"[m27] OTP trả về: {otp}")
finally:
    lock.release()
