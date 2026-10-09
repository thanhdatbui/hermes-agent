# Chụp Switcher Thực Tế Trên Thiết Bị Khi Screen Sleep/Blank (2026-09-21)

## Vấn Đề
Khi thiết bị đang ở trạng thái Sleep/Dozing, screencap trả về ảnh đen (12KB, toàn pixel (0,0,0,255)).
atx-agent `/dump/hierarchy` trả về 500 "open /sdcard/window_dump.xml: no such file or directory".

## Giải Pháp Đúng
Thứ tự: đánh thức màn hình → mở app → tap vào Profile → tap header/display name → chụp ảnh.

```python
adb = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
serial = "<device_serial>"
import subprocess, time

# 1. Đánh thức màn hình (PHẢI dùng keyevent 26 = POWER, không phải KEYCODE_WAKEUP=224 khi dozing sâu)
subprocess.run([adb, "-s", serial, "shell", "input", "keyevent", "26"])
time.sleep(1.5)

# 2. Kiểm tra màn hình đã ON chưa
out = subprocess.run([adb, "-s", serial, "shell", "dumpsys", "power"], capture_output=True, text=True).stdout
is_on = "Display Power: state=ON" in out
print("Screen ON:", is_on)

# 3. Mở TikTok qua deep link (nhanh hơn monkey, không bị "Warning: Activity not started" lần 2)
subprocess.run([adb, "-s", serial, "shell", "am", "start", "-a", "android.intent.action.VIEW",
                "-d", "snssdk1180://user/profile", "com.ss.android.ugc.trill"])
time.sleep(4)

# 4. Tap vào Display Name / header để mở Switcher
# Tọa độ chuẩn Samsung S7 (1080x1920): (285, 328) sau khi OCR đọc được vị trí display name
subprocess.run([adb, "-s", serial, "shell", "input", "tap", "285", "328"])
time.sleep(3)

# 5. uiautomator dump (chỉ khi TikTok đang foreground!)
subprocess.run([adb, "-s", serial, "shell", "uiautomator", "dump", "/sdcard/sw.xml"])
subprocess.run([adb, "-s", serial, "pull", "/sdcard/sw.xml", "D:/Taadaa/reports/m<N>_sw.xml"])
```

## Đọc Danh Sách Nick Từ XML Switcher
```python
import xml.etree.ElementTree as ET
tree = ET.parse("D:/Taadaa/reports/m<N>_sw.xml")
texts = [e.attrib.get("text") for e in tree.iter() if e.attrib.get("text")]
content_descs = [e.attrib.get("content-desc") for e in tree.iter() if e.attrib.get("content-desc")]
print("Texts:", texts)
print("Content descs:", content_descs)
```

## OCR Thay Thế Khi uiautomator dump Fail
```bash
python "C:\Users\Kibe\AppData\Local\hermes\skills\productivity\windows-native-ocr\scripts\winrt_ocr.py" D:/Taadaa/reports/m<N>_switcher.png
```

## atx-agent Forward Port
```bash
"C:\Program Files (x86)\xiaowei\tools\adb.exe" -s <serial> forward tcp:<local_port> tcp:7912
curl -s http://127.0.0.1:<local_port>/info   # kiểm tra còn sống
curl -s http://127.0.0.1:<local_port>/dump/hierarchy   # dump XML (chỉ khi màn hình ON và app đang foreground)
```
- Ghi chú: nên dùng port riêng cho từng máy (machine 1: 17912, machine 32: 17932, v.v.).

## So Khớp Danh Sách Nick Với Workbook
```python
import openpyxl
wb = openpyxl.load_workbook("D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx", data_only=True, read_only=True)
ws = wb.active
for r_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
    if row and str(row[0]) == str(machine_id):
        slot = (r_idx - 2) % 8 + 1
        print(f"Slot {slot}: {row[2]}")
```
