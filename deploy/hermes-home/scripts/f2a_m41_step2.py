# -*- coding: utf-8 -*-
"""m41: dung uiautomator dump truc tiep (capture_atx bi rong tren may nay).
Di tiep: Cai dat -> Bao mat & quyen -> Xac minh 2 buoc -> in trang thai."""
import re
import subprocess
import time

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
machine, serial = 41, "ce031823f9b1903c01"


def sh(*args):
    return subprocess.run([ADB, "-s", serial, "shell"] + list(args), capture_output=True, timeout=30).stdout.decode("utf-8", errors="ignore")


def tap(x, y):
    sh("input", "tap", str(x), str(y))


def dump_xml():
    sh("uiautomator", "dump", "/sdcard/m41.xml")
    return sh("cat", "/sdcard/m41.xml")


def find_center(xml_text, text):
    m = re.search(r'text="' + re.escape(text) + r'"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml_text)
    if not m:
        m = re.search(r'content-desc="' + re.escape(text) + r'"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml_text)
    if not m:
        return None
    return ((int(m.group(1)) + int(m.group(3))) // 2, (int(m.group(2)) + int(m.group(4))) // 2)


# 1. Vao Cai dat (da o menu tu buoc truoc? dump lai cho chac)
xml_text = dump_xml()
cd = find_center(xml_text, "Cài đặt và quyền riêng tư")
if cd:
    print(f"[m41] Cai dat {cd}")
    tap(*cd)
    time.sleep(3)

# 2. Scroll tim Bảo mật & quyền
target = None
for i in range(7):
    xml_text = dump_xml()
    target = find_center(xml_text, "Bảo mật & quyền")
    if target and target[1] > 300:
        break
    target = None
    sh("input", "swipe", "540", "1500", "540", "900", "350")
    time.sleep(1.6)
if not target:
    raise SystemExit("[m41] khong thay Bao mat & quyen")
print(f"[m41] Bao mat & quyen {target}")
tap(*target)
time.sleep(3)

# 3. Xac minh 2 buoc
xv = None
for i in range(4):
    xml_text = dump_xml()
    xv = find_center(xml_text, "Xác minh 2 bước")
    if xv:
        # co the match nhieu row; lay cai y > 300
        for m in re.finditer(r'text="Xác minh 2 bước"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml_text):
            yy = (int(m.group(2)) + int(m.group(4))) // 2
            if yy > 300:
                xv = (540, yy)
                break
        break
    sh("input", "swipe", "540", "1400", "540", "800", "350")
    time.sleep(1.6)
if not xv:
    raise SystemExit("[m41] khong thay Xac minh 2 buoc")
print(f"[m41] Xac minh 2 buoc {xv}")
tap(*xv)
time.sleep(3)

xml_text = dump_xml()
texts = sorted(set(t for t in re.findall(r'text="([^"]{2,55})"', xml_text)))
print(f"[m41] MAN XAC MINH 2 BUOC: {[t for t in texts if not t.startswith(('14:', '89%', 'Chuông', 'Thông', 'Đang'))][:16]}")
