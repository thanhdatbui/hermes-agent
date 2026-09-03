# Farm Android OS & ROM Integrity Audit Patterns

## 1. Stock ROM vs Mod ROM for Social Automation (TikTok Farm)

| Category | Stock ROM (Samsung S7 / G930x) | Modded ROM / Auto-Reset Box ROM |
| :--- | :--- | :--- |
| **System Integrity** | 100% clean, `user` build, `release-keys` | Modified `adbd`, `userdebug`, `test-keys` |
| **Framework & Root** | No Root, SELinux `Enforcing` | Magisk / KernelSU / LSPosed / Xposed hooks |
| **Device Identifier** | True hardware identifiers & sensors | Spoofed via hooks (Pchanger, Michanger, FakeDevice) |
| **Device Trust Score** | High (natural user device trust) | Low (flagged as Risk Device / Virtualized / Emulator) |
| **Use Case** | Account nurturing, live shop, long-term followers | Batch registration, quick disposable spamming |

## 2. Non-Destructive ADB Audit Recipe for Farm Fleet

To inspect OS integrity across all online devices without interfering with running automation sessions:

```python
import subprocess

adb_path = r'C:\Program Files (x86)\xiaowei\tools\adb.exe'
res = subprocess.run([adb_path, 'devices'], capture_output=True, text=True)
serials = [l.split()[0] for l in res.stdout.strip().split('\n')[1:] if '\tdevice' in l]

props = ['ro.build.tags', 'ro.build.type', 'ro.adb.secure', 'ro.boot.warranty_bit', 'ro.product.model', 'ro.build.version.release']
cmd = ' && '.join([f'echo \"{p}=\$(getprop {p})\"' for p in props])
cmd += ' && echo \"SELINUX=\$(getenforce)\"'
cmd += ' && echo \"ROOT=\$(which su 2>/dev/null)\"'

for s in serials:
    p = subprocess.run([adb_path, '-s', s, 'shell', cmd], capture_output=True, text=True, timeout=10)
    # Parse output key=value lines
```

### Key Verification Markers:
- `ro.build.tags` must be `release-keys`.
- `ro.build.type` must be `user`.
- `SELinux` must be `Enforcing`.
- `ROOT` (`which su`) must be empty.
- `ro.adb.secure` must be `1`.
- `pm list packages` must not contain: `magisk`, `xposed`, `lsposed`, `michanger`, `pchanger`, `autoreset`.

*Note on Knox (`ro.boot.warranty_bit = 1`)*: Indicates past Odin flashing/bootloader unlocking (common when cross-flashing regional firmware like G930F onto Korean/Canadian S7 variants). Does not compromise Android runtime trust for TikTok/social apps as long as current ROM is clean stock without root/hooks.

## 3. Auto-Boot on Power Plug-in (LPM Modification)

Auto-booting devices upon power connection / power recovery (without physical power button press) does **not** degrade TikTok trust when implemented via standard charging daemon bypass:
- Mechanism: Modifying `/system/bin/lpm` (Samsung Low Power Mode charging animation script) to issue `/system/bin/reboot` instead of displaying battery graphics.
- Runtime state: Once Android boots into Launcher, OS runtime environment is completely stock.

## 4. Box LAN vs Box USB Architecture & S7 (Android 8) Technical Requirements

### 4.1. Why Box LAN Requires ROM/Kernel Modification (vs Stock ROM on Box USB)
- **Auto ADB TCP/IP**: Stock ROM disables `service.adb.tcp.port=5555` on reboot (requires USB cable to trigger). Box LAN has no USB cable to PC, so `init.rc` must auto-expose port 5555.
- **Ethernet Drivers**: Kernel must include Realtek (RTL8152/8153) or ASIX (AX88179) USB-to-LAN drivers for `eth0` auto-DHCP.
- **Routing Split**: Android default behavior switches `default gateway` to `eth0` when plugged in. Modded routing (`ip rule`/`iptables`) keeps `eth0` for local ADB/Xiaowei control while `wlan0` routes Internet/Proxy.
- **Battery & Thermal Bypass**: Without physical battery, S7 firmware requires thermistor emulation to prevent charging protection shutdown.

### 4.2. Root Cause of "Low Battery Temperature" Alert on S7 (Box P30 / LAN)
- **Symptom**: System continuously displays *"Battery temperature is too low. Charging paused"* alert overlay, freezing touch input and forcing CPU thermal throttle.
- **Hardware Cause**: S7 checks battery temperature via an NTC thermistor on battery socket. Missing **10kΩ pull-down resistor** on `BATT_TEMP` pin to `GND` makes the ADC read `-15°C` to `0°C`.
- **Kernel Fix**: If hardware lacks the 10kΩ resistor, `sec-battery.c` driver in kernel must hardcode positive temperature (25°C–30°C / `dumpsys battery` reporting `temperature: 250..300`).

### 4.3. Clean Box LAN ROM Standards for Social Automation (TikTok Farm)
- **Base**: Official Samsung Stock Android 8.0 Oreo.
- **Integrity**: `SELinux: Enforcing`, `ro.build.type=user`, `ro.build.tags=release-keys`, `ro.debuggable=0`.
- **Services**: Remove/disable `com.sec.android.app.sysdiagnostics` and battery warning dialogs.
- **Verification Commands**:
  ```bash
  adb -s <ip>:5555 shell dumpsys battery | grep temperature   # Expect 250..300 (25-30°C)
  adb -s <ip>:5555 shell getenforce                            # Expect Enforcing
  adb -s <ip>:5555 shell getprop ro.build.type                 # Expect user
  ```
