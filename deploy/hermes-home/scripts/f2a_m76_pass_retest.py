# -*- coding: utf-8 -*-
"""Test lại pass m76 với escape ĐÚNG chuẩn như runner (lần trước gõ tay bị shell ăn ký tự)."""
import json
import re
import sys
import time

sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner")

from automation_core.adb import AdbClient
from automation_core.persistent_ui import capture_atx_session_ui
import xml.etree.ElementTree as ET

adb = AdbClient(adb_path=r"C:\Program Files (x86)\xiaowei\tools\adb.exe", serial="9885b64d56305a3731")
SHELL_ESCAPE = set("&<>|;()$`\\\"'!?#@*[]{}")


def dump():
    return capture_atx_session_ui(adb, timeout=10).xml


def texts():
    root = ET.fromstring(dump())
    return [n.attrib.get("text", "") for n in root.iter("node") if n.attrib.get("text", "")]


def type_escaped(pw):
    encoded = []
    for ch in pw:
        if ch == " ":
            encoded.append("%s")
        elif ch in SHELL_ESCAPE:
            encoded.append("\\" + ch)
        else:
            encoded.append(ch)
    adb.shell(["input", "tap", "540", "634"])
    time.sleep(1.0)
    for _ in range(45):
        adb.shell(["input", "keyevent", "67"])
    time.sleep(0.5)
    for enc in encoded:
        r = adb.shell(["input", "text", enc])
        if not r.ok:
            print("TYPE FAIL at", repr(enc))
            return False
    time.sleep(0.6)
    adb.shell(["input", "tap", "540", "847"])
    time.sleep(3.0)
    return True


def goto_password_entry():
    t = texts()
    if any("Xác minh đó là bạn" in x for x in t):
        root = ET.fromstring(dump())
        rows = [n for n in root.iter("node") if n.attrib.get("text", "") == "Mật khẩu"]
        b = rows[0].attrib["bounds"]
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
        cx, cy = (int(m.group(1)) + int(m.group(3))) // 2, (int(m.group(2)) + int(m.group(4))) // 2
        adb.shell(["input", "tap", str(cx), str(cy)])
        time.sleep(1.0)
        adb.shell(["input", "tap", "540", "847"])  # Tiếp [87,780][993,915]
        time.sleep(2.5)


def main():
    goto_password_entry()
    print("Man hien tai:", texts()[:7])
    files = [
        ("21/08 len11", r"D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\20260821-175105\batch_1\stt_76\tracking_result_stt76_cleoraingman07791_hotmail.com.json"),
        ("18/08 22:11 len14", r"D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\20260818-220349\batch_1\stt_76\tracking_result_stt76_cleoraingman07791_hotmail.com.json"),
        ("18/08 21:54 len13", r"D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\20260818-214439\batch_1\stt_76\tracking_result_stt76_cleoraingman07791_hotmail.com.json"),
    ]
    for tag, f in files:
        d = json.load(open(f, encoding="utf-8"))
        pw = d.get("password") or ""
        print(f"--- Thu pass {tag} (escape dung) ---")
        ok = type_escaped(pw)
        if not ok:
            continue
        out = texts()
        err = [x for x in out if "sai" in x.lower()]
        if err:
            print(f"KET QUA {tag}: SAI - {err[0][:70]}")
        else:
            print(f"KET QUA {tag}: KHONG BAO SAI -> man hinh: {out[:8]}")
            break


if __name__ == "__main__":
    main()
