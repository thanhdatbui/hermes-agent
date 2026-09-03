# Android Fleet Wi-Fi Automation & Troubleshooting via ADB

When configuring, recovering, or verifying Wi-Fi connections across large Android phone farms (80–160+ devices, Samsung S7 Android 8):

---

## 1. Zero-UI Wi-Fi Association via `adb-join-wifi.apk`

Interacting with Android Wi-Fi settings UI via ADB taps or UIAutomator is brittle in dense farms (soft keyboard covers buttons, scanned networks list shifts dynamically, auth dialogs mis-tap).

Use the headless helper tool located at `D:/Taadaa/AI-Tools/tools/adb-join-wifi.apk`:

### A. One-Step Connect Command
```bash
# 1. Install helper APK (idempotent, stream install)
adb -s <SERIAL> install -r "D:/Taadaa/AI-Tools/tools/adb-join-wifi.apk"

# 2. Trigger automated WPA2 association
adb -s <SERIAL> shell "am start -n com.steinwurf.adbjoinwifi/.MainActivity -e ssid '<SSID>' -e password '<PASSWORD>'"

# 3. Bounce Wi-Fi radio to force clean DHCP lease & route table assignment
adb -s <SERIAL> shell "svc wifi disable; sleep 1; svc wifi enable; sleep 3"
```

### B. Clean Slate Wipe (Forget Network)
If a device has bad credentials or stale BSSID cache:
```bash
# Long-press context menu or UI wipe
adb -s <SERIAL> shell "input swipe 332 528 332 528 1500; sleep 1; input tap 640 896"
```

---

## 2. Fast Parallel Farm Wi-Fi & Proxy Verification Script

Run this script to inspect all online devices concurrently (<10s for 80 phones):

```python
import subprocess, re, openpyxl, os
from concurrent.futures import ThreadPoolExecutor

ADB_PATH = r'C:\Program Files (x86)\xiaowei\tools\adb.exe'
EXCEL_PATH = r'D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx'

# Map serial -> machine index
serial_to_m = {}
if os.path.exists(EXCEL_PATH):
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws = wb['Proxy'] if 'Proxy' in wb.sheetnames else wb.active
    for r in range(2, ws.max_row + 1):
        m = ws.cell(r, 1).value
        s = str(ws.cell(r, 2).value).strip() if ws.cell(r, 2).value else ''
        if m and s:
            try:
                serial_to_m[s] = int(m)
            except:
                pass

res = subprocess.run([ADB_PATH, 'devices'], capture_output=True, text=True)
devices = [l.split('\t')[0].strip() for l in res.stdout.strip().split('\n')[1:] if '\tdevice' in l]

def check_device(s):
    m_num = serial_to_m.get(s, '?')
    try:
        out = subprocess.run([ADB_PATH, '-s', s, 'shell', 'ip addr show wlan0; dumpsys wifi | grep mWifiInfo'], capture_output=True, text=True, timeout=8).stdout
        m_ip = re.search(r'inet\s+([0-9.]+)/', out)
        ip = m_ip.group(1) if m_ip else 'NO_IP'
        
        m_ssid = re.search(r'SSID:\s*([^,]+)', out)
        ssid = m_ssid.group(1).strip() if m_ssid else 'NONE'
        
        m_spd = re.search(r'Link speed:\s*([0-9]+Mbps)', out)
        spd = m_spd.group(1) if m_spd else '?'
        
        m_freq = re.search(r'Frequency:\s*([0-9]+MHz)', out)
        freq = m_freq.group(1) if m_freq else '?'
        
        m_rssi = re.search(r'RSSI:\s*(-?[0-9]+)', out)
        rssi = m_rssi.group(1) if m_rssi else '?'
        
        proxy_ok = False
        if isinstance(m_num, int):
            port = 20000 + m_num
            p_test = subprocess.run([ADB_PATH, '-s', s, 'shell', f'printf \"GET / HTTP/1.0\\r\\n\\r\\n\" | toybox nc -w 2 -W 2 -q 1 192.168.110.2 {port}'], capture_output=True, text=True, timeout=5).stdout
            if 'HTTP' in p_test or p_test.strip():
                proxy_ok = True

        return {
            'serial': s, 'machine': m_num, 'ip': ip, 'ssid': ssid,
            'spd': spd, 'freq': freq, 'rssi': rssi, 'proxy_ok': proxy_ok,
            'status': 'OK' if (ip != 'NO_IP' and proxy_ok) else 'FAIL'
        }
    except Exception as e:
        return {'serial': s, 'machine': m_num, 'error': str(e), 'status': 'TIMEOUT'}

with ThreadPoolExecutor(max_workers=30) as ex:
    results = list(ex.map(check_device, devices))

results.sort(key=lambda x: (isinstance(x['machine'], str), x['machine']))
ok = [r for r in results if r['status'] == 'OK']
fail = [r for r in results if r['status'] != 'OK']

print(f'Total: {len(devices)} | OK: {len(ok)} | FAIL: {len(fail)}')
for f in fail:
    print(f"  FAIL: Machine {f['machine']} ({f['serial']}): IP={f.get('ip')} | SSID={f.get('ssid')} | ProxyOK={f.get('proxy_ok')}")
```
