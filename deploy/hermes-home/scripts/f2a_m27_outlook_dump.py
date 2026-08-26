# -*- coding: utf-8 -*-
"""m27: dump man Outlook hien tai de xem dang o dau (inbox? login form? quick note?)."""
import subprocess
import time
import re

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
serial = "ce031823912ae0d20c"


def sh(*args, timeout=60):
    return subprocess.run([ADB, "-s", serial, "shell"] + list(args), capture_output=True, timeout=timeout).stdout.decode("utf-8", errors="ignore")


sh("monkey", "-p", "com.microsoft.office.outlook", "-c", "android.intent.category.LAUNCHER", "1")
time.sleep(8)
print("focus:", sh("dumpsys", "window").split("mCurrentFocus=")[1][:80])
sh("uiautomator", "dump", "/sdcard/m27o.xml")
x = sh("cat", "/sdcard/m27o.xml")
print("len:", len(x))
texts = sorted(set(re.findall(r'text="([^"]{2,60})"', x)))
for t in texts[:25]:
    print(f"  {t!r}")
descs = sorted(set(re.findall(r'content-desc="([^"]{4,50})"', x)))
print("DESCS:", descs[:15])
